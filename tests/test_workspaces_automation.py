import asyncio
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from hypersolve.desktop.workspaces import save_workspace, load_workspace, restore_workspace, _restore_connected
from hypersolve.core.browser import BrowserManager
from hypersolve.core.daemon import HyperSolveDaemon
from hypersolve.parser.a11y_engine import QuizQuestion, QuizOption
import test_desktop


class WorkspaceTests(unittest.TestCase):
    def test_roundtrip_saves_tabs_not_cookies_and_preserves_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workspace.json"
            tabs = [{"url":"https://example.com/one","title":"One","cookies":"private"},
                    {"url":"https://example.com/one","title":"Duplicate"},
                    {"url":"chrome://settings","title":"Internal"}]
            save_workspace(tabs, "https://example.com/one", path)
            data = load_workspace(path)
            self.assertEqual(len(data["tabs"]), 2)
            self.assertEqual(data["selected_url"], tabs[0]["url"])
            self.assertNotIn("private", path.read_text())
            self.assertNotIn("chrome://", path.read_text())

    def test_empty_snapshot_does_not_overwrite_saved_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workspace.json"
            save_workspace([{"url":"https://example.com"}], path=path)
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                save_workspace([], path=path)
            self.assertEqual(path.read_bytes(), before)

    def test_failed_replace_preserves_previous_save_and_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workspace.json"
            save_workspace([{"url":"https://example.com"}], path=path)
            before = path.read_bytes()
            with patch.object(Path, "replace", side_effect=OSError("disk unavailable")):
                with self.assertRaises(OSError):
                    save_workspace([{"url":"https://other.test"}], path=path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_invalid_saved_urls_are_rejected_before_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workspace.json"
            path.write_text(json.dumps({"version":1,"tabs":[{"url":"file:///secret"}]}))
            with self.assertRaises(ValueError):
                load_workspace(path)

    @patch("hypersolve.desktop.workspaces.launch_chrome")
    @patch("hypersolve.desktop.workspaces.inspect_connection", return_value={"connected":False})
    def test_offline_restore_opens_saved_web_tabs_in_workspace_profile(self, inspect, launch):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workspace.json"
            save_workspace([{"url":"https://example.com"}], path=path)
            result = restore_workspace(path=path)
            launch.assert_called_once_with(urls=["https://example.com"])
            self.assertIn("Opening Chrome", result["message"])


class BrowserAutomationTests(unittest.IsolatedAsyncioTestCase):
    async def test_restore_opens_only_missing_tab_instances_and_never_closes_current_tabs(self):
        one = MagicMock(url="https://example.com/one")
        unrelated = MagicMock(url="https://other.test")
        page = MagicMock(goto=AsyncMock())
        context = MagicMock(new_page=AsyncMock(return_value=page))
        browser = MagicMock(contexts=[context])
        manager = MagicMock(connect=AsyncMock(return_value=browser), get_all_pages=AsyncMock(return_value=[one,unrelated]), disconnect=AsyncMock())
        data = {"tabs":[{"url":one.url},{"url":one.url},{"url":"https://example.com/two"}]}
        with patch("hypersolve.core.browser.BrowserManager", return_value=manager):
            self.assertEqual((await _restore_connected(data,"http://127.0.0.1:9222"))["opened"],2)
        self.assertEqual(context.new_page.await_count,2)
        one.close.assert_not_called()
        unrelated.close.assert_not_called()
        manager.disconnect.assert_awaited_once()

    async def test_restore_failure_still_disconnects_without_closing_browser(self):
        page = MagicMock(goto=AsyncMock(side_effect=RuntimeError("navigation failed")))
        context = MagicMock(new_page=AsyncMock(return_value=page))
        browser = MagicMock(contexts=[context])
        manager = MagicMock(connect=AsyncMock(return_value=browser),get_all_pages=AsyncMock(return_value=[]),disconnect=AsyncMock())
        with patch("hypersolve.core.browser.BrowserManager",return_value=manager):
            result = await _restore_connected({"tabs":[{"url":"https://example.com"}]},"http://127.0.0.1:9222")
            self.assertEqual(len(result["failed"]),1)
        manager.disconnect.assert_awaited_once()
        browser.close.assert_not_called()

    async def test_detector_uses_questions_not_quiz_url_keywords(self):
        provider = MagicMock(url="https://chatgpt.com")
        question = MagicMock(url="https://portal.test/course/lesson")
        ordinary = MagicMock(url="https://site.test/contest")
        for page in (provider,question,ordinary):
            page.is_closed.return_value = False
            page.evaluate = AsyncMock(return_value=page is question)
        manager = BrowserManager()
        manager.get_all_pages = AsyncMock(return_value=[provider,question,ordinary])
        async def parse(page):
            return [QuizQuestion(1,"Practice question?",[QuizOption(0,"First"),QuizOption(1,"Second")])] if page is question else []
        with patch("hypersolve.parser.a11y_engine.UniversalA11yParser.parse_page",side_effect=parse) as parser:
            tabs = await manager.scan_tabs()
        self.assertEqual(tabs["quiz"],[question])
        self.assertEqual(tabs["chatgpt"],[provider])
        self.assertEqual(parser.await_count,1)

    async def test_cancel_detector_propagates(self):
        page = MagicMock(url="https://portal.test/course")
        page.is_closed.return_value = False
        page.evaluate = AsyncMock(return_value=True)
        manager = BrowserManager()
        manager.get_all_pages = AsyncMock(return_value=[page])
        with patch("hypersolve.parser.a11y_engine.UniversalA11yParser.parse_page",side_effect=asyncio.CancelledError):
            with self.assertRaises(asyncio.CancelledError):
                await manager.scan_tabs()

    async def test_redirected_restored_tab_is_reused(self):
        page = MagicMock(url="https://example.com/login")
        context = MagicMock(new_page=AsyncMock())
        browser = MagicMock(contexts=[context])
        manager = MagicMock(connect=AsyncMock(return_value=browser),get_all_pages=AsyncMock(return_value=[page]),disconnect=AsyncMock(),page_target_id=AsyncMock(return_value="stable-id"))
        with patch("hypersolve.core.browser.BrowserManager",return_value=manager):
            result = await _restore_connected({"tabs":[{"url":"https://example.com/private"}],"restored_targets":{"stable-id":{"source":"https://example.com/private","landed":"https://example.com/login"}}},"http://127.0.0.1:9222")
        self.assertEqual(result["opened"],0)
        context.new_page.assert_not_called()

    async def test_restore_continues_after_one_navigation_fails(self):
        bad = MagicMock(goto=AsyncMock(side_effect=RuntimeError("offline")))
        good = MagicMock(url="https://good.test",goto=AsyncMock())
        context = MagicMock(new_page=AsyncMock(side_effect=[bad,good]))
        browser = MagicMock(contexts=[context])
        manager = MagicMock(connect=AsyncMock(return_value=browser),get_all_pages=AsyncMock(return_value=[]),disconnect=AsyncMock(),page_target_id=AsyncMock(return_value="good-id"))
        with patch("hypersolve.core.browser.BrowserManager",return_value=manager):
            result = await _restore_connected({"tabs":[{"url":"https://bad.test"},{"url":"https://good.test"}]},"http://127.0.0.1:9222")
        self.assertEqual(result["opened"],1)
        self.assertEqual(len(result["failed"]),1)
        self.assertEqual(context.new_page.await_count,2)

    async def test_quit_cancels_remaining_restore_tabs(self):
        import threading
        cancel = threading.Event()
        page = MagicMock(url="https://one.test",goto=AsyncMock(side_effect=lambda *a,**k:cancel.set()))
        context = MagicMock(new_page=AsyncMock(return_value=page))
        browser = MagicMock(contexts=[context])
        manager = MagicMock(connect=AsyncMock(return_value=browser),get_all_pages=AsyncMock(return_value=[]),disconnect=AsyncMock(),page_target_id=AsyncMock(return_value="one"))
        with patch("hypersolve.core.browser.BrowserManager",return_value=manager):
            result = await _restore_connected({"tabs":[{"url":"https://one.test"},{"url":"https://two.test"}]},"http://127.0.0.1:9222",cancel)
        self.assertTrue(result["cancelled"])
        self.assertEqual(context.new_page.await_count,1)
        manager.disconnect.assert_awaited_once()

    async def test_navigated_away_tab_does_not_hide_a_missing_saved_page(self):
        existing = MagicMock(url="https://other.test")
        fresh = MagicMock(url="https://example.com/private",goto=AsyncMock())
        context = MagicMock(new_page=AsyncMock(return_value=fresh))
        browser = MagicMock(contexts=[context])
        manager = MagicMock(connect=AsyncMock(return_value=browser),get_all_pages=AsyncMock(return_value=[existing]),disconnect=AsyncMock(),page_target_id=AsyncMock(side_effect=["old-id","new-id"]))
        data = {"tabs":[{"url":"https://example.com/private"}],"restored_targets":{"old-id":{"source":"https://example.com/private","landed":"https://example.com/login"}}}
        with patch("hypersolve.core.browser.BrowserManager",return_value=manager):
            result = await _restore_connected(data,"http://127.0.0.1:9222")
        self.assertEqual(result["opened"],1)
        existing.close.assert_not_called()

    async def test_quiz_identity_preserves_query_ids_and_hash_routes(self):
        daemon = HyperSolveDaemon()
        self.assertNotEqual(daemon._get_attempt_id("https://example.com/quiz?id=1"), daemon._get_attempt_id("https://example.com/quiz?id=2"))
        self.assertNotEqual(daemon._get_attempt_id("https://example.com/#/quiz/1"), daemon._get_attempt_id("https://example.com/#/quiz/2"))
        self.assertEqual(daemon._get_attempt_id("https://example.com/quiz?id=1&page=0"), daemon._get_attempt_id("https://example.com/quiz?id=1&page=1"))

    async def test_attempt_ids_are_scoped_by_origin(self):
        daemon = HyperSolveDaemon()
        self.assertNotEqual(daemon._get_attempt_id("https://one.test/attempt.php?attempt=1"),daemon._get_attempt_id("https://two.test/attempt.php?attempt=1"))


class AutomationDesktopTests(unittest.TestCase):
    setUpClass = classmethod(test_desktop.DesktopTests.setUpClass.__func__)
    setUp = test_desktop.DesktopTests.setUp
    tearDown = test_desktop.DesktopTests.tearDown
    def test_automatic_mode_can_start_without_a_selected_quiz(self):
        self.window._connection_result({"connected":True,"providers":["ChatGPT"],"targets":[]})
        self.assertFalse(self.window.start_button.isEnabled())
        self.window.automation_mode.setCurrentIndex(1)
        self.assertTrue(self.window.start_button.isEnabled())
        self.assertEqual(self.window.start_button.text(),"Start automation")
        self.assertFalse(self.window.targets.isEnabled())
        self.assertIsNone(self.window.engine)

    def test_watch_mode_stays_running_after_one_quiz_finishes(self):
        worker = MagicMock(auto_detect=True)
        self.window.engine = worker
        self.window._engine_event("complete",{"done":2,"total":2,"brain":"Test"})
        worker.stop.assert_not_called()
        self.assertEqual(self.window.state_label.text(),"Watching")
        self.window.engine = None

    def test_terminal_error_stops_watch_instead_of_repeating_requests(self):
        worker = MagicMock(auto_detect=True)
        self.window.engine = worker
        self.window._engine_event("error","Provider is not signed in")
        worker.stop.assert_called_once()
        self.assertTrue(self.window.log_toggle.isChecked())
        self.window.engine = None

    def test_workspace_operation_prevents_start_and_mode_change(self):
        self.window._connection_result({"connected":True,"providers":["ChatGPT"],"targets":[]})
        self.window.automation_mode.setCurrentIndex(1)
        self.window.workspace_busy = True
        self.window._update_start()
        self.assertFalse(self.window.start_button.isEnabled())
        self.assertFalse(self.window.automation_mode.isEnabled())

    def test_new_batch_replaces_old_question_rows(self):
        self.window._engine_event("questions",[{"id":1,"text":"First batch"}])
        old = self.window.question_rows[1]
        self.window._engine_event("questions",[{"id":1,"text":"Next batch"}])
        self.assertIsNot(old,self.window.question_rows[1])
        self.assertEqual(len(self.window.question_rows),1)
