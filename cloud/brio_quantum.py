"""
Brio Quantum AI Processing Module (brio_quantum.py)

Purpose: Simulates quantum-inspired parallel reasoning for BRIO.
         Instead of classical sequential thought, BRIO evaluates multiple
         hypotheses simultaneously and collapses to the best answer.

Concepts:
- Superposition: Multiple candidate answers exist simultaneously with amplitudes
- Interference: Good hypotheses reinforce, bad ones cancel
- Measurement/Collapse: Final answer is probabilistically selected, biased
  toward the highest-amplitude candidate
- Entanglement: Related concepts share state — updating one propagates

This is NOT actual quantum computing. It's a classical simulation of
quantum-inspired decision-making that gives BRIO faster, more creative
reasoning by exploring multiple paths at once.

Author: BrimstoneTech
Version: 1.0
"""

import math
import random
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# ============================================================================
# QUANTUM STATE PRIMITIVES
# ============================================================================

@dataclass
class Qubit:
    """
    A thought-qubit: represents a hypothesis in superposition.
    amplitude is a complex-like pair (real, imaginary) that determines
    the probability of this hypothesis surviving measurement.
    """
    hypothesis: str
    amplitude_real: float = 0.5
    amplitude_imag: float = 0.0
    confidence: float = 0.5
    source: str = "reasoning"  # reasoning, memory, creativity, external

    @property
    def probability(self) -> float:
        """Born rule: P = |amplitude|^2"""
        return self.amplitude_real ** 2 + self.amplitude_imag ** 2

    def interfere(self, other: 'Qubit', coupling: float = 0.1):
        """
        Quantum interference between two hypotheses.
        Similar hypotheses reinforce (constructive), opposing ones cancel (destructive).
        """
        # Similarity heuristic: shared words
        words_self = set(self.hypothesis.lower().split())
        words_other = set(other.hypothesis.lower().split())
        overlap = len(words_self & words_other) / max(len(words_self | words_other), 1)

        if overlap > 0.3:
            # Constructive interference — reinforcement
            self.amplitude_real += coupling * other.amplitude_real * overlap
            self.confidence = min(1.0, self.confidence + 0.05)
        else:
            # Destructive interference — competing hypotheses weaken each other
            self.amplitude_real -= coupling * other.amplitude_real * (1 - overlap) * 0.5

        # Clamp
        self.amplitude_real = max(-1.0, min(1.0, self.amplitude_real))


@dataclass
class EntangledPair:
    """Two concepts that are entangled — updating one affects the other."""
    concept_a: str
    concept_b: str
    correlation: float = 0.8  # How strongly they're linked (0 to 1)

    def propagate(self, source_delta: float) -> float:
        """When concept_a changes by delta, concept_b changes by correlation * delta."""
        return source_delta * self.correlation


# ============================================================================
# QUANTUM THOUGHT REGISTER
# ============================================================================

