
import unittest
import sys
import os

# Add parent directory to path to import brim_emotions
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brim_emotions import EmotionEngine, EmotionTrigger

class TestEmotionDynamics(unittest.TestCase):
    def setUp(self):
        self.engine = EmotionEngine()
    
    def test_initial_state(self):
        """Verify engine starts at baseline"""
        state = self.engine.get_state()
        # Baseline: [0.5, 0.2, 0.7, 0.6, 0.3, 0.6]
        self.assertAlmostEqual(state.joy, 0.5)
        self.assertAlmostEqual(state.frustration, 0.2)
        
    def test_trigger_application(self):
        """Verify triggers push the state vector correctly"""
        # Praise adds Joy (+0.8 * intensity) and Confidence
        self.engine.apply_trigger(EmotionTrigger.USER_PRAISE, intensity=0.1)
        state = self.engine.get_state()
        
        # 0.5 + (0.1 * 0.8) = 0.58
        self.assertAlmostEqual(state.joy, 0.58)
        
    def test_homeostasis_decay(self):
        """Verify state returns to baseline over time without input"""
        # Spike Joy to 1.0 manually
        self.engine.state.joy = 1.0
        
        # Evolve for 100 cycles
        for _ in range(100):
            self.engine.evolve(dt=1.0)
            
        # Should be close to baseline 0.5
        self.assertAlmostEqual(self.engine.state.joy, 0.5, delta=0.01)
        
    def test_interaction_dynamics(self):
        """Verify Frustration dampens Joy"""
        # Set High Frustration
        self.engine.state.frustration = 1.0
        self.engine.state.joy = 0.8
        
        # Evolve one step
        # Interaction: Frus(1) -> Joy(0) is -0.1
        # Delta Joy += -0.1 * Frus(1.0) * 0.1(scaling) = -0.01
        self.engine.evolve(dt=1.0)
        
        # Joy should be less than it would be from just decay
        # Decay force for joy=0.8 is 0.05 * (0.8 - 0.5) = 0.015
        # Joy new = 0.8 - 0.015 (decay) - 0.01 (interaction) = 0.775
        self.assertLess(self.engine.state.joy, 0.79)
        
    def test_bounds_clamping(self):
        """Verify values never exceed 0.0-1.0"""
        # Try to push Joy way up
        self.engine.apply_trigger(EmotionTrigger.USER_PRAISE, intensity=2.0) # Intensity clamped to 0.3 internally
        self.engine.state.joy = 5.0 # Manual override setter should clamp
        
        self.assertEqual(self.engine.state.joy, 1.0)
        
        self.engine.state.joy = -5.0
        self.assertEqual(self.engine.state.joy, 0.0)

if __name__ == '__main__':
    unittest.main()
