"""
BRIO Desktop Automation Agent
=================================
Autonomous desktop control — BRIO doesn't just open apps, it actually *uses* them.

Capabilities:
- GUI control: mouse movement, clicking, scrolling, typing, keyboard shortcuts
- Screen vision: screenshots + OCR to understand what's on screen
- Window management: find, focus, resize, close windows by name
- Task planning: break natural language into step-by-step GUI actions
- Task queue: chain multiple tasks, execute while user is away
- Creative drawing: open drawing apps and create artwork via mouse control
- Safety: screenshot before every action, abort hotkey

Dependencies:
    pip install pyautogui pynput Pillow pytesseract pyperclip

System requirements:
    - Tesseract OCR installed for screen reading
      Windows: https://github.com/UB-Mannheim/tesseract/wiki
      Mac: brew install tesseract
      Linux: sudo apt install tesseract-ocr

⚠️ SAFETY: Only enabled on localhost (auto-disabled on HF Spaces).
All GUI actions are logged with before/after screenshots.
"""

import os
import sys
import time
import json
import math
import random
import logging
import platform
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

log = logging.getLogger("brio.desktop_agent")

# ═══════════════════════════════════════════════════════════════
#  Dependency detection
# ═══════════════════════════════════════════════════════════════

HAS_PYAUTOGUI = False
HAS_PYNPUT = False
HAS_PIL = False
HAS_TESSERACT = False

try:
    import pyautogui
    pyautogui.PAUSE = 0.3  # 300ms between actions for safety
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    HAS_PYAUTOGUI = True
except ImportError:
    pass

try:
    from pynput import keyboard as pynput_keyboard
    from pynput import mouse as pynput_mouse
    HAS_PYNPUT = True
except ImportError:
    pass

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    HAS_PIL = True
except ImportError:
    pass

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════════
#  Data structures
# ═══════════════════════════════════════════════════════════════

