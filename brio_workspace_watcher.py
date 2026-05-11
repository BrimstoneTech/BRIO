"""
BRIO Workspace Watcher (brio_workspace_watcher.py)
==================================================
This module monitors the active window on the desktop and 
updates BRIO's context. 

Mappings:
    "Blender" -> 3D Modeling Context
    "Code" / "Visual Studio" -> Programming Context
    "Chrome" / "Edge" -> Research Context
    "Notepad" -> Writing Context
"""

import time
import threading
import logging

# Use pygetwindow if available, otherwise fallback to simple check
try:
    import pygetwindow as gw
    HAS_GW = True
except ImportError:
    HAS_GW = False

log = logging.getLogger("brio.watcher")

class WorkspaceWatcher:
    def __init__(self, system_ref=None, interval=5.0):
        self.system = system_ref
        self.interval = interval
        self.active_app = "Unknown"
        self.active_context = "General"
        self.is_running = False
        self._thread = None
        
        # Define context mappings (Keywords in window title -> Context Name)
        self.mappings = {
            "Blender": "3D Modeling",
            "Visual Studio": "Programming",
            "Code": "Programming",
            "Notepad": "Writing",
            "Word": "Writing",
            "Excel": "Data Analysis",
            "Chrome": "Research",
            "Edge": "Research",
            "Firefox": "Research",
            "Discord": "Communication",
            "Slack": "Communication",
            "Paint": "Graphics Design",
            "Krita": "Graphics Design",
            "GIMP": "Graphics Design",
            "Explorer": "File Management",
        }

    def start(self):
        """Start the background monitoring thread."""
        if self.is_running: return
        self.is_running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        log.info("[Watcher] Workspace monitoring started.")

    def stop(self):
        self.is_running = False

    def _watch_loop(self):
        while self.is_running:
            try:
                new_app, new_context = self._get_active_info()
                
                if new_app != self.active_app:
                    self.active_app = new_app
                    self.active_context = new_context
                    self._on_context_change(new_app, new_context)
                    
            except Exception as e:
                log.debug(f"[Watcher] Loop error: {e}")
            
            time.sleep(self.interval)

    def _get_active_info(self):
        """Detect active window title and map it."""
        title = ""
        if HAS_GW:
            try:
                win = gw.getActiveWindow()
                if win:
                    title = win.title
            except:
                pass
        
        # Simple mapping logic
        detected_app = "Desktop"
        detected_context = "General"
        
        if title:
            detected_app = title
            for key, context in self.mappings.items():
                if key.lower() in title.lower():
                    detected_app = key
                    detected_context = context
                    break
        
        return detected_app, detected_context

    def _on_context_change(self, app, context):
        """Notify the system of a context shift."""
        log.info(f"[Watcher] Context Shift: {app} ({context})")
        
        if self.system:
            # Update system state
            if hasattr(self.system, 'update_context'):
                self.system.update_context(app, context)
            
            # If we have a socket connection (Web Edition), emit the update
            if hasattr(self.system, 'broadcast_context'):
                self.system.broadcast_context(app, context)

    def get_current(self):
        return self.active_app, self.active_context
