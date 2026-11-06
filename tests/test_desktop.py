import asyncio
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication
from hypersolve.desktop import runtime
from hypersolve.desktop.dashboard_window import HyperSolveDashboard, EngineWorker
from hypersolve.core.browser import BrowserManager
from hypersolve.core.daemon import HyperSolveDaemon
from hypersolve.updater.engine import OTAUpdateManager, UpdateInfo


class ConnectionTests(unittest.TestCase):
    def test_provider_requires_real_hostname(self):
        self.assertEqual(runtime.provider_for_url("https://chatgpt.com/c/123"), "ChatGPT")
        for url in ("https://chatgpt.com.evil.test", "https://evil.test/?chatgpt.com", "chrome://newtab"):
            self.assertIsNone(runtime.provider_for_url(url))

    @patch("hypersolve.desktop.runtime.requests.get")
    def test_scan_filters_internal_tabs_and_does_not_claim_auth(self, get):
        get.return_value.json.return_value = [
            {"type":"page", "url":"https://chatgpt.com/"},
            {"type":"page", "url":"https://example.com/form", "title":"Form"},
            {"type":"page", "url":"chrome://settings"},
            {"type":"service_worker", "url":"https://example.com/sw"}]
        data = runtime.inspect_connection()
        self.assertTrue(data["connected"])
        self.assertEqual(data["providers"], ["ChatGPT"])
        self.assertEqual(len(data["targets"]), 1)
        self.assertNotIn("authenticated", data)

    @patch("hypersolve.desktop.runtime.requests.get", side_effect=runtime.requests.ConnectionError("offline"))
    def test_offline_scan_is_recoverable(self, get):
        self.assertFalse(runtime.inspect_connection()["connected"])

    @patch("hypersolve.desktop.runtime.subprocess.Popen")
    @patch("hypersolve.desktop.runtime.find_chrome", return_value=None)
    def test_missing_chrome_does_not_spawn(self, find, spawn):
        with self.assertRaises(FileNotFoundError):
            runtime.launch_chrome()
        spawn.assert_not_called()


