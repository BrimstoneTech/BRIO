
import unittest
from brio_communication import CommunicationCycle

class TestCommunicationCycle(unittest.TestCase):
    def setUp(self):
        self.cycle = CommunicationCycle("User", "Brio")

    def test_full_cycle(self):
        # 1. Reception
        self.cycle.reception("test command")
        self.assertEqual(self.cycle.message, "test command")

        # 2. Decode
        self.cycle.decode("Natural Language", 0.1)
        self.assertEqual(self.cycle.decoded_message, "test command")
        self.assertEqual(self.cycle.noise, 0.1)

        # 3. Cognition
        def mock_cognition(msg):
            return f"Processed: {msg}"
        
        result = self.cycle.cognition(mock_cognition)
        self.assertEqual(result, "Processed: test command")

        # 4. Context
        self.cycle.set_context("Test Context", 0.5)
        self.assertEqual(self.cycle.context, "Test Context")

        # 5. Encode
        self.cycle.encode("Response msg")
        self.assertEqual(self.cycle.encoded_message, "Response msg")

        # 6. Transmit
        transmitted_msg = []
        def mock_transmit(msg):
            transmitted_msg.append(msg)
        
        self.cycle.transmit(mock_transmit)
        self.assertEqual(transmitted_msg[0], "Response msg")

if __name__ == "__main__":
    unittest.main()


