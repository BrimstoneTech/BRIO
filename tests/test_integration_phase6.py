
import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brim_security import GhostProtocol
from brim_voice import VoiceEngine
from brim_main import BrimSystem

class TestIntegrationPhase6(unittest.TestCase):
    def test_ghost_protocol(self):
        gp = GhostProtocol()
        data = {"lat": 10.0, "long": 20.0, "name": "Brio"}
        
        # 1. Inactive (Transparent)
        clean = gp.obfuscate_telemetry(data)
        self.assertEqual(clean["lat"], 10.0)
        
        # 2. Active (Obfuscated)
        gp.activate()
        dirty = gp.obfuscate_telemetry(data)
        self.assertNotEqual(dirty["lat"], 10.0) # Should have noise
        self.assertEqual(dirty["name"], "Brio") # Strings untouched
        
    def test_voice_engine_init(self):
        # Should not crash even if libs missing
        v = VoiceEngine()
        self.assertIsNotNone(v)
        # Check dependencies string
        status = v.get_dependencies_status()
        self.assertIn("TTS", status)
        self.assertIn("STT", status)

    def test_main_loop_with_sensors(self):
        system = BrimSystem()
        state = system.tick()
        
        # Verify sensors key exists
        self.assertIn("sensors", state)
        self.assertIn("battery", state["sensors"])
        self.assertIn("cpu", state["sensors"])
        
        # Verify Web Bridge created
        self.assertIsNotNone(system.web)
        
    def test_voice_command_pass_through(self):
        system = BrimSystem()
        # "say" command should trigger voice.speak
        # We can't easily verify audio output, but we can verify no crash
        resp = system.handle_command("say Hello Test")
        self.assertIn("Speaking", resp)

if __name__ == '__main__':
    unittest.main()
