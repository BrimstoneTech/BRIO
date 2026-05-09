"""
Brio Meta-Reasoning Module (brio_meta_reasoning.py)

Purpose: Gives BRIO the ability to reason about its own reasoning.
         Self-monitoring, strategy selection, confidence calibration,
         and knowing when it doesn't know.

Concepts:
- Metacognitive Monitoring: Track reasoning quality in real-time
- Strategy Selection: Choose the best thinking approach for each problem
- Confidence Calibration: Know how certain you really are vs how certain you feel
- Epistemic Humility: Detect knowledge gaps and say "I don't know" honestly
- Reflection: After-action review of past reasoning to improve

Author: BrimstoneTech
Version: 1.0
Dependencies: None (stdlib only)
"""

import time
import math
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# THINKING STRATEGIES
# ============================================================================

class ThinkingStrategy(Enum):
    """Available reasoning strategies BRIO can select from."""
    ANALYTICAL = "analytical"       # Step-by-step logical deduction
    CREATIVE = "creative"           # Lateral thinking, novel connections
    EMPATHETIC = "empathetic"       # Understanding emotions and perspectives
    MEMORY_RECALL = "memory_recall" # Searching past knowledge
    ANALOGICAL = "analogical"       # Reasoning by analogy
    DECOMPOSITION = "decomposition" # Break complex into simple parts
    INTUITIVE = "intuitive"         # Fast pattern-matching (System 1)
    DELIBERATE = "deliberate"       # Slow careful reasoning (System 2)


class ConfidenceLevel(Enum):
    """Calibrated confidence levels."""
    CERTAIN = "certain"           # >0.9 — I know this well
    CONFIDENT = "confident"       # 0.7-0.9 — Pretty sure
    UNCERTAIN = "uncertain"       # 0.4-0.7 — Could go either way
    GUESSING = "guessing"         # 0.2-0.4 — Mostly guessing
    NO_IDEA = "no_idea"           # <0.2 — I genuinely don't know


# ============================================================================
# REASONING TRACE
# ============================================================================

@dataclass
class ReasoningStep:
    """A single step in a chain of reasoning."""
    step_number: int
    thought: str
    strategy_used: ThinkingStrategy
    confidence: float
    time_taken_ms: float
    detected_issues: List[str] = field(default_factory=list)


