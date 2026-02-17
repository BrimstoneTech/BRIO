
import sys
import unittest
from PyQt5.QtWidgets import QApplication
from brio_dashboard import BrioDashboard

# Mock system class
class MockSystem:
    def __init__(self):
        self.config = {"temperature": 0.5, "max_tokens": 100, "tone_ratio": 0.5}
        self.last_tick_data = {"cpu": 10.5}
        self.storage = None

class TestDashboardIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication(sys.argv)

    def test_dashboard_creation(self):
        mock_sys = MockSystem()
        dashboard = BrioDashboard(system_reference=mock_sys)
        
        # Check title
        self.assertEqual(dashboard.windowTitle(), "Brio Central Command - Brio")
        
        # Check tabs
        self.assertEqual(dashboard.tabs.count(), 5)
        
        # Check Overview components
        self.assertEqual(dashboard.overview.status_label.text(), "ACTIVE")
        
        # Check sliders
        self.assertEqual(dashboard.cognition.temp_slider.value(), 70)
        
    def test_slider_connectivity(self):
        mock_sys = MockSystem()
        dashboard = BrioDashboard(system_reference=mock_sys)
        
        # Change temperature slider
        dashboard.cognition.temp_slider.setValue(80)
        
        # Verify it pushed to mock_sys config
        # Slider is scaled by 0.01
        self.assertAlmostEqual(mock_sys.config["temperature"], 0.8)

if __name__ == "__main__":
    unittest.main()


