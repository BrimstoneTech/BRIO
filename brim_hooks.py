
import threading
import time
from typing import Callable, Optional
import ctypes

# Optional dependency: keyboard
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

# Windows cursor position helper
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_mouse_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

class BrioHooks:
    """
    Handles global OS interaction: Keyboard hooks, Mouse tracking, and Hotkeys.
    """
    def __init__(self, on_command_callback: Callable[[str], None]):
        self.on_command = on_command_callback
        self.is_explorative = False
        self._buffer = []
        self._last_key_time = 0
        self._is_active = True
        
    def start(self):
        """Initialize global hooks in a background thread"""
        if not HAS_KEYBOARD:
            print("[Hooks] Warning: 'keyboard' library not found. Global hooks disabled.")
            print("Run: pip install keyboard")
            return

        # 1. Explorative State Shortcut (Ctrl+Shift+B)
        keyboard.add_hotkey('ctrl+shift+b', self._toggle_explorative)
        
        # 2. Air-Typing Listener
        # We hook every key to detect "Air Typing" patterns
        keyboard.on_press(self._handle_keypress)
        
        print("[Hooks] Global Hotkeys Active (Ctrl+Shift+B to Toggle Exploration)")

    def _toggle_explorative(self):
        self.is_explorative = not self.is_explorative
        status = "ENABLED" if self.is_explorative else "DISABLED"
        print(f"[Hooks] Explorative State: {status}")

    def _handle_keypress(self, event):
        """Collect keystrokes for 'Air Typing'"""
        now = time.time()
        
        # If user stops typing for 2 seconds, we clear buffer
        if now - self._last_key_time > 2.0:
            self._buffer = []
            
        self._last_key_time = now
        
        if event.name == 'enter':
            command = "".join(self._buffer).strip()
            if command:
                self.on_command(command)
            self._buffer = []
        elif len(event.name) == 1: # Basic character
            self._buffer.append(event.name)
        elif event.name == 'space':
            self._buffer.append(" ")
        elif event.name == 'backspace' and self._buffer:
            self._buffer.pop()

    def get_context(self) -> dict:
        """Returns mouse and shortcut state for the main engine"""
        mx, my = get_mouse_pos()
        return {
            "mouse_x": mx,
            "mouse_y": my,
            "is_explorative": self.is_explorative
        }

if __name__ == "__main__":
    def mock_cmd(cmd):
        print(f"Brio received Air-Typing: {cmd}")
        
    hooks = BrioHooks(mock_cmd)
    hooks.start()
    
    # Stay alive for test
    try:
        while True:
            ctx = hooks.get_context()
            # print(f"Mouse: {ctx['mouse_x']}, {ctx['mouse_y']}")
            time.sleep(1)
    except KeyboardInterrupt:
        pass