class UpdateTests(unittest.TestCase):
    url = "https://github.com/bipin-vishwakarma/HyperSolve/releases/download/v9.0.0/HyperSolve-Setup.exe"
    def test_versions_are_numeric_and_strict(self):
        self.assertGreater(OTAUpdateManager.parse_semver("v2.10.0"), OTAUpdateManager.parse_semver("2.9.0"))
        with self.assertRaises(ValueError):
            OTAUpdateManager.parse_semver("../../bad")

    def test_only_own_https_release_urls(self):
        self.assertTrue(OTAUpdateManager._trusted_url(self.url))
        for url in (self.url.replace("https", "http"), self.url.replace("github.com", "github.com.evil.test"), self.url.replace("bipin-vishwakarma", "someone")):
            self.assertFalse(OTAUpdateManager._trusted_url(url))

    @patch("hypersolve.updater.engine.requests.get")
    def test_missing_release_is_not_reported_as_current(self, get):
        get.return_value.status_code = 404
        with self.assertRaisesRegex(RuntimeError, "No published release"):
            OTAUpdateManager.check_for_updates()

    @patch("hypersolve.updater.engine.requests.get")
    def test_new_release_requires_manifest(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = {"tag_name":"v9.0.0", "assets":[]}
        with self.assertRaisesRegex(RuntimeError, "checksum manifest"):
            OTAUpdateManager.check_for_updates()

    @patch("hypersolve.updater.engine.subprocess.Popen")
    @patch("hypersolve.updater.engine.requests.get")
    def test_download_never_executes_without_hash(self, get, spawn):
        with self.assertRaises(ValueError):
            OTAUpdateManager.download_and_install_update(UpdateInfo("9.0.0", self.url))
        get.assert_not_called()
        spawn.assert_not_called()

    @patch("hypersolve.updater.engine.subprocess.Popen")
    @patch("hypersolve.updater.engine.requests.get")
    def test_hash_mismatch_discards_download(self, get, spawn):
        get.return_value.__enter__.return_value.iter_content.return_value = [b"wrong"]
        get.return_value.__enter__.return_value.headers = {}
        with tempfile.TemporaryDirectory() as directory:
            location = Path(directory) / "download"
            location.mkdir()
            with patch("hypersolve.updater.engine.tempfile.mkdtemp", return_value=str(location)):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    OTAUpdateManager.download_and_install_update(UpdateInfo("9.0.0", self.url, sha256="a"*64))
            self.assertFalse(location.exists())
        spawn.assert_not_called()

    @patch("hypersolve.updater.engine.subprocess.Popen")
    @patch("hypersolve.updater.engine.requests.get")
    def test_matching_hash_launches_visible_installer(self, get, spawn):
        get.return_value.__enter__.return_value.iter_content.return_value = [b"installer"]
        get.return_value.__enter__.return_value.headers = {}
        with tempfile.TemporaryDirectory() as directory:
            with patch("hypersolve.updater.engine.tempfile.mkdtemp", return_value=directory):
                self.assertTrue(OTAUpdateManager.download_and_install_update(UpdateInfo("9.0.0", self.url, sha256=hashlib.sha256(b"installer").hexdigest())))
            self.assertEqual(len(spawn.call_args.args[0]), 1)
            self.assertFalse(spawn.call_args.kwargs["shell"])


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_disconnect_stops_transport_without_browser_close(self):
        manager = BrowserManager()
        manager.browser = AsyncMock()
        browser = manager.browser
        manager.playwright = AsyncMock()
        transport = manager.playwright
        await manager.disconnect()
        browser.close.assert_not_called()
        transport.stop.assert_awaited_once()
        self.assertIsNone(manager.browser)

    async def test_exact_target_id_wins_for_duplicate_urls(self):
        manager = BrowserManager()
        first, second = MagicMock(), MagicMock()
        first.url = second.url = "https://example.com"
        for page, target_id in ((first, "one"), (second, "two")):
            session = MagicMock(send=AsyncMock(return_value={"targetInfo":{"targetId":target_id}}), detach=AsyncMock())
            page.context.new_cdp_session = AsyncMock(return_value=session)
        manager.get_all_pages = AsyncMock(return_value=[first, second])
        self.assertIs(await manager.find_target_page("https://example.com", "two"), second)
        first.context.new_cdp_session.return_value.detach.assert_awaited_once()
        second.context.new_cdp_session.return_value.detach.assert_awaited_once()

    async def test_explicit_page_bypasses_quiz_classifier(self):
        events = []
        daemon = HyperSolveDaemon(target_url="https://example.com/view.php", on_event=lambda *event: events.append(event))
        page = MagicMock()
        page.url = "https://example.com/view.php"
        page.is_closed.return_value = False
        daemon.browser_manager.find_target_page = AsyncMock(return_value=page)
        daemon.browser_manager.scan_tabs = AsyncMock(side_effect=AssertionError("classifier must not run"))
        daemon.brain_router = MagicMock()
        daemon.brain_router.session_pool.get_active_providers = AsyncMock(return_value={"chatgpt":[MagicMock()]})
        daemon._solve_quiz_tab = AsyncMock()
        await daemon._supervisory_cycle()
        daemon._solve_quiz_tab.assert_awaited_once_with(page)

    async def test_cancel_always_stops_heartbeat_and_disconnects(self):
        daemon = HyperSolveDaemon(target_url="https://example.com")
        daemon.browser_manager = MagicMock()
        daemon.browser_manager.connect = AsyncMock()
        daemon.browser_manager.disconnect = AsyncMock()
        daemon._supervisory_cycle = AsyncMock(side_effect=asyncio.CancelledError)
        heartbeat = MagicMock(start=AsyncMock(), stop=AsyncMock())
        with patch("hypersolve.core.daemon.HeartbeatDaemon", return_value=heartbeat), patch("hypersolve.core.daemon.BrainRouter"):
            with self.assertRaises(asyncio.CancelledError):
                await daemon.start()
        heartbeat.stop.assert_awaited_once()
        daemon.browser_manager.disconnect.assert_awaited_once()

    async def test_stop_before_worker_initializes_never_connects(self):
        worker = EngineWorker("https://example.com")
        worker.stop()
        with patch("hypersolve.desktop.dashboard_window.HyperSolveDaemon") as daemon:
            await worker._run_engine()
        daemon.assert_not_called()


class VisionValidationTests(unittest.TestCase):
    def test_malformed_coordinates_never_become_default_clicks(self):
        from hypersolve.vision.vlm_solver import VLMSolver
        solver = VLMSolver(api_key="test")
        for raw in ('{"answer":"B"}', '{"answer":"B","x_percent":2,"y_percent":0.3}',
                    '{"answer":"B","x_percent":NaN,"y_percent":0.3}',
                    '{"answer":"","x_percent":0.2,"y_percent":0.3}'):
            self.assertIsNone(solver._parse_json_result(raw))
        result = solver._parse_json_result('{"answer":"B","x_percent":0.2,"y_percent":0.3}')
        self.assertEqual(result.x_percent, 0.2)
        self.assertIsNone(result.confidence)


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.settings_patch = patch("hypersolve.desktop.dashboard_window.QSettings")
        settings = self.settings_patch.start().return_value
        settings.value.side_effect = lambda key, default=None, **kwargs: default
        self.tray_patch = patch("hypersolve.desktop.dashboard_window.QSystemTrayIcon.isSystemTrayAvailable", return_value=False)
        self.tray_patch.start()
        self.window = HyperSolveDashboard(auto_scan=False)

    def tearDown(self):
        self.window.tray.hide()
        self.window.deleteLater()
        self.app.processEvents()
        self.tray_patch.stop()
        self.settings_patch.stop()

    def test_public_tray_import_still_resolves(self):
        from hypersolve.desktop import run_tray, HyperSolveTrayApp
        self.assertTrue(callable(run_tray))
        self.assertIs(HyperSolveTrayApp, HyperSolveDashboard)

    def test_launch_is_idle_without_engine(self):
        self.assertIsNone(self.window.engine)
        self.assertFalse(self.window.start_button.isEnabled())
        self.assertFalse(self.window.stop_button.isEnabled())

    def test_start_requires_browser_provider_and_target(self):
        data = {"connected":True, "providers":[], "targets":[{"title":"Practice", "url":"https://example.com"}]}
        with patch.dict(os.environ, {}, clear=True):
            self.window._connection_result(data)
            self.assertFalse(self.window.start_button.isEnabled())
            data["providers"] = ["ChatGPT"]
            self.window._connection_result(data)
            self.assertTrue(self.window.start_button.isEnabled())

    def test_real_events_render_full_text_as_plain_text(self):
        text = "<b>literal content</b> " + "long question " * 30
        self.window._engine_event("questions", [{"id":1,"text":text}])
        self.window._engine_event("answer", {"id":1,"answer":"Choice B", "done":1,"total":2})
        self.assertEqual(self.window.question_rows[1].answer_label.text(), "Selected: Choice B")
        self.assertEqual(self.window.progress.value(), 50)

    def test_minimum_window_size_does_not_expand(self):
        self.window.resize(860, 620)
        self.window.show()
        self.app.processEvents()
        self.window.switch_page(2)
        self.app.processEvents()
        self.assertEqual((self.window.width(), self.window.height()), (860, 620))

    def test_primary_action_has_visible_filled_background(self):
        from PyQt6.QtWidgets import QPushButton
        self.window.switch_page(1)
        self.window.show()
        self.app.processEvents()
        action = next(item for item in self.window.findChildren(QPushButton) if item.text() == "Open workspace browser")
        self.assertEqual(action.grab().toImage().pixelColor(8, 8).name(), "#3759dc")

    def test_api_key_choose_tab_action_opens_selector(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY":"test"}):
            self.window._connection_result({"connected":True,"providers":[],"targets":[{"url":"https://example.com","title":"Practice"}]})
            self.assertEqual(self.window.next_button.text(), "Choose tab")
            with patch.object(self.window.targets, "showPopup") as popup:
                self.window._next_setup_action()
                popup.assert_called_once()

    def test_engine_failure_expands_log_with_recovery_message(self):
        self.window._engine_event("error", "AI returned no usable answers. Check sign-in.")
        self.assertTrue(self.window.log_toggle.isChecked())
        self.assertIn("Check sign-in", self.window.activity.toPlainText())

    def test_final_close_is_accepted_after_workers_finish(self):
        from PyQt6.QtGui import QCloseEvent
        self.window._quitting = True
        event = QCloseEvent()
        self.window.closeEvent(event)
        self.assertTrue(event.isAccepted())
        self.window.jobs = [object()]
        event = QCloseEvent()
        self.window.closeEvent(event)
        self.assertFalse(event.isAccepted())
        self.window.jobs = []

    def test_update_failure_is_visible_and_retryable(self):
        self.window._update_failed("offline")
        self.assertIn("offline", self.window.update_label.text())
        self.assertTrue(self.window.check_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
