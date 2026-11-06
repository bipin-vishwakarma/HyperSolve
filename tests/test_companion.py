import base64
from io import BytesIO
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import threading
import time
import unittest
import requests
from hypersolve.companion.agents import AgentManager
from hypersolve.companion.answers import match_choice, parse_answers, validate_answers
from hypersolve.companion.config import EXTENSION_ID
from hypersolve.companion.native_host import read_message, write_message
from hypersolve.companion.server import CompanionServer

QUESTIONS=[{"id":1,"text":"Which colour?","options":["Blue sky","Red"]}]


class AnswerTests(unittest.TestCase):
    def test_matches_exact_text_or_letter_only(self):
        for text in ("Blue sky","blue   SKY","A","A. Blue sky"):
            self.assertEqual(match_choice(text,QUESTIONS[0]["options"]),0)
        for text in ("Blue","Blue sea","Probably blue sky","A. Red"):
            self.assertIsNone(match_choice(text,QUESTIONS[0]["options"]))
        self.assertIsNone(match_choice("Red",["Red","RED"]))

    def test_duplicate_and_unknown_ids_rejected(self):
        for text in ('{"1":"Red","Q1":"Blue sky"}','{"1":"Red","1":"Blue sky"}'):
            with self.assertRaises(ValueError):
                parse_answers(text)
        result=validate_answers('{"2":"Red"}',QUESTIONS)
        self.assertEqual(result[0]["status"],"review")

    def test_model_uncertainty_is_not_clicked(self):
        result=validate_answers('{"1":{"answer":"Red","needs_review":true,"reason":"Unclear"}}',QUESTIONS)
        self.assertEqual(result[0]["status"],"review")
        self.assertEqual(validate_answers('{"1":"Blue"}',QUESTIONS)[0]["status"],"review")
        self.assertEqual(validate_answers('{"1":"Red"}',QUESTIONS)[0]["option"],1)


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.release=threading.Event()
        self.started=threading.Event()
        def solver(questions):
            self.started.set()
            self.release.wait(3)
            return json.dumps({str(q["id"]):q["options"][0] for q in questions}),"Fixture API"
        self.manager=AgentManager(solver)
        for client,tab in (("a",1),("b",2)):
            self.manager.hello(client,"Chrome")
            self.manager.detect(client,{"id":client,"tab":tab,"url":"https://quiz.test/quiz","visible":1})

    def tearDown(self):
        self.manager.close()
        self.release.set()

    def approve(self,client):
        return self.manager.control(client,client,"approve")

    def test_no_provider_request_without_approval(self):
        with self.assertRaises(ValueError):
            self.manager.solve("a","a",QUESTIONS)
        self.assertFalse(self.started.is_set())

    def test_cross_profile_control_is_rejected(self):
        with self.assertRaises(ValueError):
            self.manager.control("a","b","approve")

    def test_tabs_have_independent_pause_and_stop(self):
        self.approve("a");self.approve("b")
        self.manager.control("a","a","pause")
        self.assertTrue(self.manager.get("a","a")["paused"])
        self.assertFalse(self.manager.get("b","b")["paused"])
        self.manager.control("a","a","stop")
        self.assertTrue(self.manager.get("b","b")["approved"])

    def test_late_api_response_cannot_revive_stopped_job(self):
        self.approve("a");self.manager.solve("a","a",QUESTIONS)
        self.assertTrue(self.started.wait(1))
        self.manager.control("a","a","stop");self.release.set();time.sleep(.05)
        job=self.manager.get("a","a")
        self.assertEqual(job["phase"],"cancelled")
        self.assertEqual(job["results"],[])

    def test_validation_and_real_counts(self):
        self.approve("a");self.manager.solve("a","a",QUESTIONS)
        self.manager.response("a","a",'{"1":"Red"}',"Fixture")
        with self.assertRaises(ValueError):
            self.manager.report("a","a",[2],[])
        self.manager.report("a","a",[1],[],True)
        self.assertEqual(self.manager.get("a","a")["phase"],"completed")
        self.assertEqual(self.manager.snapshot()["stats"],{"active":0,"waiting":1,"selected":1,"review":0})

    def test_ambiguous_answer_requires_review(self):
        self.approve("a");self.manager.solve("a","a",QUESTIONS)
        self.manager.response("a","a",'{"1":"Blue"}',"Fixture")
        self.manager.report("a","a",[],[],True)
        self.assertEqual(self.manager.get("a","a")["phase"],"review")


class TransportTests(unittest.TestCase):
    def test_native_frames_and_bounds(self):
        buffer=BytesIO();write_message(buffer,{"request":"x","data":"Café"});buffer.seek(0)
        self.assertEqual(read_message(buffer)["data"],"Café")
        for raw in (b'\x01',struct.pack('<I',1000001),struct.pack('<I',4)+b'{}'):
            with self.assertRaises(ValueError):read_message(BytesIO(raw))
        buffer=BytesIO();write_message(buffer,{"request":"x","data":"a"*1000001});buffer.seek(0)
        self.assertEqual(read_message(buffer)["request"],"x")

    def test_loopback_auth_and_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            server=CompanionServer(directory=directory);server.start()
            try:
                data=json.loads((Path(directory)/'companion-endpoint.json').read_text())
                payload={"op":"hello","client":"test"}
                self.assertEqual(requests.post(data['url'],json=payload,timeout=3).status_code,403)
                headers={"Authorization":"Bearer "+data['token']}
                self.assertEqual(requests.post(data['url'],json=payload,headers={**headers,"Origin":"https://evil.test"},timeout=3).status_code,403)
                self.assertEqual(requests.post(data['url'],json=payload,headers={**headers,"Host":"evil.test"},timeout=3).status_code,403)
                self.assertEqual(requests.post(data['url'],json=payload,headers=headers,timeout=3).status_code,200)
                self.assertEqual(requests.post(data['url'],json={**payload,"op":"unknown"},headers=headers,timeout=3).status_code,400)
            finally:server.close()
            self.assertFalse((Path(directory)/'companion-endpoint.json').exists())

    def test_extension_identity_and_shared_parser(self):
        root=Path(__file__).resolve().parents[1]
        manifest=json.loads((root/'extension/manifest.json').read_text())
        digest=hashlib.sha256(base64.b64decode(manifest['key'])).hexdigest()[:32]
        self.assertEqual(''.join(chr(ord('a')+int(v,16)) for v in digest),EXTENSION_ID)
        self.assertEqual((root/'extension/parser.js').read_bytes(),(root/'hypersolve/parser/dom_parser.js').read_bytes())
        self.assertFalse(manifest['content_scripts'][0]['all_frames'])
