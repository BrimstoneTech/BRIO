
import unittest
import sys
import os

# Add parent directory to path to import brim_security
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brim_security import SafetyProbabilityModel, SafetyInputs, SafetyModelConfig

class TestSafetyModel(unittest.TestCase):
    def setUp(self):
        self.model = SafetyProbabilityModel()
        
    def test_ideal_conditions(self):
        """Verify perfect conditions yield high safety probability"""
        inputs = SafetyInputs(
            location_familiarity=1.0,
            time_routine_match=1.0,
            device_integrity=1.0,
            network_security=1.0
        )
        
        # z = -4 + 2 + 1 + 3 + 2 = 4.0
        # p = 1 / (1 + e^-4) ≈ 0.982
        prob = self.model.calculate_probability(inputs)
        self.assertGreater(prob, 0.95)
        self.assertTrue(self.model.is_safe(inputs))

    def test_worst_conditions(self):
        """Verify worst conditions yield low safety probability"""
        inputs = SafetyInputs(
            location_familiarity=0.0,
            time_routine_match=0.0,
            device_integrity=0.0, 
            network_security=0.0
        )
        
        # z = -4.0
        # p = 1 / (1 + e^4) ≈ 0.018
        prob = self.model.calculate_probability(inputs)
        self.assertLess(prob, 0.05)
        self.assertFalse(self.model.is_safe(inputs))

    def test_compromised_device(self):
        """Verify device compromise heavily impacts safety due to high weight"""
        inputs = SafetyInputs(
            location_familiarity=1.0, # Safe loc
            time_routine_match=1.0,   # Safe time
            device_integrity=0.0,     # ROOTED/MALWARE
            network_security=1.0      # Safe net
        )
        
        # Config: beta_0=-4, loc=2, time=1, dev=3, net=2
        # z = -4 + 2 + 1 + 0 + 2 = 1.0
        # p = 1 / (1 + e^-1) ≈ 0.73
        
        # Should be statistically "safer" than total 0, but might fall below strict thresholds (e.g. 0.8)
        prob = self.model.calculate_probability(inputs)
        
        # With default threshold 0.8, this should be UNSAFE
        self.assertFalse(self.model.is_safe(inputs, threshold=0.8))
        self.assertAlmostEqual(prob, 0.731, delta=0.01)

if __name__ == '__main__':
    unittest.main()
