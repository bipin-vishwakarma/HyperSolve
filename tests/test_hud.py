import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from hypersolve.hud.controls import OverlayControls
from hypersolve.hud.injector import HUDInjector


class OverlayTests(unittest.IsolatedAsyncioTestCase):
    async def test_install_binds_controls_and_reinjects_after_navigation(self):
        page = MagicMock(expose_binding=AsyncMock(),add_init_script=AsyncMock(),evaluate=AsyncMock())
        handler = AsyncMock()
        await HUDInjector.install(page,"test_binding",handler)
        page.expose_binding.assert_awaited_once_with("test_binding",handler)
        script = page.add_init_script.call_args.kwargs["script"]
        self.assertIn('"test_binding"',script)
        self.assertNotIn('__HYPERSOLVE_CSS__',script)
        self.assertIn("attachShadow({ mode: 'open' })",script)
        self.assertNotIn('visibilityState',script)

    async def test_state_uses_structured_arguments_not_javascript_interpolation(self):
        page = MagicMock(evaluate=AsyncMock())
        unsafe = "AI's name; <script>"
        await HUDInjector.update_stats(page,2,4,unsafe,unsafe)
        script,args = page.evaluate.call_args.args
        self.assertNotIn(unsafe,script)
        self.assertEqual(args,[2,4,unsafe,unsafe])

    async def test_pause_holds_checkpoint_until_resume(self):
        controls = OverlayControls()
        controls.owner = MagicMock(done=lambda:False)
        page = MagicMock(is_closed=lambda:False)
        controls.pages.add(page)
        with patch.object(HUDInjector,"set_paused",new=AsyncMock()):
            await controls.handle({"page":page},"pause")
            checkpoint = asyncio.create_task(controls.checkpoint())
            await asyncio.sleep(0)
            self.assertFalse(checkpoint.done())
            await controls.handle({"page":page},"resume")
            await asyncio.wait_for(checkpoint,1)

    async def test_invalid_page_and_action_do_not_control_session(self):
        controls = OverlayControls()
        controls.owner = MagicMock(done=lambda:False)
        result = await controls.handle({"page":object()},"stop")
        self.assertFalse(result["accepted"])
        controls.owner.cancel.assert_not_called()

    async def test_stop_cancels_owner(self):
        controls = OverlayControls()
        owner = asyncio.create_task(asyncio.sleep(30))
        controls.owner = owner
        page = object()
        controls.pages.add(page)
        await controls.handle({"page":page},"stop")
        with self.assertRaises(asyncio.CancelledError):
            await owner

    async def test_attach_is_idempotent_and_finish_carries_error(self):
        controls = OverlayControls()
        page = MagicMock(is_closed=lambda:False)
        with patch.object(HUDInjector,"install",new=AsyncMock()) as install, patch.object(HUDInjector,"set_paused",new=AsyncMock()), patch.object(HUDInjector,"reset",new=AsyncMock()) as reset, patch.object(HUDInjector,"finish",new=AsyncMock()) as finish:
            await controls.attach(page)
            await controls.attach(page)
            install.assert_awaited_once()
            reset.assert_awaited_once_with(page)
            controls.last_error = "Provider unavailable"
            await controls.finish()
            finish.assert_awaited_once_with(page,"Provider unavailable")
        self.assertIsNone(controls.owner)

    async def test_child_frame_cannot_control_session(self):
        controls = OverlayControls()
        controls.owner = MagicMock(done=lambda:False)
        page = MagicMock()
        controls.pages.add(page)
        result = await controls.handle({"page":page,"frame":object()},"stop")
        self.assertFalse(result["accepted"])
        controls.owner.cancel.assert_not_called()

    async def test_bounded_finish_attempts_every_page(self):
        controls = OverlayControls()
        first = MagicMock(is_closed=lambda:False)
        second = MagicMock(is_closed=lambda:False)
        controls.pages.update([first,second])
        with patch.object(HUDInjector,"finish",new=AsyncMock()) as finish:
            await controls.finish()
            self.assertEqual(finish.await_count,2)
