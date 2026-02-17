
import unittest
import sys
import os
from unittest.mock import MagicMock

# Add current directory to path
sys.path.append(os.getcwd())

# Mock dependencies to avoid import-time crashes
sys.modules['pystray'] = MagicMock()
sys.modules['pyaudio'] = MagicMock()

from brio_main import BrioSystem

# Define a minimal BrioSystem for testing handle_command logic
class MinimalBrioSystem:
    def __init__(self):
        self.is_awake = True
        self.desktop_ui = MagicMock()
        self.comm_cycle = MagicMock()
        self.entropy = MagicMock()
        self.emotions = MagicMock()
        self.knowledge = MagicMock()
        self.dashboard = None
        self.custom_name = "Brio"
        self.emotions.get_dominant_emotion.return_value = "Neutral"
        self.emotions.get_intensity.return_value = 0.5
        
    def _speak_and_think(self, msg, duration=5):
        pass

    # Assign the method manually
    handle_command = BrioSystem.handle_command

class TestDashboardSecurity(unittest.TestCase):
    def setUp(self):
        self.system = MinimalBrioSystem()
        # Mock the cognition flow to execute the internal callback
        self.system.comm_cycle.cognition.side_effect = lambda cb: cb(self.system.comm_cycle.decoded_message)
        
    def test_human_trusted_access(self):
        """Verify that a trusted call (from Human UI) opens the dashboard."""
        self.system.dashboard = MagicMock()
        self.system.comm_cycle.decoded_message = "dashboard"
        
        # Simulate human interaction via UI callback (trusted=True)
        res = self.system.handle_command("dashboard", trusted=True)
        
        self.assertIn("Opening Brio Central Command", res)
        # Ensure show was called on the dashboard
        self.system.dashboard.show.assert_called_once()

    def test_ai_untrusted_access(self):
        """Verify that an untrusted call (like typing 'dashboard') is blocked."""
        self.system.dashboard = MagicMock()
        self.system.comm_cycle.decoded_message = "dashboard"
        
        # Simulate untrusted call (default trusted=False)
        res = self.system.handle_command("dashboard", trusted=False)
        
        self.assertIn("Access Denied", res)
        # Ensure show was NOT called
        self.system.dashboard.show.assert_not_called()

if __name__ == "__main__":
    unittest.main()


