
import math
import random
from typing import List, Dict, Tuple, Optional

class SubjectiveOpinion:
    """
    Implements Subjective Logic (Eq. 5).
    Represents an opinion as (b, d, u, a) where:
    b = belief, d = disbelief, u = uncertainty, a = base rate.
    b + d + u = 1
    """
    def __init__(self, b: float, d: float, u: float, a: float = 0.5):
        total = b + d + u
        self.b = b / total
        self.d = d / total
        self.u = u / total
        self.a = a

    def get_probability_expectation(self) -> float:
        """E(x) = b + a*u"""
        return self.b + (self.a * self.u)

    @staticmethod
    def fuse(o1: 'SubjectiveOpinion', o2: 'SubjectiveOpinion') -> 'SubjectiveOpinion':
        """
        Consensus Operator for independent opinions.
        Fuses two opinions into one.
        """
        denom = o1.u + o2.u - (o1.u * o2.u)
        if denom == 0:
            return o1 # Fallback
            
        b = (o1.b * o2.u + o2.b * o1.u) / denom
        d = (o1.d * o2.u + o2.d * o1.u) / denom
        u = (o1.u * o2.u) / denom
        
        # Combined base rate (simplified)
        a = (o1.a + o2.a) / 2
        return SubjectiveOpinion(b, d, u, a)

class EntropyCalculator:
    """
    Implements Information Entropy (Eq. 4).
    H(X) = -sum(p_i * log2(p_i))
    """
    @staticmethod
    def calculate_text_entropy(text: str) -> float:
        if not text:
            return 0.0
            
        # Character-level entropy as a proxy for command ambiguity/complexity
        prob = [text.count(c) / len(text) for c in set(text)]
        entropy = -sum(p * math.log2(p) for p in prob)
        return entropy

    @staticmethod
    def calculate_decision_entropy(probabilities: List[float]) -> float:
        """Calculates entropy of a probability distribution (e.g., Q-values)"""
        # Ensure no zeros for log
        safe_p = [max(1e-9, p) for p in probabilities]
        # Normalize
        total = sum(safe_p)
        norm_p = [p / total for p in safe_p]
        
        return -sum(p * math.log2(p) for p in norm_p)

class DirichletModel:
    """
    Implements Dirichlet Distribution (Eq. 3) for multi-categorical learning.
    Used to prioritize ideas based on history.
    """
    def __init__(self, categories: List[str]):
        self.categories = categories
        # Alpha parameters (counts + 1 for prior)
        self.alphas = {cat: 1.0 for cat in categories}

    def update(self, category: str, weight: float = 1.0):
        """Update alpha parameters based on feedback"""
        if category in self.alphas:
            self.alphas[category] += weight

    def get_probabilities(self) -> Dict[str, float]:
        """Expected value of the distribution: E(Xi) = alpha_i / sum(alphas)"""
        total = sum(self.alphas.values())
        return {cat: a / total for cat, a in self.alphas.items()}

    def sample(self) -> str:
        """Weighted random selection based on current expectations"""
        probs = self.get_probabilities()
        cats = list(probs.keys())
        weights = list(probs.values())
        return random.choices(cats, weights=weights)[0]

# Testing cognition logic
if __name__ == "__main__":
    # Subjective Logic Test
    o1 = SubjectiveOpinion(0.7, 0.1, 0.2) # High belief
    o2 = SubjectiveOpinion(0.2, 0.6, 0.2) # High disbelief
    fused = SubjectiveOpinion.fuse(o1, o2)
    print(f"Fused Opinion: b={fused.b:.2f}, d={fused.d:.2f}, u={fused.u:.2f}")

    # Entropy Test
    h = EntropyCalculator.calculate_text_entropy("search the web for cat photos")
    print(f"Command Entropy: {h:.2f}")

    # Dirichlet Test
    d = DirichletModel(["Research", "Fun", "Maintenance"])
    d.update("Research", 5)
    print(f"Idea Probabilities: {d.get_probabilities()}")

from typing import Annotated, TypedDict
import operator

class BrioState(TypedDict):
    """
    BRIO's persistent identity and state for LangGraph orchestration.
    """
    # Core identity & Context
    brio_identity: Dict[str, str]
    conversation_history: Annotated[List[Dict[str, str]], operator.add]
    
    # Emotional & Neural State
    emotional_state: Dict[str, float]
    complexity_score: float
    confusion: float # 0.0 to 1.0
    
    # Flow Control
    current_mode: str # companion, teacher, learner, escalated
    topic_shift_severity: str # normal, radical
    intent: str # chat, feedback, vision, clarify
    requires_human: bool
    human_approved: bool
    
    # Context Buffers
    visual_context: Optional[str]
    working_memory: List[str]
    
    # I/O
    last_message: str
    response: str

class DecisionEngine:
    """
    High-level logic for sifting through Brio's processes.
    """
    @staticmethod
    def classify_intent(text: str) -> str:
        """
        Heuristic-based intent classification for v4.0 command-less control.
        Conservative: when in doubt, send to the LLM via "chat".
        """
        text_lower = text.lower().strip()
        words = set(text_lower.split())

        # Vision: only when clearly about screen/files
        if any(w in text_lower for w in ["this file", "what is this", "look at this"]):
            return "vision"

        # Feedback: only explicit, unambiguous feedback phrases
        # (NOT bare "yes"/"no" — those are normal conversation)
        feedback_phrases = [
            "good job", "bad brio", "well done brio", "great job",
            "fix your", "you're wrong", "that's wrong", "wrong answer",
            "try again", "not what i asked", "that's not right",
        ]
        if any(p in text_lower for p in feedback_phrases):
            return "feedback"

        # Query: question words, but only if they start the sentence
        # (avoids false positives like "I know what I want")
        query_starters = ["what ", "who ", "where ", "how ", "why ",
                          "when ", "tell me", "search ", "explain "]
        if any(text_lower.startswith(q) for q in query_starters):
            return "query"

        # Default: chat — always goes through the LLM
        return "chat"
    @staticmethod
    def detect_radical_shift(state: BrioState, threshold: float = 3.5) -> str:
        """
        Detects a radical shift in topic or intent using Entropy.
        Returns 'radical' or 'normal'.
        """
        history = state.get("conversation_history", [])
        if len(history) < 2:
            return "normal"
            
        # Compare entropy of last message vs previous message
        last_msg = history[-1].get("content", "")
        prev_msg = history[-2].get("content", "")
        
        h_last = EntropyCalculator.calculate_text_entropy(last_msg)
        h_prev = EntropyCalculator.calculate_text_entropy(prev_msg)
        
        # A radical shift is characterized by a high delta in information density
        return "radical" if abs(h_last - h_prev) > threshold else "normal"


