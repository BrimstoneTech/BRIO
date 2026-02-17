
import unittest
import sys
import os

# Add parent directory to path to import brio_learning
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brio_learning import QLearningAgent

class TestQLearning(unittest.TestCase):
    def setUp(self):
        self.actions = ['A', 'B']
        self.agent = QLearningAgent(self.actions, alpha=0.5, gamma=1.0, epsilon=0.0)

    def test_learn_update_rule(self):
        # Q(s,a) <- Q(s,a) + alpha * [r + gamma * max(Q(s', a')) - Q(s,a)]
        
        # 1. Initial State: Q("Start", "A") = 0
        state = "Start"
        action = "A"
        next_state = "End"
        reward = 100
        
        # Learn: 0 + 0.5 * [100 + 1.0 * 0 - 0] = 50
        self.agent.learn(state, action, reward, next_state)
        
        self.assertEqual(self.agent.get_q_value(state, action), 50.0)
        
    def test_exploitation(self):
        # Setup: Action A is better than B
        self.agent.q_table[("State1", "A")] = 10
        self.agent.q_table[("State1", "B")] = 5
        
        # Epsilon = 0, so should always choose best
        choice = self.agent.choose_action("State1")
        self.assertEqual(choice, "A")

if __name__ == '__main__':
    unittest.main()


