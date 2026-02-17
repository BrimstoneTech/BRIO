
import unittest
import sys
import os

# Add parent directory to path to import brio_ui
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brio_ui import OverlayController, MenuOption
from brio_emotions import EmotionalState, EmotionType

class TestOverlayController(unittest.TestCase):
    def setUp(self):
        self.controller = OverlayController()
        
    def test_visual_mapping(self):
        # Create a mock emotional state
        state = EmotionalState()
        state.joy = 1.0  # Dominant Joy
        state.frustration = 0.0
        state.empathy = 0.0
        state.curiosity = 0.0
        state.concern = 0.0
        state.confidence = 0.0
        state._update_dominant()
        
        # Process Overlay
        overlay = self.controller.process_state(state)
        
        # Verify Joy Color (Gold)
        self.assertEqual(overlay.halo.color_hex, "#FFD700")
        
        # Verify High Intensity Pulse ( > 0.5)
        # Intensity = (1+0+0+0+0+0)/6 = 0.166... * 2.5 + 0.5 approx... wait
        # Formula: 0.5 + (intensity * 2.0)
        # Only joy is 1.0, others default to 0.0 for this test? 
        # EmotionalState default init has values.
        # Let's set specific vector for predictability
        state._vector = [1.0, 0, 0, 0, 0, 0] # Super intense joy, nothing else
        
        overlay = self.controller.process_state(state)
        intensity = 1.0/6.0 # 0.166
        expected_pulse = 0.5 + (0.166 * 2.0) # ~0.833
        
        self.assertAlmostEqual(overlay.halo.pulse_rate, expected_pulse, delta=0.1)

    def test_menu_interaction(self):
        # Initially closed
        self.assertFalse(self.controller.menu_visible)
        
        # Long press opens
        self.controller.handle_input("long_press")
        self.assertTrue(self.controller.menu_visible)
        
        # Generate state, should see options
        state = EmotionalState()
        overlay = self.controller.process_state(state)
        self.assertIn("settings", overlay.menu_options)
        
        # Select Option logic
        cmd = self.controller.select_menu_option("settings")
        self.assertEqual(cmd, "EXECUTE:settings")
        self.assertFalse(self.controller.menu_visible) # Should close after select

if __name__ == '__main__':
    unittest.main()


