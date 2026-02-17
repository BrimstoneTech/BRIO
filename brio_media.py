"""
Brio Media Module (brio_media.py)

Purpose: Monitors active window and media context to allow Brio to 
         "watch" and react with the user.
"""

import threading
import time
from enum import Enum
from typing import Optional, Dict

# try imports for Windows window title checking
try:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    HAS_WIN32 = True
except (ImportError, AttributeError):
    HAS_WIN32 = False

class MediaContext(Enum):
    NONE = "none"
    COMEDY = "comedy"
    HORROR = "horror"
    NEWS = "news"
    PRODUCTIVITY = "productivity"
    GAMING = "gaming"

class MediaWatcher:
    """
    Simulates Brio watching content with the user.
    Uses window title heuristics to guess the context.
    """
    
    def __init__(self):
        self.current_title = ""
        self.current_context = MediaContext.NONE
        self.is_running = False
        self.last_reaction_time = time.time()
        
        # Simple heuristic mapping (Keyword -> Context)
        self.heuristics = {
            "funny": MediaContext.COMEDY,
            "comedy": MediaContext.COMEDY,
            "cat": MediaContext.COMEDY,
            "meme": MediaContext.COMEDY,
            "horror": MediaContext.HORROR,
            "scary": MediaContext.HORROR,
            "dead": MediaContext.HORROR,
            "fear": MediaContext.HORROR,
            "news": MediaContext.NEWS,
            "politics": MediaContext.NEWS,
            "world": MediaContext.NEWS,
            "code": MediaContext.PRODUCTIVITY,
            "visual studio": MediaContext.PRODUCTIVITY,
            "python": MediaContext.PRODUCTIVITY,
            "game": MediaContext.GAMING,
            "steam": MediaContext.GAMING,
            "minecraft": MediaContext.GAMING
        }

    def start(self):
        """Starts the background polling loop"""
        if not HAS_WIN32:
            print("[MediaWatcher] Win32 API not available. Media reaction disabled.")
            return

        self.is_running = True
        t = threading.Thread(target=self._poll_loop, daemon=True)
        t.start()
        print("[MediaWatcher] Loop started.")

    def stop(self):
        self.is_running = False

    def _poll_loop(self):
        while self.is_running:
            self._update_window_info()
            time.sleep(2.0) # Poll every 2 seconds

    def _update_window_info(self):
        """Fetches the title of the current foreground window"""
        if not HAS_WIN32: return

        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        
        new_title = buff.value
        if new_title != self.current_title:
            self.current_title = new_title
            self._analyze_context(new_title)

    def _analyze_context(self, title: str):
        """Maps title keywords to context"""
        title_lower = title.lower()
        found_context = MediaContext.NONE
        
        for keyword, context in self.heuristics.items():
            if keyword in title_lower:
                found_context = context
                break
        
        if found_context != self.current_context:
            self.current_context = found_context
            # Potential for immediate reaction trigger here
            # But we leave mapping to Emotions Engine in brio_main.py

    def get_context(self) -> MediaContext:
        return self.current_context

    def get_title(self) -> str:
        return self.current_title