@dataclass
class ReasoningTrace:
    """Complete trace of a reasoning process — BRIO's inner monologue."""
    question: str
    steps: List[ReasoningStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    final_confidence: float = 0.0
    strategy_used: ThinkingStrategy = ThinkingStrategy.ANALYTICAL
    total_time_ms: float = 0.0
    was_revised: bool = False
    knowledge_gaps: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# META-REASONING ENGINE
# ============================================================================

class MetaReasoner:
    """
    BRIO's metacognitive engine. Monitors and improves reasoning.

    Usage:
        meta = MetaReasoner()

        # Before answering
        strategy = meta.select_strategy("What is the meaning of life?")

        # During answering
        meta.begin_trace("What is the meaning of life?", strategy)
        meta.log_step("This is a philosophical question", confidence=0.3)
        meta.log_step("Multiple frameworks exist: existentialist, absurdist...", confidence=0.5)

        # After answering
        trace = meta.complete_trace("There is no single answer, but...")
        reflection = meta.reflect(trace)
    """

    def __init__(self):
        self.traces: List[ReasoningTrace] = []
        self.active_trace: Optional[ReasoningTrace] = None
        self.strategy_performance: Dict[str, List[float]] = {
            s.value: [] for s in ThinkingStrategy
        }
        self.calibration_log: List[Tuple[float, bool]] = []  # (predicted_conf, was_correct)

    # ── Strategy Selection ──────────────────────────────────────────────

    def select_strategy(self, question: str, emotional_state: Optional[Dict] = None) -> ThinkingStrategy:
        """
        Choose the best thinking strategy based on the question type
        and past performance of each strategy.
        """
        q = question.lower()

        # Heuristic classification
        if any(w in q for w in ["feel", "emotion", "sad", "happy", "afraid", "love"]):
            candidate = ThinkingStrategy.EMPATHETIC
        elif any(w in q for w in ["why", "because", "reason", "cause", "explain"]):
            candidate = ThinkingStrategy.ANALYTICAL
        elif any(w in q for w in ["imagine", "what if", "create", "invent", "dream"]):
            candidate = ThinkingStrategy.CREATIVE
        elif any(w in q for w in ["remember", "last time", "before", "history"]):
            candidate = ThinkingStrategy.MEMORY_RECALL
        elif any(w in q for w in ["like", "similar", "compare", "analogy"]):
            candidate = ThinkingStrategy.ANALOGICAL
        elif any(w in q for w in ["complex", "steps", "plan", "break down"]):
            candidate = ThinkingStrategy.DECOMPOSITION
        elif len(q.split()) < 5:
            candidate = ThinkingStrategy.INTUITIVE  # Short = fast response
        else:
            candidate = ThinkingStrategy.DELIBERATE  # Complex = think carefully

        # Override with past performance if we have enough data
        perf = self.strategy_performance.get(candidate.value, [])
        if len(perf) >= 5 and sum(perf) / len(perf) < 0.3:
            # This strategy has been performing poorly — try deliberate instead
            candidate = ThinkingStrategy.DELIBERATE

        return candidate

    # ── Reasoning Trace ─────────────────────────────────────────────────

    def begin_trace(self, question: str, strategy: ThinkingStrategy):
        """Start tracking a new reasoning process."""
        self.active_trace = ReasoningTrace(
            question=question,
            strategy_used=strategy
        )

    def log_step(self, thought: str, confidence: float,
                 strategy: Optional[ThinkingStrategy] = None,
                 issues: Optional[List[str]] = None):
        """Log a single reasoning step."""
        if not self.active_trace:
            return

        step = ReasoningStep(
            step_number=len(self.active_trace.steps) + 1,
            thought=thought,
            strategy_used=strategy or self.active_trace.strategy_used,
            confidence=max(0.0, min(1.0, confidence)),
            time_taken_ms=0,
            detected_issues=issues or []
        )
        self.active_trace.steps.append(step)

    def complete_trace(self, final_answer: str) -> ReasoningTrace:
        """Finish the current reasoning trace and archive it."""
        if not self.active_trace:
            # Create a minimal trace
            self.active_trace = ReasoningTrace(question="unknown")

        self.active_trace.final_answer = final_answer

        # Calculate final confidence from step confidences
        if self.active_trace.steps:
            confidences = [s.confidence for s in self.active_trace.steps]
            # Final confidence is influenced by lowest step (weakest link)
            # and the average
            avg = sum(confidences) / len(confidences)
            minimum = min(confidences)
            self.active_trace.final_confidence = 0.6 * avg + 0.4 * minimum
        else:
            self.active_trace.final_confidence = 0.5

        # Detect knowledge gaps
        self.active_trace.knowledge_gaps = self._detect_gaps()

        self.active_trace.total_time_ms = (time.time() - self.active_trace.timestamp) * 1000

        # Archive
        trace = self.active_trace
        self.traces.append(trace)
        self.active_trace = None

        return trace

    # ── Confidence Calibration ──────────────────────────────────────────

    def get_calibrated_confidence(self, raw_confidence: float) -> Tuple[float, ConfidenceLevel]:
        """
        Calibrate raw confidence using historical accuracy.
        If BRIO has been overconfident, this adjusts downward.
        """
        if len(self.calibration_log) < 10:
            # Not enough history, return raw
            calibrated = raw_confidence
        else:
            # Calculate calibration curve
            # Group predictions by confidence bucket
            buckets: Dict[int, List[bool]] = {}
            for conf, correct in self.calibration_log[-100:]:  # Last 100
                bucket = int(conf * 10)  # 0-10
                buckets.setdefault(bucket, []).append(correct)

            # Find actual accuracy for this confidence range
            bucket = int(raw_confidence * 10)
            if bucket in buckets and len(buckets[bucket]) >= 3:
                actual_accuracy = sum(buckets[bucket]) / len(buckets[bucket])
                # Blend raw with actual
                calibrated = 0.4 * raw_confidence + 0.6 * actual_accuracy
            else:
                calibrated = raw_confidence

        calibrated = max(0.0, min(1.0, calibrated))

        # Map to level
        if calibrated > 0.9:
            level = ConfidenceLevel.CERTAIN
        elif calibrated > 0.7:
            level = ConfidenceLevel.CONFIDENT
        elif calibrated > 0.4:
            level = ConfidenceLevel.UNCERTAIN
        elif calibrated > 0.2:
            level = ConfidenceLevel.GUESSING
        else:
            level = ConfidenceLevel.NO_IDEA

        return calibrated, level

    def record_outcome(self, predicted_confidence: float, was_correct: bool):
        """Record whether a prediction was correct for calibration."""
        self.calibration_log.append((predicted_confidence, was_correct))
        # Keep last 500
        if len(self.calibration_log) > 500:
            self.calibration_log = self.calibration_log[-500:]

    # ── Reflection ──────────────────────────────────────────────────────

    def reflect(self, trace: ReasoningTrace) -> Dict:
        """
        After-action review: analyse a reasoning trace and extract lessons.
        """
        reflection = {
            "question": trace.question,
            "strategy_used": trace.strategy_used.value,
            "steps_taken": len(trace.steps),
            "final_confidence": round(trace.final_confidence, 3),
            "knowledge_gaps": trace.knowledge_gaps,
            "issues_detected": [],
            "lessons": [],
        }

        # Analyse reasoning quality
        if trace.steps:
            confidences = [s.confidence for s in trace.steps]

            # Check for confidence collapse (started high, ended low)
            if len(confidences) >= 2 and confidences[0] > 0.7 and confidences[-1] < 0.4:
                reflection["issues_detected"].append("confidence_collapse")
                reflection["lessons"].append(
                    "Started confident but lost certainty. May have encountered "
                    "contradictory evidence. Consider questioning initial assumptions sooner."
                )

            # Check for circular reasoning (same confidence throughout)
            if len(set(round(c, 1) for c in confidences)) == 1 and len(confidences) > 2:
                reflection["issues_detected"].append("stagnant_reasoning")
                reflection["lessons"].append(
                    "Confidence never changed. Reasoning may be circular or "
                    "not incorporating new information at each step."
                )

            # Check for overconfidence
            if trace.final_confidence > 0.9 and len(trace.knowledge_gaps) > 0:
                reflection["issues_detected"].append("overconfident_with_gaps")
                reflection["lessons"].append(
                    "High confidence despite identified knowledge gaps. "
                    "Should lower confidence when gaps exist."
                )

            # Collect all issues from steps
            for step in trace.steps:
                reflection["issues_detected"].extend(step.detected_issues)

        # Update strategy performance
        perf_score = trace.final_confidence  # Proxy for quality
        strategy_key = trace.strategy_used.value
        self.strategy_performance[strategy_key].append(perf_score)
        # Keep last 20 per strategy
        if len(self.strategy_performance[strategy_key]) > 20:
            self.strategy_performance[strategy_key] = self.strategy_performance[strategy_key][-20:]

        return reflection

    def should_say_i_dont_know(self, trace: ReasoningTrace) -> bool:
        """
        Epistemic humility: determine if BRIO should honestly say
        it doesn't know rather than guessing.
        """
        _, level = self.get_calibrated_confidence(trace.final_confidence)

        if level in (ConfidenceLevel.NO_IDEA, ConfidenceLevel.GUESSING):
            return True
        if len(trace.knowledge_gaps) >= 3:
            return True
        if trace.steps and all(s.confidence < 0.3 for s in trace.steps):
            return True

        return False

    # ── Internal Helpers ────────────────────────────────────────────────

    def _detect_gaps(self) -> List[str]:
        """Detect knowledge gaps from the active trace."""
        gaps = []
        if not self.active_trace:
            return gaps

        for step in self.active_trace.steps:
            thought = step.thought.lower()
            if any(phrase in thought for phrase in [
                "not sure", "don't know", "unclear", "might be",
                "possibly", "i think", "need to check", "uncertain"
            ]):
                gaps.append(step.thought[:100])

        return gaps

    # ── Stats ───────────────────────────────────────────────────────────

    def get_stats(self) -> Dict:
        """Return meta-reasoning statistics."""
        if not self.traces:
            return {"total_traces": 0}

        avg_conf = sum(t.final_confidence for t in self.traces) / len(self.traces)
        avg_steps = sum(len(t.steps) for t in self.traces) / len(self.traces)

        strategy_counts = {}
        for t in self.traces:
            s = t.strategy_used.value
            strategy_counts[s] = strategy_counts.get(s, 0) + 1

        return {
            "total_traces": len(self.traces),
            "avg_confidence": round(avg_conf, 3),
            "avg_steps_per_trace": round(avg_steps, 1),
            "strategy_distribution": strategy_counts,
            "total_knowledge_gaps_found": sum(len(t.knowledge_gaps) for t in self.traces),
            "calibration_data_points": len(self.calibration_log),
        }


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    meta = MetaReasoner()

    # Simulate reasoning about a question
    question = "What is the relationship between consciousness and free will?"
    strategy = meta.select_strategy(question)
    print(f"Selected strategy: {strategy.value}")

    meta.begin_trace(question, strategy)
    meta.log_step("This is a deep philosophical question with no definitive answer", confidence=0.3)
    meta.log_step("Multiple frameworks exist: compatibilism, libertarianism, hard determinism", confidence=0.5)
    meta.log_step("I'm not sure which framework is most defensible", confidence=0.35)
    meta.log_step("The relationship depends on how we define both terms", confidence=0.6)

    trace = meta.complete_trace("Consciousness and free will are deeply intertwined but their relationship depends on philosophical framework.")

    print(f"\nFinal confidence: {trace.final_confidence:.2f}")
    print(f"Knowledge gaps: {trace.knowledge_gaps}")
    print(f"Should say 'I don't know': {meta.should_say_i_dont_know(trace)}")

    reflection = meta.reflect(trace)
    print(f"\nReflection: {json.dumps(reflection, indent=2)}")
