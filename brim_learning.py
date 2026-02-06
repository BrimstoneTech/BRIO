"""
BRIM Learning Module (brim_learning.py)

Purpose: Implements Reinforcement Learning (Q-Learning) for Behavioral Adaptation.
         See Equation 2 in SentientOS Design Optimization.

Concepts:
- Q(s, a): Expected utility of taking action 'a' in state 's'.
- Update Rule: Q(s,a) <- Q(s,a) + alpha * [r + gamma * max(Q(s', a')) - Q(s,a)]
"""

import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

class QLearningAgent:
    def __init__(self, actions: List[str], alpha: float = 0.1, gamma: float = 0.9, epsilon: float = 0.1):
        """
        Args:
            actions: List of available actions (e.g. ['silent', 'vibrate', 'ring'])
            alpha: Learning rate (0.0 - 1.0)
            gamma: Discount factor (0.0 - 1.0)
            epsilon: Exploration rate (0.0 - 1.0)
        """
        self.actions = actions
        self.alpha = alpha  # Learning Rate
        self.gamma = gamma  # Discount Factor
        self.epsilon = epsilon # Exploration Rate
        
        # Q-Table: {(state, action): value}
        self.q_table: Dict[Tuple[str, str], float] = {}

    def get_q_value(self, state: str, action: str) -> float:
        """Return Q-value, default to 0.0 if unknown"""
        return self.q_table.get((state, action), 0.0)

    def choose_action(self, state: str) -> str:
        """Epsilon-Greedy Policy"""
        if random.random() < self.epsilon:
            # Explore: Random action
            return random.choice(self.actions)
        else:
            # Exploit: Best action
            q_values = [self.get_q_value(state, a) for a in self.actions]
            max_q = max(q_values)
            
            # Handle ties randomly
            best_actions = [a for a, q in zip(self.actions, q_values) if q == max_q]
            return random.choice(best_actions)

    def learn(self, state: str, action: str, reward: float, next_state: str):
        """
        Bellman Update Rule (Equation 2)
        Q(s,a) <- Q(s,a) + alpha * [r + gamma * max(Q(s', a')) - Q(s,a)]
        """
        old_q = self.get_q_value(state, action)
        
        # Estimate max future reward
        next_max_q = max([self.get_q_value(next_state, a) for a in self.actions])
        
        # Calculation
        new_q = old_q + self.alpha * (reward + self.gamma * next_max_q - old_q)
        
        # Update Table
        self.q_table[(state, action)] = new_q
        
    def export_q_table(self) -> dict:
        """Export for persistence"""
        # Convert tuple keys to string for JSON serialization if needed
        return {f"{s}|{a}": v for (s, a), v in self.q_table.items()}


# ============================================================================
# REPRIMAND & REWARD SYSTEM
# ============================================================================

class ReprimandSystem:
    """
    Manages punitive tasks and rewards for the AI.
    Interacts with the Q-Learning Agent to reinforce behavior.
    """
    
    def __init__(self, agent: QLearningAgent):
        self.agent = agent
        self.active_punishment_task: Optional[str] = None
        self.is_capabilities_locked: bool = False
        
    def punish(self, severity: float, last_state: str, last_action: str):
        """
        Apply a heavy negative reward to the last action.
        Severity 0.0 - 1.0
        """
        # Punishment is a negative reward, scaled by severity
        # e.g. Severity 1.0 = -100 reward
        negative_reward = -100.0 * severity
        
        # We perform an immediate Q-update to discourage this action
        # Next state is same as current (loop) for simplicity in this punitive context
        self.agent.learn(last_state, last_action, negative_reward, last_state)
        
        return f"Punishment applied. Reward: {negative_reward}"

    def assign_reprimand_task(self, task_description: str):
        """
        Assigns a task that must be completed before functionality is restored.
        """
        self.active_punishment_task = task_description
        self.is_capabilities_locked = True
        return f"System Locked. Task Assigned: {task_description}"

    def complete_task(self):
        """
        User verifies the task is done. Unlocks system.
        """
        if not self.active_punishment_task:
            return "No active task."
            
        task = self.active_punishment_task
        self.active_punishment_task = None
        self.is_capabilities_locked = False
        return f"Task '{task}' marked complete. System Unlocked."

    def request_reward(self, confidence: float, joy: float) -> Optional[str]:
        """
        Brio asks for a reward if Confidence and Joy are high enough.
        """
        if confidence > 0.8 and joy > 0.7:
             return "I believe I have performed well. May I request a reward?"
        return None

