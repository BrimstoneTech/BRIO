
import unittest
import sys
import os
import json
import math

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brio_main import BrioSystem
from brio_emotions import EmotionType

class TestSafeguardProtocol(unittest.TestCase):
    def setUp(self):
        # Ensure clean state for each test
        if os.path.exists("brio_state.json"):
            os.remove("brio_state.json")
        self.system = BrioSystem()

    def test_emotion_self_healing(self):
        # 1. Manually corrupt the vector with NaN
        self.system.emotions.state._vector[0] = float('nan')
        
        # 2. Tick the system
        # The evolution or heal() should detect NaN and reset to baseline
        self.system.tick()
        
        # 3. Verify recovery
        joy = self.system.emotions.state.joy
        self.assertFalse(math.isnan(joy))
        self.assertEqual(joy, self.system.emotions.state.BASELINE[0])

    def test_state_persistence(self):
        # 1. Modify state
        self.system.emotions.state.joy = 0.9
        self.system.tick_count = 300 # Trigger auto-save on next tick (or manual)
        self.system._save_state()
        
        self.assertTrue(os.path.exists("brio_state.json"))
        
        # 2. Create new system instance
        new_system = BrioSystem()
        # It should auto-load in __init__
        
        # 3. Verify joy is restored
        self.assertAlmostEqual(new_system.emotions.state.joy, 0.9, places=2)

    def test_supervisor_error_catch(self):
        # 1. Force a crash in one of the sub-modules' behavior
        # (Mocking gather_sensor_data to raise exception)
        original_sensor_func = self.system._gather_sensor_data
        def faulty_sensors():
            raise Exception("Sensor Hardware Failure!")
        self.system._gather_sensor_data = faulty_sensors
        
        # 2. Tick should NOT crash the entire process
        # It should catch the error and return an error status
        result = self.system.tick()
        
        self.assertEqual(result.get("status"), "ERROR")
        # Check watchdog logged it
        status = self.system.watchdog.get_system_status()
        self.assertEqual(status["overall"], "critical")
        self.assertGreater(status["details"]["HeartLoop"]["errors"], 0)

if __name__ == '__main__':
    unittest.main()


