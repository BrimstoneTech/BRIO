"""
BRIO Mascot (brio_sprite.py)
========================================
A desktop pet inspired by 'Neko' (early 2000s).
This app creates a transparent, always-on-top sprite that follows the cursor
and reacts to BRIO's internal state.

Requirements:
    pip install PyQt5 pyautogui

Usage:
    python brio_sprite.py
"""

import sys
import os
import time
import random
import math
import requests
import pyautogui
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QSize
from PyQt5.QtGui import QPixmap, QMovie, QCursor, QRegion

# --- Configuration ---
SPRITE_FILE = "brio_neko_sprites.png" # The generated image
FRAME_SIZE = 64 # Size of each sprite frame (square)
SCALE = 1.5      # Scale up the pixel art
SPEED = 5        # Pixels per frame move

class BrioMascot(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. Window Setup
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool # Hide from taskbar
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(int(FRAME_SIZE * SCALE), int(FRAME_SIZE * SCALE))

        # 2. Sprite Setup
        self.label = QLabel(self)
        self.label.setFixedSize(self.size())
        self.label.setScaledContents(True)
        
        # In a real app, we would crop the sheet. For now, we'll use 
        # a placeholder logic or show the first frame.
        self.full_sheet = QPixmap(SPRITE_FILE)
        if self.full_sheet.isNull():
             # Fallback if image not found
             self.label.setStyleSheet("background: cyan; border-radius: 32px;")
        else:
             # Crop the first frame (sitting)
             self.update_sprite(0, 0)

        # 3. State
        self.pos_x, self.pos_y = 500, 500
        self.target_x, self.target_y = 500, 500
        self.move(self.pos_x, self.pos_y)
        self.state = "idle" # idle, walking, chasing, sleeping, thinking
        self.frame = 0
        self.direction = "right"

        # 4. Timers
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_behavior)
        self.timer.start(100) # 10 FPS animation/logic

        # 5. Context Polling (v5.0)
        self.context_timer = QTimer(self)
        self.context_timer.timeout.connect(self.poll_brio_context)
        self.context_timer.start(5000) # Every 5 seconds

        self.show()

    def poll_brio_context(self):
        """Check the Brio API for context updates."""
        try:
            r = requests.get("http://localhost:5000/api/state", timeout=1)
            if r.status_code == 200:
                data = r.json()
                app = data.get("active_app", "Desktop")
                context = data.get("active_context", "General")
                
                # If we're in Blender or Coding, change state
                if context in ("3D Modeling", "Programming"):
                    self.state = "thinking"
                elif self.state == "thinking":
                    self.state = "idle" # Switch back if focus lost
        except:
            pass

    def update_sprite(self, col, row):
        """Crop a frame from the sprite sheet."""
        if self.full_sheet.isNull(): return
        rect = QRect(col * FRAME_SIZE, row * FRAME_SIZE, FRAME_SIZE, FRAME_SIZE)
        frame = self.full_sheet.copy(rect)
        self.label.setPixmap(frame)

    def update_behavior(self):
        # 1. Get cursor position
        mx, my = pyautogui.position()
        self.target_x = mx - (self.width() // 2)
        self.target_y = my - (self.height() // 2)

        # 2. Distance to cursor
        dx = self.target_x - self.pos_x
        dy = self.target_y - self.pos_y
        dist = math.sqrt(dx**2 + dy**2)

        # 3. Decision Logic (The Neko Brain)
        if dist > 300:
            self.state = "chasing"
        elif dist > 50:
            self.state = "walking"
        elif random.random() < 0.01:
            self.state = "sleeping"
        elif random.random() < 0.05:
            self.state = "idle"

        # 4. Movement
        if self.state in ("chasing", "walking"):
            move_speed = SPEED if self.state == "walking" else SPEED * 2
            
            # Move toward target
            angle = math.atan2(dy, dx)
            self.pos_x += math.cos(angle) * move_speed
            self.pos_y += math.sin(angle) * move_speed
            
            # Direction flip
            self.direction = "right" if dx > 0 else "left"
            
            # Animate (cycling walking frames)
            self.frame = (self.frame + 1) % 2
            row = 1 if self.direction == "right" else 2
            self.update_sprite(self.frame, row)
        
        elif self.state == "idle":
            self.update_sprite(0, 0) # Sitting frame
        
        elif self.state == "sleeping":
            self.update_sprite(0, 3) # Sleeping frame
            
        elif self.state == "thinking":
            self.update_sprite(2, 0) # Thinking/Lightbulb frame

        # Apply position
        self.move(int(self.pos_x), int(self.pos_y))

    def mousePressEvent(self, event):
        """Allow dragging the cat manually."""
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            self.pos_x, self.pos_y = self.x(), self.y()
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Check for image or use dummy
    if not os.path.exists(SPRITE_FILE):
        print(f"⚠️ {SPRITE_FILE} not found. Using placeholder.")
        
    mascot = BrioMascot()
    sys.exit(app.exec_())
