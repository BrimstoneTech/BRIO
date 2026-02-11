import sys
import numpy as np
import math
import time
import threading
import pystray
from pystray import MenuItem as item
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLineEdit, 
                             QSizeGrip, QMenu, QAction)
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
    hide_signal = pyqtSignal()
    show_signal = pyqtSignal()

class DesktopBrio(QWidget):
    """
    Brio v3.1 (PyQt5)
    Minimalist 20x20px pulse UI that expands into a Sticky Note Visualizer.
    """
    def __init__(self, command_callback=None):
        super().__init__()
        self.command_callback = command_callback
        self.bridge = UIBridge()
        
        # 1. State & Constants
        self.is_expanded = False
        self.orb_size = 20
        self.expanded_size = 200
        self.current_rgb = (112, 214, 255) # Light Blue
        self.intensity = 0.5
        self.pulse_phase = 0.0
        
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
        from PyQt5.QtWidgets import QTextEdit
        self.output_area = QTextEdit(self)
        self.output_area.setReadOnly(True)
        self.output_area.setFont(QFont("Segoe UI Variable Text", 10))
        self.output_area.setStyleSheet("""
            QTextEdit {
                border: none;
                background: transparent;
                color: #222; /* High contrast dark text on yellow note */
            }
        """)
        self.output_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.output_area.hide()
        self.layout.addWidget(self.output_area)
        
        # Input Field (Hidden initially)
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Type to interrupt...")
        self.input_field.setFont(QFont("Segoe UI Variable Text", 9))
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: none;
                border-top: 1px dashed #666;
                background: transparent;
                padding: 4px;
                color: #222;
            }
        """)
        self.input_field.returnPressed.connect(self._on_submit)
        self.input_field.textChanged.connect(self._on_user_typing)
        self.input_field.hide()
        
        self.layout.addWidget(self.input_field)

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
        self.x = screen.width() - 60
        self.y = 60
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

    def _trigger_cmd(self, cmd):
        if self.command_callback: self.command_callback(cmd)
    
    def minimize_to_tray(self):
        self.hide()
        
    def set_target(self, x, y):
        self.target_x = x
        self.target_y = y

    def _on_submit(self):
        text = self.input_field.text().strip()
        if text: self._trigger_cmd(text)
        self.input_field.clear()
        self._toggle_expanded(False)

    def _toggle_expanded(self, expanded: bool):
        if self.is_expanded == expanded: return
        self.is_expanded = expanded
        if expanded:
            self.resize(self.expanded_size, self.expanded_size)
            self.output_area.show()
            self.input_field.show()
            self.input_field.setFocus() # Focus here so they can type to interrupt
            self._start_audio()
        else:
            self.scroll_timer.stop()
            self.resize(self.orb_size, self.orb_size)
            self.output_area.hide()
            self.input_field.hide()
            self._stop_audio()
        self.update()

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
        if not self.input_field.text():
            self._toggle_expanded(False)

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
            # Draw Sticky Note with Gradient
            grad = QLinearGradient(0, 0, 0, self.height())
            grad.setColorAt(0, QColor("#FFFFA5")) # Classic Sticky Yellow
            grad.setColorAt(1, QColor("#FEF08A")) # Slightly darker yellow
            
            painter.setBrush(grad)
            painter.setPen(QPen(QColor(0, 0, 0, 40), 1)) # Light border
            painter.drawRoundedRect(5, 5, self.width()-10, self.height()-10, 10, 10)
            
            # Draw Visualizer
            if self.audio_data is not None:
                painter.setPen(QPen(QColor(112, 214, 255), 2))
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
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)

    def enterEvent(self, event):
        self._toggle_expanded(True)

    def leaveEvent(self, event):
        if not self.input_field.hasFocus():
            self._toggle_expanded(False)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #121212; color: #70D6FF; border: 1px solid #2a2a2a; }")
        act_hide = menu.addAction("Hide to Tray")
        act_shutdown = menu.addAction("Shutdown")
        
        action = menu.exec_(pos)
        if action == act_hide: self.hide()
        elif action == act_shutdown: self._trigger_cmd("shutdown")

    def _on_tick(self):
        # Movement Interpolation (Smooth Follow)
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        if abs(dx) > 1 or abs(dy) > 1:
            self.x += dx * 0.1
            self.y += dy * 0.1
            self.move(int(self.x), int(self.y))
            
        self.update()

    # Public API for Brain
    def show_thought(self, text: str, duration_sec: int = 5):
        self.bridge.thought_signal.emit(text, duration_sec)

    def update_visuals(self, color: str, intensity: float):
        self.bridge.visual_signal.emit(color, intensity)

    def _on_thought_signal(self, text, duration):
        self._toggle_expanded(True)
        self.input_field.setText(text)
        QTimer.singleShot(duration * 1000, lambda: self._toggle_expanded(False))

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
