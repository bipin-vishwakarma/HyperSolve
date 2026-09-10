import io
from typing import Tuple
from PIL import Image
import mss

class ScreenCapturer:
    """High-speed desktop screen capturer using MSS."""

    @staticmethod
    def capture_primary_screen() -> Image.Image:
        """Captures primary monitor and returns as PIL Image in <10ms."""
        with mss.mss() as sct:
            primary = sct.monitors[1]  # 1 is primary monitor
            sct_img = sct.grab(primary)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img

    @staticmethod
    def capture_region(bbox: Tuple[int, int, int, int]) -> Image.Image:
        """Captures a specific (left, top, width, height) region."""
        with mss.mss() as sct:
            sct_img = sct.grab({
                "left": bbox[0],
                "top": bbox[1],
                "width": bbox[2],
                "height": bbox[3]
            })
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img

    @staticmethod
    def to_jpeg_bytes(img: Image.Image, quality: int = 85) -> bytes:
        """Compresses PIL image to JPEG bytes for low-latency network transfer."""
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()