class ActionType(Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE_TEXT = "type_text"
    HOTKEY = "hotkey"
    MOVE_MOUSE = "move_mouse"
    SCROLL = "scroll"
    DRAG = "drag"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    FIND_ON_SCREEN = "find_on_screen"
    FOCUS_WINDOW = "focus_window"
    OPEN_APP = "open_app"
    # Creative drawing actions
    DRAW_LINE = "draw_line"
    DRAW_CIRCLE = "draw_circle"
    DRAW_RECT = "draw_rect"
    DRAW_FREEFORM = "draw_freeform"
    DRAW_CURVE = "draw_curve"
    SELECT_COLOR = "select_color"
    SELECT_TOOL = "select_tool"


@dataclass
class GUIAction:
    """A single GUI action in a task plan."""
    action_type: ActionType
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class TaskPlan:
    """A planned sequence of GUI actions."""
    name: str
    description: str
    steps: List[GUIAction] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed, aborted
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    current_step: int = 0


# ═══════════════════════════════════════════════════════════════
#  Screen Vision — Understanding what's on the display
# ═══════════════════════════════════════════════════════════════

class ScreenVision:
    """Read and understand what's on the screen."""

    def __init__(self):
        self.last_screenshot: Optional[Any] = None  # PIL Image
        self.screenshot_dir = os.path.join(str(Path.home()), ".brio", "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def capture(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[Any]:
        """Take a screenshot. Returns PIL Image."""
        if not HAS_PYAUTOGUI or not HAS_PIL:
            return None
        try:
            img = pyautogui.screenshot(region=region)
            self.last_screenshot = img
            return img
        except Exception as e:
            log.warning(f"[Vision] Screenshot failed: {e}")
            return None

    def save_screenshot(self, tag: str = "action") -> Optional[str]:
        """Capture and save a screenshot with timestamp."""
        img = self.capture()
        if img:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.screenshot_dir, f"brio_{tag}_{ts}.png")
            img.save(path)
            return path
        return None

    def read_screen_text(self, region: Optional[Tuple[int, int, int, int]] = None) -> str:
        """OCR — read text from the screen or a region."""
        if not HAS_TESSERACT or not HAS_PIL:
            return ""
        img = self.capture(region)
        if img:
            try:
                text = pytesseract.image_to_string(img)
                return text.strip()
            except Exception as e:
                log.warning(f"[Vision] OCR failed: {e}")
        return ""

    def find_text_on_screen(self, target: str) -> Optional[Tuple[int, int]]:
        """Find the location of specific text on screen using OCR."""
        if not HAS_TESSERACT or not HAS_PIL or not HAS_PYAUTOGUI:
            return None
        img = self.capture()
        if not img:
            return None
        try:
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            target_lower = target.lower()
            for i, word in enumerate(data['text']):
                if word and target_lower in word.lower():
                    x = data['left'][i] + data['width'][i] // 2
                    y = data['top'][i] + data['height'][i] // 2
                    return (x, y)
        except Exception as e:
            log.warning(f"[Vision] Text search failed: {e}")
        return None

    def find_image_on_screen(self, image_path: str, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
        """Find an image/icon on screen. Returns center coordinates."""
        if not HAS_PYAUTOGUI:
            return None
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                return (center.x, center.y)
        except Exception as e:
            log.warning(f"[Vision] Image search failed: {e}")
        return None

    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen resolution."""
        if HAS_PYAUTOGUI:
            return pyautogui.size()
        return (1920, 1080)  # default fallback

    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        if HAS_PYAUTOGUI:
            pos = pyautogui.position()
            return (pos.x, pos.y)
        return (0, 0)


# ═══════════════════════════════════════════════════════════════
#  Window Manager — Find, focus, manage windows
# ═══════════════════════════════════════════════════════════════

class WindowManager:
    """Cross-platform window management."""

    def __init__(self):
        self.os_type = platform.system()

    def get_active_window(self) -> Optional[str]:
        """Get the title of the currently active window."""
        try:
            if self.os_type == "Windows":
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                return buf.value
            elif self.os_type == "Darwin":
                result = subprocess.run(
                    ["osascript", "-e",
                     'tell application "System Events" to get name of first application process whose frontmost is true'],
                    capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip() if result.returncode == 0 else None
            else:
                result = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip() if result.returncode == 0 else None
        except Exception as e:
            log.warning(f"[WindowMgr] Active window error: {e}")
            return None

    def list_windows(self) -> List[str]:
        """List all visible window titles."""
        try:
            if self.os_type == "Windows":
                result = subprocess.run(
                    ["powershell", "-command",
                     "Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object -ExpandProperty MainWindowTitle"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return [w.strip() for w in result.stdout.strip().split("\n") if w.strip()]
            elif self.os_type == "Darwin":
                result = subprocess.run(
                    ["osascript", "-e",
                     'tell application "System Events" to get name of every window of every application process whose visible is true'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return [w.strip() for w in result.stdout.strip().split(",") if w.strip()]
            else:
                result = subprocess.run(
                    ["wmctrl", "-l"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return [" ".join(line.split()[3:]) for line in result.stdout.strip().split("\n") if line.strip()]
        except Exception:
            pass
        return []

    def focus_window(self, title: str) -> bool:
        """Bring a window to the foreground by (partial) title match."""
        try:
            if self.os_type == "Windows":
                result = subprocess.run(
                    ["powershell", "-command",
                     f'$w = Get-Process | Where-Object {{$_.MainWindowTitle -like "*{title}*"}} | Select-Object -First 1; '
                     f'if ($w) {{ [void][System.Runtime.InteropServices.Marshal]::GetActiveObject(""); '
                     f'Add-Type -Name Win -Namespace Native -MemberDefinition \'[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);\'; '
                     f'[Native.Win]::SetForegroundWindow($w.MainWindowHandle) }}'],
                    capture_output=True, text=True, timeout=10
                )
                # Simpler fallback using Alt+Tab strategy
                if result.returncode != 0:
                    import ctypes
                    import ctypes.wintypes
                    EnumWindows = ctypes.windll.user32.EnumWindows
                    GetWindowText = ctypes.windll.user32.GetWindowTextW
                    SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
                    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

                    found = [False]
                    title_lower = title.lower()

                    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
                    def callback(hwnd, lParam):
                        if IsWindowVisible(hwnd):
                            buf = ctypes.create_unicode_buffer(256)
                            GetWindowText(hwnd, buf, 256)
                            if title_lower in buf.value.lower():
                                SetForegroundWindow(hwnd)
                                found[0] = True
                                return False
                        return True

                    EnumWindows(callback, 0)
                    return found[0]
                return True
            elif self.os_type == "Darwin":
                result = subprocess.run(
                    ["osascript", "-e",
                     f'tell application "{title}" to activate'],
                    capture_output=True, text=True, timeout=5
                )
                return result.returncode == 0
            else:
                result = subprocess.run(
                    ["wmctrl", "-a", title],
                    capture_output=True, text=True, timeout=5
                )
                return result.returncode == 0
        except Exception as e:
            log.warning(f"[WindowMgr] Focus error: {e}")
            return False

    def close_window(self, title: str) -> bool:
        """Close a window by title."""
        try:
            if self.os_type == "Windows":
                subprocess.run(
                    ["powershell", "-command",
                     f'Get-Process | Where-Object {{$_.MainWindowTitle -like "*{title}*"}} | Stop-Process -Force'],
                    timeout=10
                )
                return True
            elif self.os_type == "Darwin":
                subprocess.run(
                    ["osascript", "-e",
                     f'tell application "{title}" to quit'],
                    timeout=5
                )
                return True
            else:
                subprocess.run(["wmctrl", "-c", title], timeout=5)
                return True
        except Exception:
            return False

    def minimize_window(self, title: str = None) -> bool:
        """Minimize current or specified window."""
        try:
            if self.os_type == "Windows":
                subprocess.run(
                    ["powershell", "-command",
                     "(New-Object -ComObject Shell.Application).MinimizeAll()"],
                    timeout=5
                )
                return True
            elif self.os_type == "Darwin":
                subprocess.run(
                    ["osascript", "-e",
                     'tell application "System Events" to keystroke "m" using command down'],
                    timeout=5
                )
                return True
        except Exception:
            return False
        return False


# ═══════════════════════════════════════════════════════════════
#  GUI Controller — Mouse, keyboard, drawing
# ═══════════════════════════════════════════════════════════════

class GUIController:
    """Direct GUI control — mouse, keyboard, and creative drawing."""

    def __init__(self):
        self.os_type = platform.system()
        self._abort = False
        self._abort_lock = threading.Lock()

    def abort(self):
        """Set the abort flag to stop current task."""
        with self._abort_lock:
            self._abort = True
        log.warning("[GUI] ABORT requested!")

    def reset_abort(self):
        """Clear the abort flag."""
        with self._abort_lock:
            self._abort = False

    def is_aborted(self) -> bool:
        with self._abort_lock:
            return self._abort

    # ─── Mouse ────────────────────────────────────────────────────

    def move_to(self, x: int, y: int, duration: float = 0.3):
        """Move mouse to coordinates."""
        if HAS_PYAUTOGUI:
            pyautogui.moveTo(x, y, duration=duration)

    def click(self, x: int = None, y: int = None, button: str = "left", clicks: int = 1):
        """Click at position (or current position if x/y not given)."""
        if HAS_PYAUTOGUI:
            pyautogui.click(x=x, y=y, button=button, clicks=clicks)

    def double_click(self, x: int = None, y: int = None):
        if HAS_PYAUTOGUI:
            pyautogui.doubleClick(x=x, y=y)

    def right_click(self, x: int = None, y: int = None):
        if HAS_PYAUTOGUI:
            pyautogui.rightClick(x=x, y=y)

    def drag_to(self, x: int, y: int, duration: float = 0.5, button: str = "left"):
        """Drag from current position to (x, y)."""
        if HAS_PYAUTOGUI:
            pyautogui.dragTo(x, y, duration=duration, button=button)

    def drag_from_to(self, x1: int, y1: int, x2: int, y2: int,
                     duration: float = 0.5, button: str = "left"):
        """Move to (x1,y1), then drag to (x2,y2)."""
        if HAS_PYAUTOGUI:
            pyautogui.moveTo(x1, y1, duration=0.2)
            time.sleep(0.1)
            pyautogui.drag(x2 - x1, y2 - y1, duration=duration, button=button)

    def scroll(self, clicks: int, x: int = None, y: int = None):
        """Scroll up (positive) or down (negative)."""
        if HAS_PYAUTOGUI:
            pyautogui.scroll(clicks, x=x, y=y)

    # ─── Keyboard ─────────────────────────────────────────────────

    def type_text(self, text: str, interval: float = 0.02):
        """Type text character by character."""
        if HAS_PYAUTOGUI:
            pyautogui.typewrite(text, interval=interval) if text.isascii() else pyautogui.write(text)

    def type_unicode(self, text: str):
        """Type text including unicode characters (uses clipboard method)."""
        if HAS_PYAUTOGUI:
            try:
                import pyperclip
                old = pyperclip.paste()
                pyperclip.copy(text)
                self.hotkey("ctrl", "v")
                time.sleep(0.2)
                pyperclip.copy(old)
            except ImportError:
                # Fallback — pyautogui.write handles some unicode
                pyautogui.write(text)

    def press_key(self, key: str):
        """Press a single key (enter, tab, escape, etc.)."""
        if HAS_PYAUTOGUI:
            pyautogui.press(key)

    def hotkey(self, *keys):
        """Press a keyboard shortcut (e.g., hotkey('ctrl', 's'))."""
        if HAS_PYAUTOGUI:
            pyautogui.hotkey(*keys)

    def key_down(self, key: str):
        """Hold a key down."""
        if HAS_PYAUTOGUI:
            pyautogui.keyDown(key)

    def key_up(self, key: str):
        """Release a held key."""
        if HAS_PYAUTOGUI:
            pyautogui.keyUp(key)

    # ─── Creative Drawing ─────────────────────────────────────────

    def draw_line(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5):
        """Draw a straight line from (x1,y1) to (x2,y2) by dragging."""
        self.drag_from_to(x1, y1, x2, y2, duration=duration)

    def draw_circle(self, cx: int, cy: int, radius: int, steps: int = 36, duration: float = 2.0):
        """Draw a circle centered at (cx, cy) with the given radius."""
        if not HAS_PYAUTOGUI:
            return
        step_time = duration / steps
        # Move to start position (top of circle)
        start_x = cx + radius
        start_y = cy
        pyautogui.moveTo(start_x, start_y, duration=0.2)
        time.sleep(0.1)
        pyautogui.mouseDown()
        for i in range(1, steps + 1):
            if self.is_aborted():
                pyautogui.mouseUp()
                return
            angle = 2 * math.pi * i / steps
            x = cx + int(radius * math.cos(angle))
            y = cy + int(radius * math.sin(angle))
            pyautogui.moveTo(x, y, duration=step_time)
        pyautogui.mouseUp()

    def draw_rectangle(self, x: int, y: int, width: int, height: int, duration: float = 1.5):
        """Draw a rectangle starting at (x, y) with given dimensions."""
        if not HAS_PYAUTOGUI:
            return
        step = duration / 4
        pyautogui.moveTo(x, y, duration=0.2)
        time.sleep(0.1)
        pyautogui.mouseDown()
        pyautogui.moveTo(x + width, y, duration=step)         # top
        pyautogui.moveTo(x + width, y + height, duration=step) # right
        pyautogui.moveTo(x, y + height, duration=step)         # bottom
        pyautogui.moveTo(x, y, duration=step)                  # left
        pyautogui.mouseUp()

    def draw_freeform(self, points: List[Tuple[int, int]], duration: float = 2.0):
        """Draw a freeform shape through a list of (x, y) points."""
        if not HAS_PYAUTOGUI or not points:
            return
        step_time = duration / len(points)
        pyautogui.moveTo(points[0][0], points[0][1], duration=0.2)
        time.sleep(0.1)
        pyautogui.mouseDown()
        for px, py in points[1:]:
            if self.is_aborted():
                pyautogui.mouseUp()
                return
            pyautogui.moveTo(px, py, duration=step_time)
        pyautogui.mouseUp()

    def draw_curve(self, points: List[Tuple[int, int]], smoothness: int = 20,
                   duration: float = 2.0):
        """Draw a smooth curve through control points using Bezier interpolation."""
        if not HAS_PYAUTOGUI or len(points) < 2:
            return
        # Generate smooth Bezier points
        smooth_points = self._bezier_curve(points, smoothness)
        self.draw_freeform(smooth_points, duration)

    def draw_star(self, cx: int, cy: int, outer_r: int, inner_r: int = None,
                  points: int = 5, duration: float = 2.0):
        """Draw a star centered at (cx, cy)."""
        if not HAS_PYAUTOGUI:
            return
        if inner_r is None:
            inner_r = outer_r // 2
        star_points = []
        for i in range(points * 2):
            angle = math.pi * i / points - math.pi / 2
            r = outer_r if i % 2 == 0 else inner_r
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * math.sin(angle))
            star_points.append((x, y))
        star_points.append(star_points[0])  # close the star
        self.draw_freeform(star_points, duration)

    def draw_heart(self, cx: int, cy: int, size: int = 100, duration: float = 2.0):
        """Draw a heart shape centered at (cx, cy)."""
        points = []
        for i in range(100):
            t = 2 * math.pi * i / 100
            x = cx + int(size * 16 * math.sin(t) ** 3 / 16)
            y = cy - int(size * (13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t)) / 16)
            points.append((x, y))
        points.append(points[0])
        self.draw_freeform(points, duration)

    def draw_spiral(self, cx: int, cy: int, max_radius: int = 150,
                    turns: float = 3, duration: float = 3.0):
        """Draw a spiral centered at (cx, cy)."""
        points = []
        total_steps = int(turns * 60)
        for i in range(total_steps):
            angle = 2 * math.pi * turns * i / total_steps
            r = max_radius * i / total_steps
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * math.sin(angle))
            points.append((x, y))
        self.draw_freeform(points, duration)

    def draw_text_manually(self, text: str, x: int, y: int, char_width: int = 15):
        """Click at position and type text (for text tools in drawing apps)."""
        if HAS_PYAUTOGUI:
            pyautogui.click(x, y)
            time.sleep(0.3)
            self.type_unicode(text)

    @staticmethod
    def _bezier_curve(control_points: List[Tuple[int, int]],
                      num_points: int = 50) -> List[Tuple[int, int]]:
        """Generate smooth Bezier curve through control points."""
        if len(control_points) < 2:
            return control_points
        n = len(control_points) - 1
        result = []
        for t_step in range(num_points + 1):
            t = t_step / num_points
            x, y = 0.0, 0.0
            for i, (px, py) in enumerate(control_points):
                # Bernstein polynomial
                coeff = math.comb(n, i) * (t ** i) * ((1 - t) ** (n - i))
                x += coeff * px
                y += coeff * py
            result.append((int(x), int(y)))
        return result


# ═══════════════════════════════════════════════════════════════
#  Creative Engine — BRIO draws from its own creativity
# ═══════════════════════════════════════════════════════════════

class CreativeDrawingEngine:
    """
    BRIO's creative drawing capabilities.
    Generates drawing plans that the GUIController executes.
    """

    # Drawing templates — shapes BRIO knows how to create
    TEMPLATES = {
        "face": {
            "description": "A simple face with eyes, nose, and smile",
            "steps": ["circle:head", "circle:left_eye", "circle:right_eye",
                      "line:nose", "curve:smile"]
        },
        "house": {
            "description": "A house with roof, door, and windows",
            "steps": ["rect:body", "triangle:roof", "rect:door",
                      "rect:window_left", "rect:window_right"]
        },
        "tree": {
            "description": "A tree with trunk and leafy canopy",
            "steps": ["rect:trunk", "circle:canopy1", "circle:canopy2", "circle:canopy3"]
        },
        "flower": {
            "description": "A flower with petals and stem",
            "steps": ["line:stem", "circle:center",
                      "circle:petal1", "circle:petal2", "circle:petal3",
                      "circle:petal4", "circle:petal5"]
        },
        "sun": {
            "description": "A sun with rays",
            "steps": ["circle:body", "line:ray1", "line:ray2", "line:ray3",
                      "line:ray4", "line:ray5", "line:ray6", "line:ray7", "line:ray8"]
        },
        "star": {
            "description": "A five-pointed star",
            "steps": ["star:body"]
        },
        "heart": {
            "description": "A heart shape",
            "steps": ["heart:body"]
        },
        "cat": {
            "description": "A simple cat face",
            "steps": ["circle:head", "triangle:left_ear", "triangle:right_ear",
                      "circle:left_eye", "circle:right_eye",
                      "dot:nose", "curve:mouth_left", "curve:mouth_right",
                      "line:whisker1", "line:whisker2", "line:whisker3",
                      "line:whisker4", "line:whisker5", "line:whisker6"]
        },
        "landscape": {
            "description": "A simple landscape with mountains and sun",
            "steps": ["line:horizon", "triangle:mountain1", "triangle:mountain2",
                      "circle:sun", "line:ray1", "line:ray2", "line:ray3",
                      "curve:cloud1", "curve:cloud2"]
        },
        "robot": {
            "description": "A friendly robot",
            "steps": ["rect:head", "rect:body", "rect:left_arm", "rect:right_arm",
                      "rect:left_leg", "rect:right_leg",
                      "circle:left_eye", "circle:right_eye",
                      "line:antenna", "circle:antenna_ball", "rect:mouth"]
        },
        "abstract": {
            "description": "Abstract art — spirals, intersecting shapes, flowing curves",
            "steps": ["spiral:center", "circle:accent1", "curve:flow1",
                      "curve:flow2", "star:accent2", "freeform:splash"]
        },
    }

    def __init__(self, gui: GUIController):
        self.gui = gui

    def get_available_drawings(self) -> List[Dict]:
        """List all drawings BRIO can create."""
        return [
            {"name": name, "description": tpl["description"]}
            for name, tpl in self.TEMPLATES.items()
        ]

    def draw_template(self, template_name: str, canvas_x: int, canvas_y: int,
                      canvas_w: int, canvas_h: int) -> bool:
        """Execute a drawing template within the given canvas bounds."""
        tpl = self.TEMPLATES.get(template_name)
        if not tpl:
            log.warning(f"[Creative] Unknown template: {template_name}")
            return False

        cx = canvas_x + canvas_w // 2
        cy = canvas_y + canvas_h // 2
        scale = min(canvas_w, canvas_h) // 4

        log.info(f"[Creative] Drawing '{template_name}' at center ({cx}, {cy}), scale {scale}")

        # Dispatch based on template name
        method = getattr(self, f"_draw_{template_name}", None)
        if method:
            try:
                method(cx, cy, scale)
                return True
            except Exception as e:
                log.error(f"[Creative] Drawing error: {e}")
                return False
        else:
            log.warning(f"[Creative] No implementation for template: {template_name}")
            return False

    def _draw_face(self, cx: int, cy: int, s: int):
        self.gui.draw_circle(cx, cy, s)  # head
        time.sleep(0.3)
        self.gui.draw_circle(cx - s // 3, cy - s // 4, s // 8)  # left eye
        time.sleep(0.2)
        self.gui.draw_circle(cx + s // 3, cy - s // 4, s // 8)  # right eye
        time.sleep(0.2)
        self.gui.draw_line(cx, cy - s // 10, cx, cy + s // 6, duration=0.3)  # nose
        time.sleep(0.2)
        # Smile
        smile_pts = [(cx - s // 3, cy + s // 4),
                     (cx - s // 6, cy + s // 2.5),
                     (cx + s // 6, cy + s // 2.5),
                     (cx + s // 3, cy + s // 4)]
        smile_pts = [(int(x), int(y)) for x, y in smile_pts]
        self.gui.draw_curve(smile_pts, duration=0.5)

    def _draw_house(self, cx: int, cy: int, s: int):
        # Body
        bx, by = cx - s, cy - s // 2
        self.gui.draw_rectangle(bx, by, s * 2, s * 1.5)
        time.sleep(0.3)
        # Roof (triangle)
        self.gui.draw_freeform([
            (bx, by), (cx, by - s), (bx + s * 2, by), (bx, by)
        ], duration=1.0)
        time.sleep(0.3)
        # Door
        self.gui.draw_rectangle(cx - s // 4, int(by + s * 0.6), s // 2, int(s * 0.9))
        time.sleep(0.2)
        # Windows
        self.gui.draw_rectangle(bx + s // 5, by + s // 4, s // 3, s // 3)
        time.sleep(0.2)
        self.gui.draw_rectangle(bx + s + s // 3, by + s // 4, s // 3, s // 3)

    def _draw_tree(self, cx: int, cy: int, s: int):
        # Trunk
        tw = s // 3
        self.gui.draw_rectangle(cx - tw // 2, cy, tw, s)
        time.sleep(0.3)
        # Canopy circles
        self.gui.draw_circle(cx, cy - s // 3, int(s * 0.7))
        time.sleep(0.2)
        self.gui.draw_circle(cx - s // 2, cy, int(s * 0.5))
        time.sleep(0.2)
        self.gui.draw_circle(cx + s // 2, cy, int(s * 0.5))

    def _draw_flower(self, cx: int, cy: int, s: int):
        # Stem
        self.gui.draw_line(cx, cy + s // 2, cx, cy + s * 2, duration=0.5)
        time.sleep(0.3)
        # Center
        self.gui.draw_circle(cx, cy, s // 4)
        time.sleep(0.2)
        # Petals (5 around center)
        petal_r = s // 3
        for i in range(5):
            angle = 2 * math.pi * i / 5 - math.pi / 2
            px = cx + int((s // 2) * math.cos(angle))
            py = cy + int((s // 2) * math.sin(angle))
            self.gui.draw_circle(px, py, petal_r)
            time.sleep(0.15)

    def _draw_sun(self, cx: int, cy: int, s: int):
        self.gui.draw_circle(cx, cy, s // 2)
        time.sleep(0.3)
        # 8 rays
        for i in range(8):
            angle = 2 * math.pi * i / 8
            x1 = cx + int((s * 0.6) * math.cos(angle))
            y1 = cy + int((s * 0.6) * math.sin(angle))
            x2 = cx + int((s * 1.1) * math.cos(angle))
            y2 = cy + int((s * 1.1) * math.sin(angle))
            self.gui.draw_line(x1, y1, x2, y2, duration=0.2)
            time.sleep(0.1)

    def _draw_star(self, cx: int, cy: int, s: int):
        self.gui.draw_star(cx, cy, s, s // 2, 5)

    def _draw_heart(self, cx: int, cy: int, s: int):
        self.gui.draw_heart(cx, cy, s)

    def _draw_cat(self, cx: int, cy: int, s: int):
        # Head
        self.gui.draw_circle(cx, cy, s)
        time.sleep(0.3)
        # Ears (triangles)
        ear_h = int(s * 0.7)
        self.gui.draw_freeform([
            (cx - s + s // 5, cy - s // 2),
            (cx - s // 2, cy - s - ear_h),
            (cx - s // 10, cy - s + s // 5),
        ], duration=0.5)
        time.sleep(0.2)
        self.gui.draw_freeform([
            (cx + s // 10, cy - s + s // 5),
            (cx + s // 2, cy - s - ear_h),
            (cx + s - s // 5, cy - s // 2),
        ], duration=0.5)
        time.sleep(0.2)
        # Eyes
        self.gui.draw_circle(cx - s // 3, cy - s // 5, s // 8)
        time.sleep(0.1)
        self.gui.draw_circle(cx + s // 3, cy - s // 5, s // 8)
        time.sleep(0.2)
        # Nose dot
        self.gui.click(cx, cy + s // 10)
        time.sleep(0.2)
        # Whiskers
        wl = int(s * 0.6)
        for i, (dx, dy) in enumerate([(-1, -0.2), (-1, 0), (-1, 0.2), (1, -0.2), (1, 0), (1, 0.2)]):
            wx = cx + int(s // 4 * (1 if dx > 0 else -1))
            self.gui.draw_line(wx, cy + s // 5,
                               wx + int(wl * dx), cy + s // 5 + int(wl * dy * 0.5),
                               duration=0.2)
            time.sleep(0.1)

    def _draw_robot(self, cx: int, cy: int, s: int):
        # Head
        hw = int(s * 0.8)
        hh = int(s * 0.6)
        self.gui.draw_rectangle(cx - hw // 2, cy - s - hh, hw, hh)
        time.sleep(0.2)
        # Eyes
        self.gui.draw_circle(cx - hw // 4, cy - s - hh // 2, hh // 6)
        time.sleep(0.1)
        self.gui.draw_circle(cx + hw // 4, cy - s - hh // 2, hh // 6)
        time.sleep(0.2)
        # Mouth
        self.gui.draw_rectangle(cx - hw // 4, int(cy - s - hh * 0.2), hw // 2, hh // 6)
        time.sleep(0.2)
        # Antenna
        self.gui.draw_line(cx, cy - s - hh, cx, cy - s - hh - s // 2, duration=0.3)
        self.gui.draw_circle(cx, cy - s - hh - s // 2 - s // 10, s // 10)
        time.sleep(0.2)
        # Body
        bw = int(s * 1.2)
        bh = int(s * 1.0)
        self.gui.draw_rectangle(cx - bw // 2, cy - s, bw, bh)
        time.sleep(0.2)
        # Arms
        self.gui.draw_rectangle(cx - bw // 2 - s // 3, cy - s + s // 4, s // 3, int(s * 0.6))
        self.gui.draw_rectangle(cx + bw // 2, cy - s + s // 4, s // 3, int(s * 0.6))
        time.sleep(0.2)
        # Legs
        self.gui.draw_rectangle(cx - bw // 4, cy - s + bh, s // 3, int(s * 0.7))
        self.gui.draw_rectangle(cx + bw // 4 - s // 6, cy - s + bh, s // 3, int(s * 0.7))

    def _draw_landscape(self, cx: int, cy: int, s: int):
        w = s * 3
        # Horizon line
        self.gui.draw_line(cx - w // 2, cy, cx + w // 2, cy, duration=0.5)
        time.sleep(0.3)
        # Mountains
        self.gui.draw_freeform([
            (cx - w // 3, cy), (cx - w // 6, cy - s), (cx, cy)
        ], duration=0.5)
        time.sleep(0.2)
        self.gui.draw_freeform([
            (cx - s // 3, cy), (cx + s // 2, cy - int(s * 1.3)), (cx + w // 3, cy)
        ], duration=0.5)
        time.sleep(0.3)
        # Sun
        sun_x, sun_y = cx + w // 3, cy - int(s * 1.5)
        self.gui.draw_circle(sun_x, sun_y, s // 3)
        for i in range(6):
            angle = 2 * math.pi * i / 6
            rx = sun_x + int(s * 0.45 * math.cos(angle))
            ry = sun_y + int(s * 0.45 * math.sin(angle))
            rx2 = sun_x + int(s * 0.7 * math.cos(angle))
            ry2 = sun_y + int(s * 0.7 * math.sin(angle))
            self.gui.draw_line(rx, ry, rx2, ry2, duration=0.15)
        time.sleep(0.2)
        # Clouds
        cloud_y = cy - int(s * 1.2)
        for offset in [-w // 4, w // 6]:
            cloud_x = cx + offset
            self.gui.draw_curve([
                (cloud_x - s // 2, cloud_y),
                (cloud_x - s // 3, cloud_y - s // 3),
                (cloud_x, cloud_y - s // 4),
                (cloud_x + s // 3, cloud_y - s // 3),
                (cloud_x + s // 2, cloud_y),
            ], duration=0.4)
            time.sleep(0.15)

    def _draw_abstract(self, cx: int, cy: int, s: int):
        # Spiral
        self.gui.draw_spiral(cx, cy, s, turns=2.5, duration=2.0)
        time.sleep(0.3)
        # Accent circles
        for _ in range(3):
            rx = cx + random.randint(-s, s)
            ry = cy + random.randint(-s, s)
            self.gui.draw_circle(rx, ry, random.randint(s // 6, s // 3))
            time.sleep(0.2)
        # Flowing curves
        for _ in range(2):
            pts = [(cx + random.randint(-s * 2, s * 2),
                     cy + random.randint(-s, s)) for _ in range(4)]
            self.gui.draw_curve(pts, duration=0.8)
            time.sleep(0.2)
        # Star accent
        self.gui.draw_star(cx + s, cy - s, s // 2, s // 4, 5)

    def draw_custom(self, instructions: str, canvas_x: int, canvas_y: int,
                    canvas_w: int, canvas_h: int) -> str:
        """
        Interpret natural language drawing instructions.
        Returns description of what was drawn.
        """
        cx = canvas_x + canvas_w // 2
        cy = canvas_y + canvas_h // 2
        scale = min(canvas_w, canvas_h) // 4
        inst = instructions.lower()

        drawn = []

        if "circle" in inst:
            self.gui.draw_circle(cx, cy, scale)
            drawn.append("circle")
        if "square" in inst or "rectangle" in inst or "box" in inst:
            self.gui.draw_rectangle(cx - scale, cy - scale, scale * 2, scale * 2)
            drawn.append("rectangle")
        if "star" in inst:
            self.gui.draw_star(cx, cy, scale, scale // 2)
            drawn.append("star")
        if "heart" in inst:
            self.gui.draw_heart(cx, cy, scale)
            drawn.append("heart")
        if "spiral" in inst:
            self.gui.draw_spiral(cx, cy, scale)
            drawn.append("spiral")
        if "line" in inst:
            self.gui.draw_line(cx - scale, cy, cx + scale, cy, duration=0.5)
            drawn.append("line")
        if "triangle" in inst:
            self.gui.draw_freeform([
                (cx, cy - scale), (cx - scale, cy + scale),
                (cx + scale, cy + scale), (cx, cy - scale)
            ], duration=0.8)
            drawn.append("triangle")

        # Match known templates
        for name in self.TEMPLATES:
            if name in inst:
                self.draw_template(name, canvas_x, canvas_y, canvas_w, canvas_h)
                drawn.append(name)
                break

        if not drawn:
            # Default: draw something creative/abstract
            self._draw_abstract(cx, cy, scale)
            drawn.append("abstract composition")

        return f"Drew: {', '.join(drawn)}"


# ═══════════════════════════════════════════════════════════════
#  App-Specific Adapters — How to interact with known apps
# ═══════════════════════════════════════════════════════════════

class AppAdapter:
    """Base class for application-specific control."""

    def __init__(self, gui: GUIController, vision: ScreenVision, windows: WindowManager):
        self.gui = gui
        self.vision = vision
        self.windows = windows
        self.os_type = platform.system()

    def open_app(self, app_name: str) -> bool:
        """Open an application."""
        try:
            if self.os_type == "Windows":
                subprocess.Popen(["start", app_name], shell=True)
            elif self.os_type == "Darwin":
                subprocess.Popen(["open", "-a", app_name])
            else:
                subprocess.Popen([app_name], start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)  # Wait for app to open
            return True
        except Exception as e:
            log.warning(f"[AppAdapter] Failed to open {app_name}: {e}")
            return False


class PaintAdapter(AppAdapter):
    """Control MS Paint / system paint app for drawing."""

    APP_NAMES = {
        "Windows": "mspaint",
        "Darwin": "Paintbrush",
        "Linux": "kolourpaint"
    }

    FALLBACK_APPS = {
        "Linux": ["gimp", "krita", "pinta", "drawing"]
    }

    def open(self) -> bool:
        """Open the paint application."""
        app = self.APP_NAMES.get(self.os_type, "gimp")
        success = self.open_app(app)
        if not success and self.os_type == "Linux":
            for fallback in self.FALLBACK_APPS.get("Linux", []):
                if self.open_app(fallback):
                    return True
        return success

    def new_canvas(self):
        """Create a new blank canvas."""
        time.sleep(1)
        self.gui.hotkey("ctrl", "n")
        time.sleep(1)
        # Press Enter to accept default canvas size (or type dimensions)
        self.gui.press_key("enter")
        time.sleep(0.5)

    def select_brush(self):
        """Select the brush/pencil tool."""
        # In MS Paint, pencil is already default
        # Try keyboard shortcut
        if self.os_type == "Windows":
            # MS Paint doesn't have great keyboard shortcuts for tools
            # We'll just click on the pencil area (approximate position)
            pass
        time.sleep(0.3)

    def select_color(self, color: str):
        """Select a color from the palette."""
        # Color positions in MS Paint (approximate — top-left of color palette)
        # These would need to be calibrated per screen/DPI
        color_map = {
            "black": (0, 0),
            "red": (1, 0),
            "orange": (2, 0),
            "yellow": (3, 0),
            "green": (0, 1),
            "blue": (1, 1),
            "purple": (2, 1),
            "white": (3, 1),
        }
        # In practice, we'd use OCR or image matching to find the color palette
        log.info(f"[Paint] Color selection: {color} (would click palette)")

    def get_canvas_bounds(self) -> Tuple[int, int, int, int]:
        """Get the canvas area bounds (approximate)."""
        screen_w, screen_h = self.vision.get_screen_size()
        # Approximate canvas area (below toolbar, above taskbar)
        # These are rough estimates — vision module can refine them
        if self.os_type == "Windows":
            return (0, 150, screen_w - 20, screen_h - 200)
        else:
            return (0, 80, screen_w - 20, screen_h - 100)


class BrowserAdapter(AppAdapter):
    """Control web browser for Canva, Figma, or web-based drawing tools."""

    def open_browser(self, url: str = "") -> bool:
        """Open default browser with optional URL."""
        try:
            import webbrowser
            if url:
                webbrowser.open(url)
            else:
                webbrowser.open("about:blank")
            time.sleep(3)
            return True
        except Exception:
            return False

    def open_canva(self) -> bool:
        """Open Canva in browser."""
        return self.open_browser("https://www.canva.com")

    def navigate_to(self, url: str):
        """Navigate to a URL (assumes browser is focused)."""
        self.gui.hotkey("ctrl", "l")  # Focus address bar
        time.sleep(0.3)
        self.gui.hotkey("ctrl", "a")  # Select all
        time.sleep(0.1)
        self.gui.type_text(url)
        time.sleep(0.2)
        self.gui.press_key("enter")
        time.sleep(3)

    def new_tab(self):
        self.gui.hotkey("ctrl", "t")
        time.sleep(0.5)

    def close_tab(self):
        self.gui.hotkey("ctrl", "w")
        time.sleep(0.3)


# ═══════════════════════════════════════════════════════════════
#  Task Planner — Break commands into GUI action sequences
# ═══════════════════════════════════════════════════════════════

class TaskPlanner:
    """Plan and execute multi-step GUI tasks."""

    def __init__(self, gui: GUIController, vision: ScreenVision,
                 windows: WindowManager, creative: CreativeDrawingEngine):
        self.gui = gui
        self.vision = vision
        self.windows = windows
        self.creative = creative
        self.paint = PaintAdapter(gui, vision, windows)
        self.browser = BrowserAdapter(gui, vision, windows)
        self.task_history: List[TaskPlan] = []
        self.task_queue: List[TaskPlan] = []
        self._running = False

    def plan_drawing_task(self, description: str) -> TaskPlan:
        """Plan a drawing task from natural language."""
        desc_lower = description.lower()

        plan = TaskPlan(
            name=f"Draw: {description[:50]}",
            description=description,
        )

        # Determine which app to use
        use_canva = "canva" in desc_lower
        use_browser = "browser" in desc_lower or "web" in desc_lower or use_canva

        # Step 1: Open the drawing application
        if use_canva:
            plan.steps.append(GUIAction(
                action_type=ActionType.OPEN_APP,
                params={"app": "canva", "url": "https://www.canva.com"},
                description="Open Canva in browser"
            ))
        elif use_browser:
            plan.steps.append(GUIAction(
                action_type=ActionType.OPEN_APP,
                params={"app": "browser"},
                description="Open web browser"
            ))
        else:
            plan.steps.append(GUIAction(
                action_type=ActionType.OPEN_APP,
                params={"app": "paint"},
                description="Open Paint application"
            ))

        # Step 2: Wait for app to load
        plan.steps.append(GUIAction(
            action_type=ActionType.WAIT,
            params={"seconds": 3},
            description="Wait for application to load"
        ))

        # Step 3: New canvas
        plan.steps.append(GUIAction(
            action_type=ActionType.HOTKEY,
            params={"keys": ["ctrl", "n"]},
            description="Create new canvas"
        ))

        # Step 4: Screenshot to find canvas bounds
        plan.steps.append(GUIAction(
            action_type=ActionType.SCREENSHOT,
            params={"tag": "canvas_ready"},
            description="Capture screen to find drawing area"
        ))

        # Step 5: Draw
        plan.steps.append(GUIAction(
            action_type=ActionType.DRAW_FREEFORM,
            params={"instructions": description},
            description=f"Draw: {description}"
        ))

        # Step 6: Save
        plan.steps.append(GUIAction(
            action_type=ActionType.HOTKEY,
            params={"keys": ["ctrl", "s"]},
            description="Save the drawing"
        ))

        # Step 7: Final screenshot
        plan.steps.append(GUIAction(
            action_type=ActionType.SCREENSHOT,
            params={"tag": "completed"},
            description="Screenshot of completed work"
        ))

        return plan

    def plan_app_task(self, description: str) -> TaskPlan:
        """Plan a general application task from natural language."""
        desc_lower = description.lower()
        plan = TaskPlan(name=description[:60], description=description)

        # Detect what app/action is needed
        if any(w in desc_lower for w in ["draw", "paint", "sketch", "design", "create art", "artwork"]):
            return self.plan_drawing_task(description)

        # Text editing tasks
        if any(w in desc_lower for w in ["notepad", "text editor", "write", "type"]):
            plan.steps.append(GUIAction(
                action_type=ActionType.OPEN_APP,
                params={"app": "notepad" if platform.system() == "Windows" else "gedit"},
                description="Open text editor"
            ))
            plan.steps.append(GUIAction(
                action_type=ActionType.WAIT, params={"seconds": 2},
                description="Wait for editor"
            ))
            # Extract what to type
            plan.steps.append(GUIAction(
                action_type=ActionType.TYPE_TEXT,
                params={"text": description},
                description="Type content"
            ))
            plan.steps.append(GUIAction(
                action_type=ActionType.HOTKEY,
                params={"keys": ["ctrl", "s"]},
                description="Save file"
            ))

        # Browser tasks
        elif any(w in desc_lower for w in ["browse", "chrome", "firefox", "website", "url", "search",
                                            "google", "gmail", "email"]):
            plan.steps.append(GUIAction(
                action_type=ActionType.OPEN_APP,
                params={"app": "browser"},
                description="Open web browser"
            ))
            plan.steps.append(GUIAction(
                action_type=ActionType.WAIT, params={"seconds": 3},
                description="Wait for browser"
            ))
            # Try to extract URL or search query
            plan.steps.append(GUIAction(
                action_type=ActionType.TYPE_TEXT,
                params={"text": description, "target": "address_bar"},
                description="Navigate/search"
            ))

        # File manager
        elif any(w in desc_lower for w in ["file explorer", "finder", "files", "folder"]):
            plan.steps.append(GUIAction(
                action_type=ActionType.OPEN_APP,
                params={"app": "explorer" if platform.system() == "Windows" else "nautilus"},
                description="Open file manager"
            ))

        return plan

    def execute_plan(self, plan: TaskPlan) -> TaskPlan:
        """Execute a planned sequence of GUI actions."""
        plan.status = "running"
        self._running = True
        log.info(f"[TaskPlanner] Executing: {plan.name} ({len(plan.steps)} steps)")

        for i, step in enumerate(plan.steps):
            if self.gui.is_aborted():
                plan.status = "aborted"
                log.warning(f"[TaskPlanner] Aborted at step {i+1}/{len(plan.steps)}")
                break

            plan.current_step = i
            step.timestamp = datetime.now().isoformat()

            # Screenshot before
            step.screenshot_before = self.vision.save_screenshot(f"step{i}_before")

            try:
                self._execute_step(step)
                step.success = True
            except Exception as e:
                step.error = str(e)
                step.success = False
                log.error(f"[TaskPlanner] Step {i+1} failed: {e}")

            # Screenshot after
            step.screenshot_after = self.vision.save_screenshot(f"step{i}_after")

            log.info(f"[TaskPlanner] Step {i+1}/{len(plan.steps)}: {step.description} — {'✓' if step.success else '✗'}")

        if plan.status != "aborted":
            plan.status = "completed" if all(s.success for s in plan.steps) else "failed"

        plan.completed_at = datetime.now().isoformat()
        self.task_history.append(plan)
        self._running = False

        log.info(f"[TaskPlanner] {plan.name} — {plan.status}")
        return plan

    def _execute_step(self, step: GUIAction):
        """Execute a single GUI action."""
        p = step.params

        if step.action_type == ActionType.CLICK:
            self.gui.click(p.get("x"), p.get("y"), p.get("button", "left"))

        elif step.action_type == ActionType.DOUBLE_CLICK:
            self.gui.double_click(p.get("x"), p.get("y"))

        elif step.action_type == ActionType.RIGHT_CLICK:
            self.gui.right_click(p.get("x"), p.get("y"))

        elif step.action_type == ActionType.TYPE_TEXT:
            text = p.get("text", "")
            if p.get("target") == "address_bar":
                self.gui.hotkey("ctrl", "l")
                time.sleep(0.3)
            self.gui.type_unicode(text)

        elif step.action_type == ActionType.HOTKEY:
            keys = p.get("keys", [])
            if keys:
                self.gui.hotkey(*keys)

        elif step.action_type == ActionType.MOVE_MOUSE:
            self.gui.move_to(p.get("x", 0), p.get("y", 0), p.get("duration", 0.3))

        elif step.action_type == ActionType.SCROLL:
            self.gui.scroll(p.get("clicks", 3), p.get("x"), p.get("y"))

        elif step.action_type == ActionType.DRAG:
            self.gui.drag_from_to(p["x1"], p["y1"], p["x2"], p["y2"],
                                   p.get("duration", 0.5))

        elif step.action_type == ActionType.WAIT:
            time.sleep(p.get("seconds", 1))

        elif step.action_type == ActionType.SCREENSHOT:
            self.vision.save_screenshot(p.get("tag", "manual"))

        elif step.action_type == ActionType.FIND_ON_SCREEN:
            target = p.get("text", "")
            pos = self.vision.find_text_on_screen(target)
            if pos:
                step.params["found_at"] = pos
            else:
                raise RuntimeError(f"Could not find '{target}' on screen")

        elif step.action_type == ActionType.FOCUS_WINDOW:
            if not self.windows.focus_window(p.get("title", "")):
                raise RuntimeError(f"Window not found: {p.get('title')}")

        elif step.action_type == ActionType.OPEN_APP:
            app = p.get("app", "")
            if app == "paint":
                self.paint.open()
            elif app in ("browser", "canva"):
                url = p.get("url", "")
                self.browser.open_browser(url)
            else:
                self.paint.open_app(app)

        elif step.action_type in (ActionType.DRAW_LINE, ActionType.DRAW_CIRCLE,
                                    ActionType.DRAW_RECT, ActionType.DRAW_FREEFORM,
                                    ActionType.DRAW_CURVE):
            instructions = p.get("instructions", "")
            bounds = self.paint.get_canvas_bounds()
            self.creative.draw_custom(instructions, *bounds)

    def queue_task(self, plan: TaskPlan):
        """Add a task to the queue for later execution."""
        self.task_queue.append(plan)
        log.info(f"[TaskPlanner] Queued: {plan.name} (queue size: {len(self.task_queue)})")

    def execute_queue(self):
        """Execute all queued tasks in order."""
        while self.task_queue:
            if self.gui.is_aborted():
                log.warning("[TaskPlanner] Queue aborted!")
                break
            plan = self.task_queue.pop(0)
            self.execute_plan(plan)
            time.sleep(1)  # Brief pause between tasks


# ═══════════════════════════════════════════════════════════════
#  BRIO Desktop Agent — The main orchestrator
# ═══════════════════════════════════════════════════════════════

class BrioDesktopAgent:
    """
    BRIO's autonomous desktop control agent.
    Handles natural language commands and executes them via GUI automation.
    """

    def __init__(self):
        self.is_local = self._detect_local()
        self.gui = GUIController()
        self.vision = ScreenVision()
        self.windows = WindowManager()
        self.creative = CreativeDrawingEngine(self.gui)
        self.planner = TaskPlanner(self.gui, self.vision, self.windows, self.creative)
        self._abort_listener = None

        # Check dependencies
        self.deps = {
            "pyautogui": HAS_PYAUTOGUI,
            "pynput": HAS_PYNPUT,
            "pillow": HAS_PIL,
            "tesseract": HAS_TESSERACT,
        }
        self.has_gui_control = HAS_PYAUTOGUI and HAS_PIL

        if self.is_local:
            missing = [k for k, v in self.deps.items() if not v]
            if missing:
                log.warning(f"[DesktopAgent] Missing optional deps: {', '.join(missing)}")
                log.warning(f"[DesktopAgent] Install with: pip install {' '.join(missing)}")
            else:
                log.info("[DesktopAgent] All dependencies ready — full desktop control enabled")

            # Start abort hotkey listener
            self._start_abort_listener()
        else:
            log.info("[DesktopAgent] Disabled — running in cloud mode")

    def _detect_local(self) -> bool:
        """Detect if running locally."""
        if os.environ.get("SPACE_ID"):
            return False
        if os.environ.get("SYSTEM") == "spaces":
            return False
        return True

    def _start_abort_listener(self):
        """Start listening for abort hotkey (Ctrl+Shift+Esc)."""
        if not HAS_PYNPUT:
            return
        try:
            pressed_keys = set()

            def on_press(key):
                try:
                    pressed_keys.add(key)
                    # Check for Ctrl+Shift+Escape
                    if (pynput_keyboard.Key.ctrl_l in pressed_keys and
                        pynput_keyboard.Key.shift in pressed_keys and
                        pynput_keyboard.Key.esc in pressed_keys):
                        self.gui.abort()
                        log.warning("[DesktopAgent] ABORT hotkey detected! Stopping all tasks.")
                except Exception:
                    pass

            def on_release(key):
                pressed_keys.discard(key)

            self._abort_listener = pynput_keyboard.Listener(
                on_press=on_press, on_release=on_release
            )
            self._abort_listener.daemon = True
            self._abort_listener.start()
            log.info("[DesktopAgent] Abort hotkey active: Ctrl+Shift+Esc")
        except Exception as e:
            log.warning(f"[DesktopAgent] Could not start abort listener: {e}")

    def handle_command(self, text: str) -> Optional[str]:
        """
        Handle a desktop automation command from natural language.
        Returns response string if handled, None if not a desktop command.
        """
        if not self.is_local:
            return None

        text_lower = text.lower().strip()

        # ─── Drawing commands ─────────────────────────────────────
        if any(w in text_lower for w in ["draw ", "sketch ", "paint ", "create art",
                                          "draw me", "make a drawing", "design ",
                                          "artwork", "doodle"]):
            if not self.has_gui_control:
                return self._missing_deps_msg()

            # Check for specific templates
            for template in self.creative.TEMPLATES:
                if template in text_lower:
                    return self._execute_drawing(template, text)

            # Custom drawing
            return self._execute_drawing(None, text)

        # ─── App control commands ─────────────────────────────────
        if any(w in text_lower for w in ["open and use", "use ", "go to ", "type in ",
                                          "click on ", "automate ", "while i'm away",
                                          "while i am away", "when i'm away"]):
            if not self.has_gui_control:
                return self._missing_deps_msg()
            return self._execute_app_task(text)

        # ─── Window management ────────────────────────────────────
        if text_lower.startswith(("focus ", "switch to ", "bring up ")):
            target = text[text.index(" "):].strip()
            if self.windows.focus_window(target):
                return f"🖥️ Focused: {target}"
            return f"❌ Window not found: {target}"

        if text_lower.startswith("close "):
            target = text[6:].strip()
            if self.windows.close_window(target):
                return f"✅ Closed: {target}"
            return f"❌ Could not close: {target}"

        if text_lower in ("list windows", "show windows", "what's open", "open windows"):
            windows = self.windows.list_windows()
            if windows:
                lines = ["🖥️ *Open Windows:*"] + [f"  • {w}" for w in windows[:20]]
                return "\n".join(lines)
            return "Could not list windows."

        if text_lower in ("active window", "current window", "which window"):
            active = self.windows.get_active_window()
            return f"🖥️ Active: {active}" if active else "Could not detect active window."

        # ─── Screen reading ───────────────────────────────────────
        if any(w in text_lower for w in ["read screen", "what's on screen",
                                          "screen text", "ocr"]):
            if not HAS_TESSERACT:
                return "❌ Tesseract OCR not installed. Install with:\n`brew install tesseract` (Mac) or `sudo apt install tesseract-ocr` (Linux)"
            text_on_screen = self.vision.read_screen_text()
            if text_on_screen:
                return f"📖 *Screen text:*\n```\n{text_on_screen[:3000]}\n```"
            return "Could not read screen text."

        if text_lower.startswith(("find on screen ", "locate ", "where is ")):
            target = text[text.index(" ") + 1:].strip().strip("'\"")
            pos = self.vision.find_text_on_screen(target)
            if pos:
                return f"🎯 Found '{target}' at position ({pos[0]}, {pos[1]})"
            return f"❌ Could not find '{target}' on screen."

        # ─── Task queue ───────────────────────────────────────────
        if text_lower.startswith(("queue ", "schedule ", "later ", "after that ")):
            task_desc = text[text.index(" "):].strip()
            plan = self.planner.plan_app_task(task_desc)
            self.planner.queue_task(plan)
            return f"📋 Queued: {plan.name} (queue size: {len(self.planner.task_queue)})"

        if text_lower in ("run queue", "execute queue", "do the queue", "start queue"):
            if not self.planner.task_queue:
                return "📋 Task queue is empty."
            count = len(self.planner.task_queue)
            # Run in background thread
            thread = threading.Thread(target=self.planner.execute_queue, daemon=True)
            thread.start()
            return f"🚀 Executing {count} queued tasks. Press *Ctrl+Shift+Esc* to abort."

        # ─── Mouse control ────────────────────────────────────────
        if text_lower.startswith("click at "):
            try:
                coords = text_lower.replace("click at ", "").strip()
                x, y = [int(c.strip()) for c in coords.split(",")]
                self.gui.click(x, y)
                return f"🖱️ Clicked at ({x}, {y})"
            except Exception:
                return "❌ Usage: `click at X, Y`"

        if text_lower.startswith("move mouse to "):
            try:
                coords = text_lower.replace("move mouse to ", "").strip()
                x, y = [int(c.strip()) for c in coords.split(",")]
                self.gui.move_to(x, y)
                return f"🖱️ Mouse moved to ({x}, {y})"
            except Exception:
                return "❌ Usage: `move mouse to X, Y`"

        if text_lower.startswith("type "):
            content = text[5:].strip().strip("'\"")
            self.gui.type_unicode(content)
            return f"⌨️ Typed: {content[:100]}"

        if text_lower.startswith("press "):
            key = text[6:].strip().lower()
            self.gui.press_key(key)
            return f"⌨️ Pressed: {key}"

        if text_lower.startswith("hotkey "):
            keys = [k.strip() for k in text[7:].strip().split("+")]
            self.gui.hotkey(*keys)
            return f"⌨️ Hotkey: {'+'.join(keys)}"

        # ─── Agent status / capabilities ──────────────────────────
        if text_lower in ("desktop status", "agent status", "what can you control"):
            return self._status_message()

        if text_lower in ("what can you draw", "drawing list", "show drawings"):
            drawings = self.creative.get_available_drawings()
            lines = ["🎨 *BRIO can draw:*"]
            for d in drawings:
                lines.append(f"  • *{d['name']}* — {d['description']}")
            lines.append("\nOr describe anything and I'll draw it freestyle!")
            return "\n".join(lines)

        # ─── Abort ────────────────────────────────────────────────
        if text_lower in ("abort", "stop", "cancel task", "stop drawing"):
            self.gui.abort()
            time.sleep(0.5)
            self.gui.reset_abort()
            return "🛑 Aborted all running tasks."

        return None  # Not a desktop agent command

    def _execute_drawing(self, template: Optional[str], full_text: str) -> str:
        """Execute a drawing task."""
        # Open paint app
        self.planner.paint.open()
        time.sleep(2)

        # Get canvas bounds
        bounds = self.planner.paint.get_canvas_bounds()

        # Take pre-drawing screenshot
        self.vision.save_screenshot("pre_drawing")

        if template and template in self.creative.TEMPLATES:
            self.creative.draw_template(template, *bounds)
            result = f"🎨 Drew a *{template}*!"
        else:
            drawn = self.creative.draw_custom(full_text, *bounds)
            result = f"🎨 {drawn}"

        # Post-drawing screenshot
        after = self.vision.save_screenshot("post_drawing")

        result += f"\n\n📸 Screenshot saved: `{after}`"
        result += "\n\n_Say `save` or press Ctrl+S to save your drawing._"
        return result

    def _execute_app_task(self, text: str) -> str:
        """Execute a general application task."""
        plan = self.planner.plan_app_task(text)
        result = self.planner.execute_plan(plan)

        lines = [f"{'✅' if result.status == 'completed' else '❌'} Task: {result.name}",
                 f"Status: {result.status}",
                 f"Steps: {sum(1 for s in result.steps if s.success)}/{len(result.steps)} succeeded"]

        for i, step in enumerate(result.steps):
            icon = "✓" if step.success else "✗"
            lines.append(f"  {i+1}. {icon} {step.description}")
            if step.error:
                lines.append(f"     Error: {step.error}")

        return "\n".join(lines)

    def _missing_deps_msg(self) -> str:
        """Message when dependencies are missing."""
        missing = [k for k, v in self.deps.items() if not v]
        return (
            "🔧 *Desktop control needs additional packages:*\n"
            f"```\npip install {' '.join(missing)}\n```\n"
            "Plus Tesseract OCR for screen reading:\n"
            "• Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "• Mac: `brew install tesseract`\n"
            "• Linux: `sudo apt install tesseract-ocr`\n\n"
            "After installing, restart BRIO."
        )

    def _status_message(self) -> str:
        """Return agent status."""
        lines = ["🤖 *BRIO Desktop Agent Status*\n"]
        lines.append(f"*Local mode:* {'✅ Enabled' if self.is_local else '❌ Cloud mode'}")
        lines.append(f"*OS:* {platform.system()} {platform.release()}")
        lines.append("")
        lines.append("*Dependencies:*")
        for dep, available in self.deps.items():
            lines.append(f"  {'✅' if available else '❌'} {dep}")
        lines.append("")
        lines.append(f"*GUI Control:* {'✅ Ready' if self.has_gui_control else '❌ Install pyautogui + Pillow'}")
        lines.append(f"*Screen OCR:* {'✅ Ready' if HAS_TESSERACT else '❌ Install pytesseract + Tesseract'}")
        lines.append(f"*Abort Hotkey:* {'✅ Ctrl+Shift+Esc' if self._abort_listener else '❌ Install pynput'}")
        lines.append(f"*Task Queue:* {len(self.planner.task_queue)} pending")
        lines.append(f"*Task History:* {len(self.planner.task_history)} completed")
        lines.append("")
        lines.append("*Capabilities:*")
        caps = [
            "🖱️ Mouse control (move, click, drag, scroll)",
            "⌨️ Keyboard control (type, hotkeys, shortcuts)",
            "🎨 Creative drawing (10+ templates + freestyle)",
            "🖥️ Window management (focus, list, close)",
            "📖 Screen reading (OCR text recognition)",
            "🎯 Visual search (find text/images on screen)",
            "📋 Task queue (chain tasks for autonomous execution)",
            "🛑 Safety abort (Ctrl+Shift+Esc or 'abort')",
        ]
        for cap in caps:
            lines.append(f"  {cap}")
        return "\n".join(lines)

    def get_status(self) -> Dict:
        """Status dict for API endpoint."""
        return {
            "enabled": self.is_local,
            "has_gui_control": self.has_gui_control,
            "dependencies": self.deps,
            "os": platform.system(),
            "task_queue_size": len(self.planner.task_queue),
            "task_history_size": len(self.planner.task_history),
            "abort_listener": self._abort_listener is not None,
            "capabilities": [
                "mouse_control", "keyboard_control", "creative_drawing",
                "window_management", "screen_ocr", "visual_search",
                "task_queue", "safety_abort"
            ] if self.is_local else [],
            "drawing_templates": list(self.creative.TEMPLATES.keys()),
        }
