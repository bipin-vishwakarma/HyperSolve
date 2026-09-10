import time
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
        screen_w, screen_h = pyautogui.size()
        target_x = int(screen_w * x_percent)
        target_y = int(screen_h * y_percent)

        if humanized:
            # Human duration between 0.25 and 0.45 seconds
            duration = random.uniform(0.25, 0.45)
            # Smooth ease-out quad interpolation
            pyautogui.moveTo(target_x, target_y, duration=duration, tween=pyautogui.easeOutQuad)
            time.sleep(random.uniform(0.05, 0.12))
            pyautogui.click()
        else:
            pyautogui.click(target_x, target_y)
