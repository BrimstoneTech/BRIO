"""
Brio Vision Engine (brio_vision.py)

Purpose: Allows Brio to "see" the desktop screen and analyze visual context.
"""

import os
import time
from PIL import ImageGrab

class VisionEngine:
    def __init__(self, storage_dir="vision_cache"):
        self.storage_dir = storage_dir
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def capture_screen(self, region=None):
        """
        Captures the screen or a specific region.
        """
        try:
            screenshot = ImageGrab.grab(bbox=region)
            timestamp = int(time.time())
            filepath = os.path.join(self.storage_dir, f"vision_{timestamp}.png")
            screenshot.save(filepath)
            return filepath
        except Exception as e:
            print(f"[Vision Error] Capture failed: {e}")
            return None

    def analyze_context(self, prompt="what is on the screen?"):
        """
        High-level call to 'see' and describe the screen.
        In v4.0, this captures the screen and prepares context for the Brain.
        """
        img_path = self.capture_screen()
        if img_path:
            # For now, we return the path. 
            # In a full multimodal setup, we would send this to a Vision model.
            return f"[VISUAL CONTEXT CAPTURED: {img_path}]"
        return "[Vision Unavailable]"

if __name__ == "__main__":
    v = VisionEngine()
    print(f"Captured: {v.capture_screen()}")