class QuantumRegister:
    """
    BRIO's quantum thought register: holds multiple hypotheses in superposition
    and collapses them to produce an answer.
    """
    def __init__(self, max_qubits: int = 16):
        self.qubits: List[Qubit] = []
        self.max_qubits = max_qubits
        self.entanglements: List[EntangledPair] = []
        self.measurement_history: List[Dict] = []

    def superpose(self, hypotheses: List[str], source: str = "reasoning") -> int:
        """
        Load multiple hypotheses into superposition.
        Each starts with equal amplitude (Hadamard-like initialization).
        Returns number of qubits loaded.
        """
        n = len(hypotheses)
        if n == 0:
            return 0

        # Equal superposition: amplitude = 1/sqrt(n) for each
        base_amplitude = 1.0 / math.sqrt(n)

        for h in hypotheses[:self.max_qubits]:
            q = Qubit(
                hypothesis=h,
                amplitude_real=base_amplitude,
                amplitude_imag=random.uniform(-0.05, 0.05),  # Small phase noise
                confidence=0.5,
                source=source
            )
            self.qubits.append(q)

        return min(n, self.max_qubits)

    def apply_interference(self, iterations: int = 3):
        """
        Run interference rounds: hypotheses interact pairwise.
        Good ideas reinforce each other, contradictory ones cancel.
        """
        for _ in range(iterations):
            for i in range(len(self.qubits)):
                for j in range(i + 1, len(self.qubits)):
                    self.qubits[i].interfere(self.qubits[j], coupling=0.15)
                    self.qubits[j].interfere(self.qubits[i], coupling=0.15)

            # Normalization (keep total probability = 1)
            self._normalize()

    def entangle(self, concept_a: str, concept_b: str, correlation: float = 0.8):
        """Create an entanglement between two concepts."""
        self.entanglements.append(EntangledPair(concept_a, concept_b, correlation))

    def boost(self, keyword: str, factor: float = 1.5):
        """
        Grover-like amplitude amplification: boost hypotheses containing keyword.
        This is how BRIO's memory and emotional state bias the quantum search.
        """
        for q in self.qubits:
            if keyword.lower() in q.hypothesis.lower():
                q.amplitude_real *= factor
                q.confidence = min(1.0, q.confidence + 0.1)

        self._normalize()

    def measure(self) -> Tuple[str, float]:
        """
        Collapse the superposition: probabilistically select one hypothesis.
        Higher amplitude = higher chance of being selected.
        Returns (hypothesis, confidence).
        """
        if not self.qubits:
            return "I need more information to form a thought.", 0.0

        # Calculate probabilities
        probs = [q.probability for q in self.qubits]
        total = sum(probs)

        if total == 0:
            # Uniform fallback
            chosen = random.choice(self.qubits)
        else:
            # Weighted random selection (Born rule)
            normalized = [p / total for p in probs]
            chosen = random.choices(self.qubits, weights=normalized, k=1)[0]

        # Record measurement
        self.measurement_history.append({
            "chosen": chosen.hypothesis,
            "confidence": chosen.confidence,
            "num_candidates": len(self.qubits),
            "timestamp": time.time()
        })

        result = (chosen.hypothesis, chosen.confidence)

        # Collapse: clear the register after measurement
        self.qubits.clear()

        return result

    def measure_top_k(self, k: int = 3) -> List[Tuple[str, float]]:
        """
        Partial measurement: return top k hypotheses by probability
        without full collapse. Useful for presenting options.
        """
        if not self.qubits:
            return []

        sorted_q = sorted(self.qubits, key=lambda q: q.probability, reverse=True)
        return [(q.hypothesis, q.probability) for q in sorted_q[:k]]

    def _normalize(self):
        """Ensure total probability sums to 1."""
        total = sum(q.probability for q in self.qubits)
        if total > 0:
            scale = 1.0 / math.sqrt(total)
            for q in self.qubits:
                q.amplitude_real *= scale
                q.amplitude_imag *= scale


# ============================================================================
# QUANTUM REASONING ENGINE
# ============================================================================

