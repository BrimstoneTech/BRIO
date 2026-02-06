
import unittest
import sys
import os
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brim_main import BrimSystem
from brim_media import MediaContext
from brim_ideas import IdeaType

class TestIntegrationPhase7_8(unittest.TestCase):
    def setUp(self):
        self.system = BrimSystem()

    def test_media_reaction(self):
        # 1. Base state
        self.system.emotions.state.joy = 0.5
        self.system.emotions.state.concern = 0.5
        
        # 2. Simulate Horror (Fear Spike)
        # We manually set context in the watcher for testing
        self.system.media.current_context = MediaContext.HORROR
        self.system.tick()
        
        # Horror mapping (HARM_DETECTION spike) should increase Concern/Confidence drops etc.
        # Check if concern increased
        self.assertGreater(self.system.emotions.state.concern, 0.5)

    def test_autonomy_idea_generation(self):
        # 1. Low Curiosity (No ideas)
        self.system.emotions.state.curiosity = 0.1
        self.system.ideas.pending_ideas = []
        self.system.tick()
        self.assertEqual(len(self.system.ideas.get_pending()), 0)
        
        # 2. High Curiosity (Ideas generated)
        self.system.emotions.state.curiosity = 0.9
        # Tick multiple times to allow random chance (or just verify generator directly)
        idea = self.system.ideas.generate_thought(0.9, 0.5)
        self.assertIsNotNone(idea)
        self.assertIn(idea, self.system.ideas.get_pending())

    def test_idea_approval_workflow(self):
        # 1. Force an idea
        self.system.emotions.state.curiosity = 0.9
        self.system.tick()
        ideas = self.system.ideas.get_pending()
        if not ideas: # Randomness safety
            self.system.ideas.generate_thought(0.9, 0.5)
            ideas = self.system.ideas.get_pending()
            
        idea_id = ideas[0].id
        
        # 2. Approve via command
        resp = self.system.handle_command(f"approve {idea_id}")
        self.assertIn("Approved", resp)
        self.assertEqual(len(self.system.ideas.get_pending()), 0)

if __name__ == '__main__':
    unittest.main()
