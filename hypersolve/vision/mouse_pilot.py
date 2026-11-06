import time
import math
import random
import pyautogui

class MousePilot:
    """Dispatches organic, humanized mouse movements and hardware clicks."""

    @staticmethod
    def click_normalized(x_percent: float, y_percent: float, humanized: bool = True):
        """
        Converts normalized (0.0 - 1.0) coordinates to screen pixels
        and moves the mouse with smooth easing and organic jitter.
        """
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in (x_percent, y_percent)):
            raise ValueError("Click coordinates must be finite values between 0 and 1")
        screen_w, screen_h = pyautogui.size()
        target_x = min(screen_w - 1, int(screen_w * x_percent))
        target_y = min(screen_h - 1, int(screen_h * y_percent))

        if humanized:
            # Human duration between 0.25 and 0.45 seconds
            duration = random.uniform(0.25, 0.45)
            # Smooth ease-out quad interpolation
            pyautogui.moveTo(target_x, target_y, duration=duration, tween=pyautogui.easeOutQuad)
            time.sleep(random.uniform(0.05, 0.12))
            pyautogui.click()
        else:
            pyautogui.click(target_x, target_y)