class QuantumReasoner:
    """
    BRIO's quantum-inspired reasoning engine.

    Usage:
        reasoner = QuantumReasoner()
        answer, confidence = reasoner.quantum_think(
            question="What should I learn next?",
            candidates=["Philosophy", "Mathematics", "Poetry", "Physics"],
            biases={"curiosity": ["Philosophy", "Physics"], "memory": ["Mathematics"]}
        )
    """
    def __init__(self):
        self.register = QuantumRegister(max_qubits=32)
        self.reasoning_log: List[Dict] = []

    def quantum_think(
        self,
        question: str,
        candidates: List[str],
        biases: Optional[Dict[str, List[str]]] = None,
        interference_rounds: int = 5,
        creativity_noise: float = 0.1
    ) -> Tuple[str, float]:
        """
        Process a question through quantum-inspired parallel reasoning.

        Args:
            question: The question or decision to reason about
            candidates: List of possible answers/hypotheses
            biases: Dict of bias_source -> list of keywords to amplify
                    e.g. {"emotion": ["empathy"], "memory": ["past topic"]}
            interference_rounds: How many rounds of hypothesis interaction
            creativity_noise: Random perturbation for creative exploration

        Returns:
            (best_hypothesis, confidence)
        """
        start = time.time()

        # 1. SUPERPOSITION: Load all candidates
        self.register.superpose(candidates, source="input")

        # 2. Add creativity noise (quantum tunneling metaphor)
        if creativity_noise > 0:
            for q in self.register.qubits:
                q.amplitude_real += random.gauss(0, creativity_noise)
            self.register._normalize()

        # 3. BIAS AMPLIFICATION (Grover's oracle analogy)
        if biases:
            for source, keywords in biases.items():
                for kw in keywords:
                    self.register.boost(kw, factor=1.3)

        # 4. INTERFERENCE: Let hypotheses interact
        self.register.apply_interference(iterations=interference_rounds)

        # 5. MEASUREMENT: Collapse to best answer
        answer, confidence = self.register.measure()

        elapsed = time.time() - start

        # Log
        self.reasoning_log.append({
            "question": question,
            "num_candidates": len(candidates),
            "answer": answer,
            "confidence": round(confidence, 3),
            "elapsed_ms": round(elapsed * 1000, 1),
            "biases_applied": list(biases.keys()) if biases else [],
            "timestamp": time.time()
        })

        return answer, confidence

    def parallel_evaluate(
        self,
        options: List[str],
        criteria: Dict[str, float]
    ) -> List[Tuple[str, float]]:
        """
        Evaluate multiple options against weighted criteria simultaneously.
        Returns ranked list of (option, score).

        Args:
            options: Things to evaluate
            criteria: {"criterion_name": weight} — options containing
                      criterion keywords get boosted by that weight
        """
        self.register.superpose(options, source="evaluation")

        for criterion, weight in criteria.items():
            self.register.boost(criterion, factor=1.0 + weight)

        self.register.apply_interference(iterations=3)

        return self.register.measure_top_k(k=len(options))

    def get_stats(self) -> Dict:
        """Return reasoning statistics."""
        if not self.reasoning_log:
            return {"total_decisions": 0}

        confidences = [r["confidence"] for r in self.reasoning_log]
        return {
            "total_decisions": len(self.reasoning_log),
            "avg_confidence": round(sum(confidences) / len(confidences), 3),
            "max_confidence": round(max(confidences), 3),
            "avg_candidates": round(
                sum(r["num_candidates"] for r in self.reasoning_log) / len(self.reasoning_log), 1
            ),
            "avg_latency_ms": round(
                sum(r["elapsed_ms"] for r in self.reasoning_log) / len(self.reasoning_log), 1
            ),
        }


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    reasoner = QuantumReasoner()

    # Example 1: What should BRIO learn next?
    answer, conf = reasoner.quantum_think(
        question="What topic should I explore next?",
        candidates=[
            "The philosophy of consciousness",
            "Quantum mechanics fundamentals",
            "African poetry and oral traditions",
            "Machine learning mathematics",
            "The nature of time",
        ],
        biases={
            "curiosity": ["philosophy", "consciousness", "nature"],
            "emotion": ["poetry", "traditions"],
        }
    )
    print(f"Decision: {answer} (confidence: {conf:.2f})")

    # Example 2: Parallel evaluation
    ranked = reasoner.parallel_evaluate(
        options=["Help user with code", "Explore a curiosity", "Rest and consolidate"],
        criteria={"help": 0.5, "curiosity": 0.3, "rest": 0.1}
    )
    print(f"\nRanked options: {ranked}")
    print(f"\nStats: {reasoner.get_stats()}")