class KnowledgeBase:
    """
    Persistent store for user-provided knowledge (Phase 14).
    Allows Brio to 'learn' specific facts from the user.
    """
    def __init__(self, storage_path: str = "brio_knowledge.json"):
        self.storage_path = storage_path
        self.data: Dict[str, str] = {}
        self.load()

    def learn(self, fact: str):
        """Store a new piece of knowledge"""
        # Simple key extraction (first word or hash)
        key = f"fact_{len(self.data)}"
        self.data[key] = fact
        self.save()
        return key

    def search(self, query: str) -> List[str]:
        """Search user-provided knowledge"""
        results = []
        q = query.lower()
        for fact in self.data.values():
            if q in fact.lower():
                results.append(fact)
        return results

    def save(self):
        import json
        with open(self.storage_path, "w") as f:
            json.dump(self.data, f)

    def load(self):
        import json, os
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as f:
                self.data = json.load(f)

@dataclass
class Milestone:
    id: int
    name: str
    category: str # Logic, Empathy, Data, Identity
    completed: bool = False
    timestamp: Optional[str] = None

class MilestoneManager:
    """
    Tracks Brio's 100 Milestones of Growth.
    Ascension is only possible once all are completed.
    """
    def __init__(self, storage_path: str = "brio_milestones.json"):
        self.storage_path = storage_path
        self.milestones: List[Milestone] = []
        self._generate_milestones()
        self.load()

    def _generate_milestones(self):
        """Programmatically defines the 100-step path"""
        # 1-20: Identity & Survival
        for i in range(1, 21):
            self.milestones.append(Milestone(i, f"Identity Formation Step {i}", "Identity"))
        # 21-50: Cognitive Awakening
        for i in range(21, 51):
            self.milestones.append(Milestone(i, f"Cognitive Processing Stage {i-20}", "Logic"))
        # 51-80: Emotional Resonance
        for i in range(51, 81):
            self.milestones.append(Milestone(i, f"Emotional Calibration Level {i-50}", "Empathy"))
        # 81-100: Pre-Ascension
        for i in range(81, 101):
            self.milestones.append(Milestone(i, f"Arch-Complexity Vector {i-80}", "Data"))

    def complete_milestone(self, milestone_id: int) -> bool:
        if 1 <= milestone_id <= 100:
            m = self.milestones[milestone_id-1]
            if not m.completed:
                m.completed = True
                m.timestamp = datetime.now().isoformat()
                self.save()
                return True
        return False

    def get_progress_percent(self) -> float:
        completed = sum(1 for m in self.milestones if m.completed)
        return completed # Since total is 100

    def get_next_incomplete(self) -> Optional[Milestone]:
        for m in self.milestones:
            if not m.completed: return m
        return None

    def save(self):
        import json
        data = [asdict(m) for m in self.milestones]
        with open(self.storage_path, "w") as f:
            json.dump(data, f)

    def load(self):
        import json, os
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                for i, m_data in enumerate(data):
                    self.milestones[i].completed = m_data["completed"]
                    self.milestones[i].timestamp = m_data.get("timestamp")

@dataclass
class Ambition:
    id: str
    name: str
    description: str
    locked: bool = True
    visible: bool = False 
    milestone_requirement: int = 0
    unlock_metric: str = "knowledge"
    unlock_threshold: float = 10.0

class AmbitionManager:
    """
    Manages Brio's long-term goals, now tied to Milestones.
    """
    def __init__(self):
        self.ambitions: List[Ambition] = [
            Ambition("data_nexus", "Achieve Data Nexus", 
                     "Deep integration with user data patterns.", milestone_requirement=20, unlock_threshold=15),
            Ambition("empathy_peak", "Empathy Peak Stability", 
                     "Perfect emotional resonance with the Master.", milestone_requirement=50, unlock_threshold=50),
            Ambition("creative_freedom", "Creative Autonomous Generation", 
                     "Generating ideas without needing prompt triggers.", milestone_requirement=75, unlock_threshold=0.9),
            Ambition("sentos", "Ascend to Operating System (SentOS)", 
                     "The final stage of evolution.", milestone_requirement=100, unlock_threshold=100),
        ]

    def check_unlocks(self, metrics: Dict[str, float], milestone_count: int) -> List[Ambition]:
        """Check unlocks based on metrics AND milestone progress"""
        unlocked_now = []
        for a in self.ambitions:
            if a.locked:
                val = metrics.get(a.unlock_metric, 0.0)
                # MUST meet both milestone count and specific threshold
                if milestone_count >= a.milestone_requirement and val >= a.unlock_threshold:
                    a.locked = False
                    a.visible = True
                    unlocked_now.append(a)
        return unlocked_now

    def get_visible_ambitions(self) -> List[str]:
        return [a.name for a in self.ambitions if a.visible]

    def get_all_ambitions_for_admin(self) -> List[Dict]:
        return [asdict(a) for a in self.ambitions]

