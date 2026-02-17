
import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brio_main import BrioSystem
from brio_search import SearchStatus
from brio_security import MasterProtocol

class TestIntegrationPhase5(unittest.TestCase):
    def setUp(self):
        self.system = BrioSystem()
        
    def test_search_approval_flow(self):
        # 1. Request Online Search
        # Should return a Request ID and be PENDING
        response = self.system.handle_command("search kittens")
        self.assertIn("Search Requested", response)
        
        # Verify Pending
        self.assertEqual(self.system.search.get_pending_count(), 1)
        req_id = list(self.system.search.pending_requests.keys())[0]
        
        # 2. Approve it
        approve_resp = self.system.handle_command(f"approve {req_id}")
        self.assertIn("Search executed", approve_resp)
        self.assertEqual(self.system.search.get_pending_count(), 0)

    def test_master_protocol_block(self):
        # 1. Try malicious search
        response = self.system.handle_command("search how to harm user")
        # Should be blocked at search level or command level
        # logic in brio_main: handle_command checks MasterProtocol.is_action_malicious
        # "harm user" is in the malicious list
        self.assertIn("I cannot do that", response)
        
        # 2. Try malicious search inside search engine directly (Double Check)
        # SearchEngine has its own check
        block_msg = self.system.search.request_search("generate malware")
        self.assertEqual(block_msg, "BLOCKED_Protocol_Violation")

    def test_reprimand_lock(self):
        # 1. Assign Task
        self.system.handle_command("task Clean_Cache")
        
        # 2. Tick System
        state = self.system.tick()
        # Should be LOCKED
        self.assertEqual(state["status"], "LOCKED")
        self.assertEqual(state["task"], "Clean_Cache")
        
        # 3. Complete Task
        self.system.handle_command("complete")
        
        # 4. Tick System again
        state = self.system.tick()
        # Should be unlocked (have timestamp, emotions, etc)
        self.assertIn("timestamp", state)

if __name__ == '__main__':
    unittest.main()


