"""Local tab snapshots; browser credentials stay in Chrome's profile."""
import asyncio
from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlparse

from .runtime import DATA_DIR, CDP_URL, inspect_connection, launch_chrome

WORKSPACE_PATH = DATA_DIR / "workspace.json"


def web_url(url):
    try:
        parsed = urlparse(url)
        return isinstance(url, str) and parsed.scheme in ("https", "http") and bool(parsed.hostname)
    except (ValueError, TypeError, AttributeError):
        return False


def load_workspace(path=WORKSPACE_PATH):
    path = Path(path)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("version") != 1
            or not isinstance(data.get("tabs"), list) or not data["tabs"]
            or any(not isinstance(tab, dict) or not web_url(tab.get("url")) for tab in data["tabs"])
            or (data.get("selected_url") is not None and not web_url(data["selected_url"]))
            or not isinstance(data.get("restored_targets", {}), dict)
            or any(not isinstance(key, str) or not isinstance(binding, dict)
                   or not web_url(binding.get("source")) or not web_url(binding.get("landed"))
                   for key, binding in data.get("restored_targets", {}).items())):
        raise ValueError("The saved workspace is invalid. Save the current tabs again.")
    return data


def save_workspace(tabs, selected_url=None, path=WORKSPACE_PATH):
    saved = [{"url": tab["url"], "title": str(tab.get("title", ""))}
             for tab in tabs if web_url(tab.get("url"))]
    if not saved:
        raise ValueError("No web tabs to save. Open your tabs in workspace Chrome first.")
    data = {"version": 1, "saved_at": datetime.now().astimezone().isoformat(),
            "tabs": saved, "selected_url": selected_url if web_url(selected_url) else None}
    _write_workspace(data, path)
    return data


def _write_workspace(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="workspace-", suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            json.dump(data, output, ensure_ascii=False, indent=2)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


async def _restore_connected(data, cdp_url, cancel_event=None):
    from hypersolve.core.browser import BrowserManager
    manager = BrowserManager(cdp_url)
    opened = 0
    try:
        browser = await manager.connect()
        pages = await manager.get_all_pages()
        wanted = {tab["url"] for tab in data["tabs"]}
        existing = Counter()
        bindings = {}
        previous_bindings = data.get("restored_targets", {})
        for page in pages:
            try:
                target_id = await manager.page_target_id(page)
            except Exception:
                target_id = None
            binding = previous_bindings.get(target_id, {})
            source = binding.get("source")
            if source in wanted and page.url in (source, binding.get("landed")):
                existing[source] += 1
                bindings[target_id] = binding
            else:
                existing[page.url] += 1
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        failed = []
        for tab in data["tabs"]:
            if cancel_event and cancel_event.is_set():
                break
            url = tab["url"]
            if existing[url]:
                existing[url] -= 1
                continue
            try:
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                opened += 1
                try:
                    target_id = await manager.page_target_id(page)
                    if isinstance(target_id, str):
                        bindings[target_id] = {"source": url, "landed": page.url}
                except Exception:
                    pass
            except Exception as exc:
                failed.append({"url": url, "error": str(exc)})
        return {"opened": opened, "failed": failed, "restored_targets": bindings,
                "cancelled": bool(cancel_event and cancel_event.is_set())}
    finally:
        await manager.disconnect()


def restore_workspace(cdp_url=CDP_URL, path=WORKSPACE_PATH, cancel_event=None):
    data = load_workspace(path)
    if not data:
        raise ValueError("No saved workspace yet. Save your open tabs first.")
    if cancel_event and cancel_event.is_set():
        return {"message": "Workspace restore cancelled.", "selected_url": data.get("selected_url")}
    if inspect_connection(cdp_url)["connected"]:
        result = asyncio.run(_restore_connected(data, cdp_url, cancel_event))
        data["restored_targets"] = result["restored_targets"]
        _write_workspace(data, path)
        message = f"Workspace restored. Opened {result['opened']} missing tab(s); current tabs were kept."
        if result["cancelled"]:
            message = f"Restore stopped. Opened {result['opened']} tab(s); current tabs were kept."
        if result["failed"]:
            message += f" {len(result['failed'])} tab(s) could not finish loading: " + "; ".join(item["url"] for item in result["failed"])
    else:
        launch_chrome(urls=[tab["url"] for tab in data["tabs"]])
        message = f"Opening Chrome with {len(data['tabs'])} saved tab(s). Refresh after it opens."
    return {"message": message, "selected_url": data.get("selected_url")}
