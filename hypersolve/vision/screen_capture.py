import io
from typing import Tuple
from PIL import Image
import mss

class ScreenCapturer:
    """
    High-speed desktop screen capturer.
    Prioritizes Qt QScreen grabWindow (completely immune to GDI permission / BitBlt errors)
    with graceful fallback to MSS and PIL.ImageGrab.
    """

    @staticmethod
    def capture_primary_screen() -> Image.Image:
        """Captures primary monitor and returns as PIL Image in <10ms."""
        # 1. Try PyQt6 QScreen grabWindow (fastest and handles Windows permissions reliably)
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QBuffer, QIODevice
            app = QApplication.instance()
            if app:
                screen = app.primaryScreen()
                if screen:
                    pixmap = screen.grabWindow(0)
                    buffer = QBuffer()
                    buffer.open(QIODevice.OpenModeFlag.ReadWrite)
                    pixmap.save(buffer, "JPEG", quality=85)
                    return Image.open(io.BytesIO(bytes(buffer.data())))
        except Exception:
            pass

        # 2. Try MSS
        try:
            import mss
            with mss.mss() as sct:
                primary = sct.monitors[1]  # 1 is primary monitor
                sct_img = sct.grab(primary)
                return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception:
            pass

        # 3. Try PIL ImageGrab
        try:
            from PIL import ImageGrab
            return ImageGrab.grab()
        except Exception as e:
            raise RuntimeError(f"All screen capture methods failed: {e}")

    @staticmethod
    def capture_region(bbox: Tuple[int, int, int, int]) -> Image.Image:
        """Captures a specific (left, top, width, height) region."""
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QBuffer, QIODevice
            app = QApplication.instance()
            if app:
                screen = app.primaryScreen()
                if screen:
                    pixmap = screen.grabWindow(0, bbox[0], bbox[1], bbox[2], bbox[3])
                    buffer = QBuffer()
                    buffer.open(QIODevice.OpenModeFlag.ReadWrite)
                    pixmap.save(buffer, "JPEG", quality=85)
                    return Image.open(io.BytesIO(bytes(buffer.data())))
        except Exception:
            pass

        try:
            import mss
            with mss.mss() as sct:
                sct_img = sct.grab({
                    "left": bbox[0],
                    "top": bbox[1],
                    "width": bbox[2],
                    "height": bbox[3]
                })
                return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception:
            pass

        from PIL import ImageGrab
        return ImageGrab.grab(bbox=(bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]))

    @staticmethod
    def to_jpeg_bytes(img: Image.Image, quality: int = 85) -> bytes:
        """Compresses PIL image to JPEG bytes for low-latency network transfer."""
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()
