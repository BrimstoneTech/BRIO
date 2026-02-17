
import unittest
import sys
import os

# Add parent directory to path to import brio_logic
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brio_logic import SubjectiveOpinion

class TestSubjectiveLogic(unittest.TestCase):
    def test_normalization(self):
        # User provides non-summing values
        # b=1, d=1, u=0 -> Total 2
        # Should normalize to b=0.5, d=0.5, u=0
        op = SubjectiveOpinion(1.0, 1.0, 0.0)
        self.assertAlmostEqual(op.b, 0.5)
        self.assertAlmostEqual(op.d, 0.5)
        
    def test_fusion_consensus(self):
        # Opinion A: Semi-trusting (b=0.8, d=0.1, u=0.1)
        op_a = SubjectiveOpinion(0.8, 0.1, 0.1)
        
        # Opinion B: Also trusting (b=0.7, d=0.1, u=0.2)
        op_b = SubjectiveOpinion(0.7, 0.1, 0.2)
        
        # Fusing two supporting opinions should INCREASE belief and DECREASE uncertainty
        fused = op_a.fuse(op_b)
        
        # Expected Logic:
        # k = 0.1 + 0.2 - 0.02 = 0.28
        # b = (0.8*0.2 + 0.7*0.1) / 0.28 = (0.16 + 0.07) / 0.28 = 0.23 / 0.28 ≈ 0.82
        # u = (0.1*0.2) / 0.28 = 0.02 / 0.28 ≈ 0.07
        
        self.assertGreater(fused.b, 0.8) # Belief increased
        self.assertLess(fused.u, 0.1)    # Uncertainty decreased
        self.assertAlmostEqual(fused.b + fused.d + fused.u, 1.0) # Invariant holds

    def test_fusion_conflict(self):
        # Opinion A: Trust (b=0.9, u=0.1)
        op_a = SubjectiveOpinion(0.9, 0.0, 0.1)
        
        # Opinion B: Distrust (d=0.9, u=0.1)
        op_b = SubjectiveOpinion(0.0, 0.9, 0.1)
        
        fused = op_a.fuse(op_b)
        
        # Conflict should result in high uncertainty or middle probability
        # k = 0.1 + 0.1 - 0.01 = 0.19
        # b = (0.9*0.1 + 0*0.1) / 0.19 = 0.09 / 0.19 ≈ 0.47
        # d = (0*0.1 + 0.9*0.1) / 0.19 = 0.09 / 0.19 ≈ 0.47
        # u = 0.01 / 0.19 ≈ 0.05
        
        self.assertAlmostEqual(fused.b, fused.d, delta=0.01) # Symmetrical conflict
        
    def test_dogmatic_fusion(self):
        # Two absolute opinions shouldn't crash
        op_a = SubjectiveOpinion(1, 0, 0)
        op_b = SubjectiveOpinion(1, 0, 0)
        fused = op_a.fuse(op_b)
        self.assertEqual(fused.b, 1.0)

if __name__ == '__main__':
    unittest.main()


