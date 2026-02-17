
import unittest
import sys
import os

# Add parent directory to path to import brio_emotions
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brio_emotions import FuzzyLogic, get_emotion_description, EmotionType

class TestFuzzyLogic(unittest.TestCase):
    def test_triangular_membership(self):
        # Peak check
        # Triangle: a=0, b=0.5, c=1.0
        # Peak at 0.5 should be 1.0
        val = FuzzyLogic.triangular_membership(0.5, 0.0, 0.5, 1.0)
        self.assertAlmostEqual(val, 1.0)
        
        # Zero check (outside range)
        val = FuzzyLogic.triangular_membership(1.1, 0.0, 0.5, 1.0)
        self.assertEqual(val, 0.0)
        
        # Halfway check
        # x=0.25 (midpoint between 0 and 0.5) should be 0.5 membership
        val = FuzzyLogic.triangular_membership(0.25, 0.0, 0.5, 1.0)
        self.assertAlmostEqual(val, 0.5)

    def test_fuzzy_description_selection(self):
        # Sets: Low(-0.1, 0, 0.4), Med(0.3, 0.5, 0.7), High(0.6, 1.0, 1.1)
        
        # Test Case 1: Clear Low (0.1)
        # Low membership(0.1) formula: (0.4-0.1)/(0.4-0) = 0.75
        # Med membership(0.1) = 0
        desc = get_emotion_description(EmotionType.JOY, 0.1)
        self.assertEqual(desc, "Content")
        
        # Test Case 2: Clear Medium (0.5)
        desc = get_emotion_description(EmotionType.JOY, 0.5)
        self.assertEqual(desc, "Happy")
        
        # Test Case 3: Clear High (0.9)
        desc = get_emotion_description(EmotionType.JOY, 0.9)
        self.assertEqual(desc, "Ecstatic")

    def test_vocab_mapping(self):
        # Verify different emotions have different words
        joy_high = get_emotion_description(EmotionType.JOY, 0.9)
        frus_high = get_emotion_description(EmotionType.FRUSTRATION, 0.9)
        
        self.assertEqual(joy_high, "Ecstatic")
        self.assertEqual(frus_high, "Angry") # High Frustration = Angry
        
        conf_low = get_emotion_description(EmotionType.CONFIDENCE, 0.1)
        self.assertEqual(conf_low, "Uncertain")

if __name__ == '__main__':
    unittest.main()


