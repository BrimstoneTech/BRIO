import sys
import numpy as np
import math
import time
import threading
import pystray
from pystray import MenuItem as item
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLineEdit, 
                             QSizeGrip, QMenu, QAction, QPushButton, QHBoxLayout, QLabel, QTextEdit)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPoint, pyqtSignal, QObject
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QIcon, QFont, QLinearGradient, QRadialGradient
try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    
from PIL import Image, ImageDraw

class UIBridge(QObject):
    """Thread-safe bridge for signals from the Brain to the UI."""
    thought_signal = pyqtSignal(str, int)
    visual_signal = pyqtSignal(str, float)
    status_signal = pyqtSignal(str) # For "Neural Pathways" status
    hide_signal = pyqtSignal()
    show_signal = pyqtSignal()

class DesktopBrio(QWidget):
    """
    Brio v4.5 (PyQt5)
    Minimalist 20x20px pulse UI that expands into a Sticky Note Visualizer.
    """
    def __init__(self, command_callback=None):
        super().__init__()
        self.command_callback = command_callback
        self.bridge = UIBridge()
        
        # 1. State & Constants
        self.is_expanded = True # Start expanded (Text Form)
        self.is_hovered = False
        self.option_mode = False 
        self.move_freely = False # Fixed until command
        self.orb_size = 20
        self.expanded_size = 280 
        self.current_rgb = (112, 214, 255) 
        self.intensity = 0.5
        self.pulse_phase = 0.0
        self.is_pinned = True 
        
        # Audio Visualizer State
        self.CHUNK = 1024
        self.FORMAT = 8 # pyaudio.paInt16 fallback
        self.CHANNELS = 1
        self.RATE = 44100
        self.p = None
        self.stream = None
        self.audio_data = None
        
        if HAS_PYAUDIO and HAS_NUMPY:
            try:
                self.p = pyaudio.PyAudio()
                self.FORMAT = pyaudio.paInt16
                self.audio_data = np.zeros(self.CHUNK)
            except:
                pass
        
        # 2. Window Setup
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.init_ui()
        
        # 3. Signals
        self.bridge.thought_signal.connect(self._on_thought_signal)
        self.bridge.visual_signal.connect(self._on_visual_signal)
        self.bridge.status_signal.connect(self._on_status_signal)
        self.bridge.hide_signal.connect(self.hide)
        self.bridge.show_signal.connect(self.show)
        
        # 4. Timers
        self.timer = QTimer()
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(50) # 20Hz logic
        
        # 5. Position
        self._pos_init()
        
        # 6. System Tray
        self._setup_tray()
        
    user_typing_signal = pyqtSignal()

    def init_ui(self):
        self.resize(self.orb_size, self.orb_size)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        
        # Output Area (Scrolling "End Credits" Style)
        # We use a read-only TextEdit for rich text and scrolling
        self.output_area = QTextEdit(self)
        self.output_area.setReadOnly(True)
        self.output_area.setFont(QFont("Segoe UI Variable Text", 11, QFont.Bold))
        self.output_area.setStyleSheet("""
            QTextEdit {
                border: none;
                background: transparent;
                color: #1a1a1a; 
                selection-background-color: rgba(112, 214, 255, 100);
                padding: 10px;
            }
        """)
        self.output_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.output_area.show() # Show by default
        self.layout.addWidget(self.output_area)
        
        # Input Field & Status Label
        self.input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Type to interrupt...")
        self.input_field.setFont(QFont("Segoe UI Variable Text", 9))
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: none;
                border-top: 1px solid rgba(0, 0, 0, 0.1);
                background: rgba(255, 255, 255, 0.3);
                padding: 6px;
                color: #333;
                border-radius: 4px;
            }
            QLineEdit:focus {
                background: rgba(255, 255, 255, 0.5);
                border-top: 1px solid #70D6FF;
            }
        """)
        self.input_field.returnPressed.connect(self._on_submit)
        self.input_field.textChanged.connect(self._on_user_typing)
        
        self.status_label = QLabel("Neural Pathways: Initializing...", self)
        self.status_label.setFont(QFont("Segoe UI Variable Text", 8, QFont.Medium))
        self.status_label.setStyleSheet("color: #70D6FF; margin-left: 5px;")
        
        self.input_layout.addWidget(self.input_field, 4)
        self.input_layout.addWidget(self.status_label, 1)
        self.layout.addLayout(self.input_layout)

        # 4. Selection HUD (Notepad/Voice)
        self.option_layout = QHBoxLayout()
        self.btn_notepad = QPushButton("Notepad", self)
        self.btn_voice = QPushButton("Voice", self)
        
        for btn in [self.btn_notepad, self.btn_voice]:
            btn.setFont(QFont("Segoe UI Variable Text", 9, QFont.Bold))
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(112, 214, 255, 40);
                    border: 1px solid #70D6FF;
                    color: #1a1a1a;
                    padding: 8px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background: #70D6FF;
                    color: white;
                }
            """)
        
        self.btn_notepad.clicked.connect(self._select_notepad)
        self.btn_voice.clicked.connect(self._select_voice)
        
        self.option_layout.addWidget(self.btn_notepad)
        self.option_layout.addWidget(self.btn_voice)
        
        self.option_widget = QWidget()
        self.option_widget.setLayout(self.option_layout)
        self.option_widget.hide()
        self.layout.addWidget(self.option_widget)

        # Scroll Timer
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self._scroll_text)
        
    def _on_user_typing(self):
        if self.input_field.text():
            self.user_typing_signal.emit()
            self.scroll_timer.stop() # Stop scrolling if user types
            
    def _scroll_text(self):
        # Auto-scroll down
        vsb = self.output_area.verticalScrollBar()
        if vsb.value() < vsb.maximum():
            vsb.setValue(vsb.value() + 1)
        else:
            self.scroll_timer.stop()
        
    def _pos_init(self):
        screen = QApplication.primaryScreen().size()
        # Center horizontally at the top
        self.x = (screen.width() - self.expanded_size) / 2
        self.y = 20 
        self.target_x = self.x
        self.target_y = self.y
        self.move(int(self.x), int(self.y))

    def _setup_tray(self):
        img = Image.new('RGB', (64, 64), (18, 18, 18))
        draw = ImageDraw.Draw(img)
        draw.ellipse((10, 10, 54, 54), fill=(112, 214, 255))
        
        menu = (
            item('Restore Brio', lambda: self.bridge.show_signal.emit(), default=True),
            item('Settings', lambda: self._trigger_cmd("settings")),
            item('Exit', self._on_exit_entirely)
        )
        self.tray_icon = pystray.Icon("Brio", img, "Brio", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _on_exit_entirely(self, icon=None, item=None):
        if self.tray_icon: self.tray_icon.stop()
        self._trigger_cmd("shutdown_force")

    def _trigger_cmd(self, cmd, trusted=False):
        if self.command_callback:
            self.command_callback(cmd, trusted=trusted)
    
    def minimize_to_tray(self):
        self.hide()
        
    def set_target(self, x, y):
        self.target_x = x
        self.target_y = y

    def _on_submit(self):
        try:
            text = self.input_field.text().strip()
            if text:
                # Set feedback status immediately
                if hasattr(self, 'status_label'):
                    self.status_label.setText("Pathways: Processing...")
                self._trigger_cmd(text)
            self.input_field.clear()
        except Exception as e:
            print(f"[UI Error] Submission failed: {e}")
            if hasattr(self, 'status_label'):
                self.status_label.setText("Pathways: Error.")
            self.show_thought(f"I encountered a neural hiccup processing that: {str(e)[:50]}...")

    def _toggle_expanded(self, expanded: bool):
        if self.is_expanded == expanded: return
        self.is_expanded = expanded
        
        if expanded:
            self.option_widget.hide() # Hide options when fully expanded
            self.resize(self.expanded_size, self.expanded_size)
            self.output_area.show()
            self.input_field.show()
            self.input_field.setFocus()
            self._start_audio()
        else:
            self.scroll_timer.stop()
            self.resize(self.orb_size, self.orb_size)
            self.output_area.hide()
            self.input_field.hide()
            self.option_widget.hide()
            self._stop_audio()
        self.update()

    def _show_options(self):
        """Shows the selection overlay"""
        self.option_mode = True
        self.resize(self.expanded_size, 80) # Narrow but wide for buttons
        self.option_widget.show()
        self.output_area.hide()
        self.input_field.hide()
        self.update()

    def _select_notepad(self):
        self.option_mode = False
        self.is_pinned = False # Once they interact, allow movement? 
        # Or maybe keep it pinned until they explicitly move it.
        self._toggle_expanded(True)

    def _select_voice(self):
        # Simplification: Voice opens the visualizer area
        self.option_mode = False
        self._toggle_expanded(True)
        self.input_field.setPlaceholderText("Listening to your voice...")
        self._trigger_cmd("say I'm listening. Speak now.")

    def show_thought(self, text: str, duration_sec: int = 5):
        """Thread-safe way for Brain to trigger a thought buble."""
        self.bridge.thought_signal.emit(text, duration_sec)

    def _on_thought_signal(self, text, duration):
        self._toggle_expanded(True)
        # Set text to the scrolling area
        self.output_area.setText(text)
        self.output_area.verticalScrollBar().setValue(0)
        
        # Start scrolling if text is long enough, otherwise just show it
        # Speed: 50ms per pixel scroll
        self.scroll_timer.start(50) 
        
        # Auto-hide after duration (unless user is typing)
        QTimer.singleShot(duration * 1000, lambda: self._check_autohide())

    def _check_autohide(self):
        # Disabled: Persist in text form as requested
        pass

    def _on_status_signal(self, status: str):
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"Pathways: {status}")

    def _start_audio(self):
        if not self.stream:
            try:
                self.stream = self.p.open(
                    format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE,
                    input=True, frames_per_buffer=self.CHUNK,
                    stream_callback=self._audio_callback
                )
            except: pass

    def _stop_audio(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def _audio_callback(self, in_data, frame_count, time_info, status):
        self.audio_data = np.frombuffer(in_data, dtype=np.int16)
        return (None, pyaudio.paContinue)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.is_expanded:
            # Draw Premium Sticky Note with Glassmorphism
            # 1. Shadow/Outer Glow
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 30))
            painter.drawRoundedRect(7, 7, self.width()-10, self.height()-10, 12, 12)

            # 2. Main Body (Translucent Yellow Gradient)
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0, QColor(255, 255, 165, 230)) # Frosted Yellow
            grad.setColorAt(1, QColor(254, 240, 138, 200)) # Warmer translucency
            
            painter.setBrush(grad)
            painter.setPen(QPen(QColor(255, 255, 255, 100), 2)) # White "glass" border
            painter.drawRoundedRect(5, 5, self.width()-10, self.height()-10, 12, 12)
            
            # 3. Inner Shine (Top lighting)
            shine = QLinearGradient(0, 0, 0, 20)
            shine.setColorAt(0, QColor(255, 255, 255, 80))
            shine.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(shine)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(5, 5, self.width()-10, 20, 12, 12)

            # Draw Visualizer area
            if self.audio_data is not None:
                painter.setPen(QPen(QColor(112, 214, 255, 180), 2))
                norm_data = self.audio_data / 32768.0
                step = self.width() / len(norm_data)
                path = QPainterPath()
                path.moveTo(0, self.height() * 0.8)
                for i, val in enumerate(norm_data[::4]): # Sampled for performance
                    x = i * step * 4
                    y = self.height() * 0.8 - val * 30
                    path.lineTo(x, y)
                painter.drawPath(path)
        else:
            # Draw Brio Orb with Glow
            self.pulse_phase += 0.1
            pulse = 0.7 + 0.3 * abs(math.sin(self.pulse_phase))
            
            r = int(self.current_rgb[0] * pulse)
            g = int(self.current_rgb[1] * pulse)
            b = int(self.current_rgb[2] * pulse)
            
            # Glow effect
            glow = QRadialGradient(self.width()/2, self.height()/2, self.orb_size/2)
            glow.setColorAt(0, QColor(r, g, b, 255))
            glow.setColorAt(0.8, QColor(r, g, b, 150))
            glow.setColorAt(1, QColor(r, g, b, 0))
            
            painter.setBrush(glow)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, self.width(), self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.move_freely:
                self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.move_freely:
            self.move(event.globalPos() - self.drag_pos)

    def enterEvent(self, event):
        self.is_hovered = True

    def leaveEvent(self, event):
        self.is_hovered = False

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #121212; color: #70D6FF; border: 1px solid #2a2a2a; }")
        dashboard_action = menu.addAction("Dashboard")
        options_action = menu.addAction("Options Overlay")
        notepad_action = menu.addAction("Notepad Mode")
        voice_action = menu.addAction("Voice Mode")
        menu.addSeparator()
        exit_action = menu.addAction("Exit Brio")

        action = menu.exec_(pos)
        if action == dashboard_action:
            self._trigger_cmd("dashboard", trusted=True)
        elif action == options_action:
            self._show_options()
        elif action == notepad_action:
            self._select_notepad()
        elif action == voice_action:
            self._select_voice()
        elif action == exit_action:
            self._on_exit_entirely()

    def _on_tick(self):
        # 1. Movement Interpolation (Smooth Follow)
        # If hovered, expanded, pinned, or in option mode, PAUSE movement
        if self.is_hovered or self.is_expanded or self.option_mode or self.is_pinned:
            # But if pinned at start, ensure we ARE at the target
            if self.is_pinned and (abs(self.x - self.target_x) > 1 or abs(self.y - self.target_y) > 1):
                pass # Allow it to slide to the corner initially
            else:
                self.update()
                return

        dx = self.target_x - self.x
        dy = self.target_y - self.y
        if abs(dx) > 1 or abs(dy) > 1:
            # Smoother interpolation factor (0.05 instead of 0.1)
            self.x += dx * 0.05
            self.y += dy * 0.05
            self.move(int(self.x), int(self.y))
            
        self.update()

    # Public API for Brain
    def show_thought(self, text: str, duration_sec: int = 5):
        self.bridge.thought_signal.emit(text, duration_sec)

    def update_visuals(self, color: str, intensity: float):
        self.bridge.visual_signal.emit(color, intensity)

    def _on_visual_signal(self, color_hex, intensity):
        try:
            h = color_hex.lstrip('#')
            self.current_rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        except: self.current_rgb = (112, 214, 255)
        self.intensity = intensity

    def run_loop(self):
        # In PyQt, the app handles the loop, but for compatibility:
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    brio = DesktopBrio()
    brio.show()
    sys.exit(app.exec_())


