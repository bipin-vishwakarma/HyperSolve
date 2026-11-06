"""Thread-safe, independent per-tab sessions. No provider call before approval."""
from copy import deepcopy
import os
import json
import threading
import time
from urllib.parse import urlparse
import requests
from .answers import build_prompt, validate_answers

TERMINAL = {"completed", "review", "cancelled", "error", "ignored"}


def web_url(value):
    try:
        return isinstance(value,str) and urlparse(value).scheme in ("http","https") and bool(urlparse(value).hostname)
    except ValueError:
        return False


class AgentManager:
    def __init__(self, api_solver=None):
        self.lock = threading.RLock()
        self.jobs = {}
        self.clients = {}
        self.api_solver = api_solver or self._api_solve
        self.api_slots = threading.Semaphore(3)
        self.closing = False

    def _owned(self, client, job_id):
        job = self.jobs.get(job_id)
        if not job or job["client"] != client:
            raise ValueError("Session was not found in this browser")
        return job

    def hello(self, client, browser):
        if not isinstance(client,str) or not 1 <= len(client) <= 100:
            raise ValueError("Invalid browser identity")
        with self.lock:
            self.clients[client] = {"browser":str(browser)[:40],"last_seen":time.time()}
        return self.snapshot(client)

    def detect(self, client, payload):
        job_id = payload.get("id")
        if (not isinstance(job_id,str) or not 1 <= len(job_id) <= 200 or not web_url(payload.get("url"))
                or not isinstance(payload.get("tab"),int) or not isinstance(payload.get("visible"),int)
                or not 1 <= payload["visible"] <= 500):
            raise ValueError("Invalid quiz detection")
        with self.lock:
            if self.closing:
                raise ValueError("Manager is closing")
            if job_id in self.jobs:
                job = self._owned(client,job_id)
                if job["phase"] == "detected":
                    total = payload.get("total")
                    job.update(title=str(payload.get("title","Quiz"))[:200],visible=payload["visible"],total=total if isinstance(total,int) and payload["visible"] <= total <= 500 else None)
                return self._public(job)
            if len(self.jobs) >= 300:
                inactive = next((key for key,value in self.jobs.items() if value["phase"] in TERMINAL),None)
                if inactive:
                    del self.jobs[inactive]
                else:
                    raise ValueError("Too many active sessions; stop some tabs first")
            job = {"id":job_id,"client":client,"tab":payload["tab"],"document":str(payload.get("document",""))[:100],
                   "url":payload["url"],"title":str(payload.get("title","Quiz"))[:200],"visible":payload["visible"],
                   "total":payload.get("total") if isinstance(payload.get("total"),int) and payload["total"]>=payload["visible"] else None,
                   "phase":"detected","approved":False,"paused":False,"provider":"","detail":"Waiting for your confirmation",
                   "questions":[],"results":[],"selected":[],"failed":[],"created":time.time(),"updated":time.time()}
            self.jobs[job_id] = job
            return self._public(job)

    def control(self, client, job_id, action):
        with self.lock:
            job = self._owned(client,job_id)
            if action == "approve" and job["phase"] == "detected":
                job.update(approved=True,detail="Approved; preparing to scan")
            elif action == "ignore" and job["phase"] == "detected":
                job.update(phase="ignored",detail="Ignored")
            elif action == "pause" and job["phase"] not in TERMINAL:
                job["paused"] = True
            elif action == "resume" and job["phase"] not in TERMINAL:
                job["paused"] = False
            elif action == "stop":
                job.update(phase="cancelled",paused=False,detail="Stopped by you")
            else:
                raise ValueError("This action is not available for the session")
            job["updated"] = time.time()
            return self._public(job)

    def progress(self, client, job_id, phase, detail="", total=None, provider=None):
        with self.lock:
            job = self._owned(client,job_id)
            if not job["approved"] or job["phase"] in TERMINAL:
                return self._public(job)
            if phase not in ("harvesting","queued","solving","selecting","error"):
                raise ValueError("Invalid session phase")
            job.update(phase=phase,detail=str(detail)[:1000],updated=time.time())
            if isinstance(total,int) and 0 <= total <= 500:
                job["total"] = total
            if provider is not None:
                job["provider"] = str(provider)[:100]
            return self._public(job)

    def solve(self, client, job_id, questions):
        if len(json.dumps(questions,ensure_ascii=False).encode("utf-8")) > 300_000:
            raise ValueError("Question set is too large; split the quiz into smaller sessions")
        if (not isinstance(questions,list) or not 1 <= len(questions) <= 500
                or any(not isinstance(q,dict) or not isinstance(q.get("id"),int)
                       or not isinstance(q.get("text"),str) or not q["text"].strip() or len(q["text"])>20000
                       or not isinstance(q.get("options"),list) or not 2 <= len(q["options"]) <= 30
                       or any(not isinstance(v,str) or not v.strip() or len(v)>5000 for v in q["options"]) for q in questions)
                or len({q["id"] for q in questions}) != len(questions)):
            raise ValueError("Invalid question set")
        with self.lock:
            job = self._owned(client,job_id)
            if not job["approved"] or job["phase"] in TERMINAL:
                raise ValueError("This quiz is not approved for solving")
            if job["questions"]:
                return self._public(job)
            job.update(questions=deepcopy(questions),total=len(questions),phase="queued",detail="Waiting for a provider")
            api = bool(os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or self.api_solver != self._api_solve)
            job["execution"] = "api" if api else "web"
            if api:
                threading.Thread(target=self._run_api,args=(client,job_id),daemon=True).start()
            return self._public(job,work=True)

    def _run_api(self, client, job_id):
        with self.api_slots:
            while True:
                with self.lock:
                    job = self._owned(client,job_id)
                    if self.closing or job["phase"] in TERMINAL:
                        return
                    if not job["paused"]:
                        questions = deepcopy(job["questions"])
                        job.update(phase="solving",provider="API",detail="Waiting for AI response")
                        break
                time.sleep(.1)
            try:
                raw,provider = self.api_solver(questions)
                self.response(client,job_id,raw,provider)
            except Exception as exc:
                self.progress(client,job_id,"error",str(exc))

    @staticmethod
    def _api_solve(questions):
        prompt = build_prompt(questions)
        if os.getenv("OPENAI_API_KEY"):
            response = requests.post("https://api.openai.com/v1/chat/completions",headers={"Authorization":"Bearer "+os.environ["OPENAI_API_KEY"]},
                                     json={"model":os.getenv("HYPERSOLVE_OPENAI_MODEL","gpt-4o-mini"),"messages":[{"role":"user","content":prompt}],"response_format":{"type":"json_object"}},timeout=(5,45))
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"],"OpenAI API"
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("No API key configured")
        model = os.getenv("HYPERSOLVE_GEMINI_MODEL","gemini-2.0-flash")
        response = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",headers={"x-goog-api-key":key},json={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"response_mime_type":"application/json"}},timeout=(5,45))
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"],"Gemini API"

    def response(self, client, job_id, raw, provider):
        with self.lock:
            job = self._owned(client,job_id)
            if not job["approved"] or not job["questions"] or job["phase"] in TERMINAL:
                return self._public(job)
            job.update(results=validate_answers(raw,job["questions"]),provider=str(provider)[:100],phase="ready",detail="Answers validated; ready to select",updated=time.time())
            return self._public(job)

    def report(self, client, job_id, selected, failed, finish=False):
        with self.lock:
            job = self._owned(client,job_id)
            if job["phase"] in TERMINAL or not job["approved"]:
                return self._public(job)
            allowed = {r["id"] for r in job["results"] if r["status"] == "ready"}
            if not isinstance(selected,list) or not isinstance(failed,list) or not set(selected) <= allowed or not set(failed) <= {q["id"] for q in job["questions"]}:
                raise ValueError("Invalid selection report")
            job["selected"] = sorted(set(job["selected"]) | set(selected))
            job["failed"] = sorted(set(job["failed"]) | set(failed))
            if finish:
                review = len(job["selected"]) != len(job["questions"]) or bool(job["failed"])
                job.update(phase="review" if review else "completed",detail="Review flagged questions in your browser" if review else "All matching answers selected; review in browser")
            else:
                job["phase"] = "selecting"
            job["updated"] = time.time()
            return self._public(job)

    def get(self, client, job_id):
        with self.lock:
            return self._public(self._owned(client,job_id),work=True)

    def snapshot(self, client=None):
        with self.lock:
            recent = {key:value for key,value in self.clients.items() if time.time()-value["last_seen"] < 30}
            for job in self.jobs.values():
                if job["client"] not in recent and job["phase"] not in TERMINAL:
                    job.update(phase="error",paused=False,detail="Browser companion disconnected. Scan again to restart.")
            jobs = [self._public(job) for job in self.jobs.values() if client is None or job["client"] == client]
            return {"sessions":jobs,"clients":deepcopy(recent) if client is None else {},
                    "stats":{"active":sum(j["phase"] not in TERMINAL and j["approved"] for j in jobs),
                             "waiting":sum(j["phase"]=="detected" and not j["approved"] for j in jobs),
                             "selected":sum(len(j["selected"]) for j in jobs),"review":sum(j["review_count"] + len(j["failed"]) for j in jobs)}}

    def close(self):
        with self.lock:
            self.closing = True
            for job in self.jobs.values():
                if job["phase"] not in TERMINAL:
                    job.update(phase="cancelled",detail="Windows manager closed")

    @staticmethod
    def _public(job, work=False):
        result = deepcopy(job)
        questions = result.pop("questions")
        result["review_count"] = sum(r["status"] == "review" for r in result["results"])
        if not work:
            result.pop("results")
        result["status"] = "paused" if job["paused"] else job["phase"]
        if work and result.get("execution") == "web" and questions and result["phase"] in ("queued","solving"):
            result["prompt"] = build_prompt(questions)
        return result
