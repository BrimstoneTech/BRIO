"""
Brio Dashboard (brio_dashboard.py)

Purpose: Central command hub for Brio (Brio).
         Provides a comprehensive interface for configuration, monitoring, and control.
"""

import sys
import time
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QLabel, QPushButton, QSlider, 
                             QListWidget, QTextEdit, QProgressBar, QGridLayout,
                             QScrollArea, QFrame, QLineEdit, QComboBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor

class DashboardTab(QWidget):
    """Base class for dashboard tabs with standard styling."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

class OverviewTab(DashboardTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Title
        title = QLabel("AI System Overview")
        title.setFont(QFont("Outfit", 18, QFont.Bold))
        self.layout.addWidget(title)
        
        # Grid for metrics
        grid = QGridLayout()
        
        self.status_label = self._create_metric_card(grid, "Status", "ACTIVE", 0, 0, "green")
        self.uptime_label = self._create_metric_card(grid, "Uptime", "00:00:00", 0, 1)
        self.cpu_label = self._create_metric_card(grid, "CPU Usage", "0%", 1, 0)
        self.memory_label = self._create_metric_card(grid, "Memory Usage", "0MB", 1, 1)
        
        self.layout.addLayout(grid)
        
        # Heartbeat Log
        self.layout.addWidget(QLabel("Real-time System Heartbeat"))
        self.heartbeat_log = QListWidget()
        self.heartbeat_log.setStyleSheet("background-color: #1e1e1e; color: #a0a0a0; border: none; font-family: 'Consolas';")
        self.layout.addWidget(self.heartbeat_log)
        
    def _create_metric_card(self, grid, label, value, r, c, color="white"):
        frame = QFrame()
        frame.setStyleSheet("background-color: #2b2b2b; border-radius: 10px; padding: 10px;")
        flay = QVBoxLayout(frame)
        
        l = QLabel(label)
        l.setStyleSheet("color: #888888; font-size: 12px;")
        v = QLabel(value)
        v.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        
        flay.addWidget(l)
        flay.addWidget(v)
        grid.addWidget(frame, r, c)
        return v

class CognitionTab(DashboardTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        title = QLabel("Model Management & Behavior")
        title.setFont(QFont("Outfit", 18, QFont.Bold))
        self.layout.addWidget(title)
        
        # Model Selection
        self.layout.addWidget(QLabel("Primary Intelligence Core"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["Brio Core v3.3 (Local)", "Kimi AI (Cloud Bridge)", "Sunbird (Translation)"])
        self.layout.addWidget(self.model_combo)
        
        # Sliders
        self.temp_slider = self._create_slider_control("Creativity (Temperature)", 0, 100, 70, "temperature", 0.01)
        self.verbosity_slider = self._create_slider_control("Verbosity (Max Tokens)", 50, 2048, 512, "max_tokens", 1)
        self.tone_slider = self._create_slider_control("Tone (Professional <-> Casual)", 0, 100, 50, "tone_ratio", 0.01)

    def _create_slider_control(self, label_text, min_v, max_v, default_v, config_key, scale=1.0):
        layout = QVBoxLayout()
        lbl = QLabel(label_text)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(default_v)
        val_lbl = QLabel(str(default_v * scale if scale != 1.0 else default_v))
        
        def on_change(v):
            real_val = v * scale if scale != 1.0 else v
            val_lbl.setText(f"{real_val:.2f}" if scale != 1.0 else str(real_val))
            # Push to system config if available
            dashboard = self.window()
            if hasattr(dashboard, 'system') and dashboard.system:
                dashboard.system.config[config_key] = real_val

        slider.valueChanged.connect(on_change)
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(slider)
        h_layout.addWidget(val_lbl)
        
        layout.addWidget(lbl)
        layout.addLayout(h_layout)
        self.layout.addWidget(QFrame()) # Spacer
        self.layout.addLayout(layout)
        return slider

class MemoryTab(DashboardTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        title = QLabel("Memory & Interaction History")
        title.setFont(QFont("Outfit", 18, QFont.Bold))
        self.layout.addWidget(title)
        
        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search interaction logs...")
        self.search_btn = QPushButton("Refresh Logs")
        self.search_btn.clicked.connect(self.refresh_logs)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        self.layout.addLayout(search_layout)
        
        # Log View
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; font-family: 'Consolas';")
        self.layout.addWidget(self.log_view)

    def refresh_logs(self):
        dashboard = self.window()
        if hasattr(dashboard, 'system') and dashboard.system and hasattr(dashboard.system, 'storage'):
            logs = dashboard.system.storage.get_recent_interactions(limit=50)
            text = ""
            for log in logs:
                text += f"[{log.timestamp.strftime('%Y-%m-%d %H:%M')}] USER: {log.user_input}\n"
                text += f"BRIO: {log.brio_response}\n"
                text += "-"*40 + "\n"
            self.log_view.setPlainText(text)
        else:
            self.log_view.setPlainText("System storage not connected.")

class AnalyticsTab(DashboardTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        title = QLabel("Performance Analytics")
        title.setFont(QFont("Outfit", 18, QFont.Bold))
        self.layout.addWidget(title)
        
        self.stats_label = QLabel("Loading statistics...")
        self.layout.addWidget(self.stats_label)
        
        self.refresh_btn = QPushButton("Refresh Metrics")
        self.refresh_btn.clicked.connect(self.refresh_stats)
        self.layout.addWidget(self.refresh_btn)

    def refresh_stats(self):
        dashboard = self.window()
        if hasattr(dashboard, 'system') and dashboard.system and hasattr(dashboard.system, 'storage'):
            stats = dashboard.system.storage.get_statistics()
            text = f"Total Interactions: {stats.get('total_interactions', 0)}\n"
            text += f"Average Sentiment: {stats.get('avg_sentiment', 'N/A')}\n"
            text += f"Storage Path: {dashboard.system.storage.db_path}\n"
            self.stats_label.setText(text)

class DevToolsTab(DashboardTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        title = QLabel("Developer Console")
        title.setFont(QFont("Outfit", 18, QFont.Bold))
        self.layout.addWidget(title)
        
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("background-color: black; color: #00ff00; font-family: 'Consolas';")
        self.layout.addWidget(self.console_output)
        
        entry_layout = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Enter test command...")
        self.cmd_input.returnPressed.connect(self.run_test_cmd)
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self.run_test_cmd)
        entry_layout.addWidget(self.cmd_input)
        entry_layout.addWidget(run_btn)
        self.layout.addLayout(entry_layout)

    def run_test_cmd(self):
        cmd = self.cmd_input.text()
        if not cmd: return
        self.console_output.append(f"> {cmd}")
        self.cmd_input.clear()
        dashboard = self.window()
        if hasattr(dashboard, 'system') and dashboard.system:
            res = dashboard.system.handle_command(cmd)
            self.console_output.append(f"< {res}")

class BrioDashboard(QMainWindow):
    def __init__(self, system_reference=None):
        super().__init__()
        self.system = system_reference
        self.setWindowTitle("Brio Central Command - Brio")
        self.resize(1000, 700)
        
        # Styling (Dark Theme)
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; color: white; }
            QTabWidget::pane { border: 1px solid #333; top: -1px; background: #1a1a1a; }
            QTabBar::tab { background: #222; color: #888; padding: 12px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #1a1a1a; color: white; border-bottom: 2px solid #70D6FF; }
            QLabel { color: white; }
            QPushButton { background-color: #0078d4; color: white; border-radius: 5px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #0086f0; }
            QLineEdit, QComboBox { background-color: #2b2b2b; color: white; border: 1px solid #444; padding: 5px; border-radius: 3px; }
        """)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Header
        header = QHBoxLayout()
        logo = QLabel("BRIO DASHBOARD")
        logo.setFont(QFont("Outfit", 20, QFont.Bold))
        logo.setStyleSheet("color: #70D6FF;")
        header.addWidget(logo)
        header.addStretch()
        self.main_layout.addLayout(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.overview = OverviewTab()
        self.cognition = CognitionTab()
        self.memory = MemoryTab()
        self.analytics = AnalyticsTab()
        self.devtools = DevToolsTab()
        
        self.tabs.addTab(self.overview, "Overview")
        self.tabs.addTab(self.cognition, "Cognition")
        self.tabs.addTab(self.memory, "Memory")
        self.tabs.addTab(self.analytics, "Analytics")
        self.tabs.addTab(self.devtools, "DevTools")
        
        self.main_layout.addWidget(self.tabs)
        
        # Update Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000) # 1Hz update
        
        self.start_time = time.time()

    def update_stats(self):
        """Update live metrics if system reference is available."""
        uptime_sec = int(time.time() - self.start_time)
        hrs, rem = divmod(uptime_sec, 3600)
        mins, secs = divmod(rem, 60)
        self.overview.uptime_label.setText(f"{hrs:02d}:{mins:02d}:{secs:02d}")
        
        if self.system:
            # 1. Gather actual system stats
            data = getattr(self.system, 'last_tick_data', {})
            cpu = data.get('cpu', 0.0)
            self.overview.cpu_label.setText(f"{cpu:.1f}%")
            
            # Simple Memory usage heuristic (since we don't have psutil everywhere)
            try:
                import os, psutil
                process = psutil.Process(os.getpid())
                mem = process.memory_info().rss / (1024 * 1024)
                self.overview.memory_label.setText(f"{mem:.1f} MB")
            except:
                self.overview.memory_label.setText("N/A")
            
            # 2. Heartbeat Log (Show system tick success)
            if uptime_sec % 5 == 0:
                 self.overview.heartbeat_log.insertItem(0, f"[{time.strftime('%H:%M:%S')}] Core Heartbeat: STABLE")
                 if self.overview.heartbeat_log.count() > 50:
                     self.overview.heartbeat_log.takeItem(50)
        
        # Update Analytics and Memory if tabs are active
        if self.tabs.currentWidget() == self.memory:
            # Maybe auto-refresh memory? (Don't do it too often)
            pass

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = BrioDashboard()
    window.show()
    sys.exit(app.exec_())


