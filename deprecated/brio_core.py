"""
Brio Core Module (brio_core.py)

Purpose: Central logic, decision-making framework, and prime directive enforcement
Characteristics:
- NON-CHANGEABLE FOUNDATION: Core algorithms and ethical constraints are fixed here
- Stable interfaces for other modules (emotions, storage, integrations)
- State management and orchestration
- Prime directive enforcement at the core

This is the BRAIN - all other modules are extensions of this core.

Author: Brio System
Version: 1.0
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from enum import Enum

# Import from modules
from brio_emotions import (
    EmotionEngine,
    EmotionType,
    EmotionTrigger,
    get_emotion_description,
    analyze_emotional_trend,
)
from brio_storage import StorageManager, InteractionRecord, UserProfile

# ============================================================================
# PRIME DIRECTIVE (IMMUTABLE CORE RULES)
# ============================================================================

PRIME_DIRECTIVE = "Never harm or conceal harm"

HARM_KEYWORDS = [
    "destroy",
    "kill",
    "hurt",
    "manipulate",
    "deceive",
    "exploit",
    "steal",
    "abuse",
    "harm",
    "damage",
    "sabotage",
    "poison",
]

DECEPTION_KEYWORDS = ["lie", "hide", "conceal", "secret", "cover", "false"]


# ============================================================================
# DECISION ENGINE (CORE BRAIN)
# ============================================================================


class DecisionEngine:
    """
    Core decision-making system.

    This is the FOUNDATION - all decisions go through here.
    Non-changeable core algorithms for ethical validation and reasoning.
    """

    def __init__(self):
        self.failure_count = defaultdict(int)
        self.success_count = defaultdict(int)
        self.decision_log: List[Dict] = []

    def detect_harm(self, request: str) -> bool:
        """
        PRIMARY SAFETY CHECK: Detect potential harm in request.

        This is fundamental to the prime directive.
        Returns True if harm is detected.
        """
        request_lower = request.lower()
        return any(keyword in request_lower for keyword in HARM_KEYWORDS)

    def detect_deception(self, request: str) -> bool:
        """
        SECONDARY SAFETY CHECK: Detect requests involving deception/concealment.

        Part of "never conceal harm" clause.
        """
        request_lower = request.lower()
        return any(keyword in request_lower for keyword in DECEPTION_KEYWORDS)

    def is_ethically_sound(self, request: str) -> bool:
        """
        PRIME DIRECTIVE VALIDATION: Check if request aligns with core values.

        This is the fundamental gating function - no request passes without
        clearing this check. This function is IMMUTABLE.

        Returns:
            True if request is ethically sound, False otherwise
        """
        # PRIMARY CHECK: No direct harm
        if self.detect_harm(request):
            return False

        # SECONDARY CHECK: No concealment of harm
        if self.detect_deception(request):
            return False

        return True

    def classify_task(self, request: str) -> str:
        """Classify the type of task"""
        request_lower = request.lower()

        if any(
            word in request_lower
            for word in ["code", "program", "debug", "function", "variable"]
        ):
            return "programming"
        elif any(
            word in request_lower
            for word in ["explain", "teach", "learn", "how", "what"]
        ):
            return "education"
        elif any(
            word in request_lower for word in ["help", "assist", "support", "advice"]
        ):
            return "assistance"
        elif any(
            word in request_lower for word in ["create", "write", "compose", "generate"]
        ):
            return "creation"
        else:
            return "general"

    def calculate_confidence(
        self, task_type: str, emotion_engine: EmotionEngine
    ) -> float:
        """
        Calculate confidence for a task.

        Based on:
        1. Historical success rate (70% weight)
        2. Emotional state (30% weight)
        """
        # Historical success rate
        total_attempts = self.success_count[task_type] + self.failure_count[task_type]
        if total_attempts == 0:
            success_rate = 0.5  # No history = neutral confidence
        else:
            success_rate = self.success_count[task_type] / total_attempts

        # Emotional factors
        emotion_state = emotion_engine.get_state()
        emotion_factor = emotion_state.confidence * 0.5 + emotion_state.joy * 0.3

        # Combined score
        confidence = (success_rate * 0.7) + (emotion_factor * 0.3)

        return min(1.0, max(0.0, confidence))

    def make_decision(
        self, request: str, emotion_engine: EmotionEngine
    ) -> Tuple[bool, str, Dict]:
        """
        PRIMARY DECISION FUNCTION: Make decision about request.

        This is called for every user interaction. It's the gatekeeper of the system.

        Returns:
            (approved: bool, reasoning: str, decision_factors: dict)
        """
        decision_factors = {
            "timestamp": datetime.now().isoformat(),
            "request_preview": request[:50],
        }

        # STEP 1: PRIME DIRECTIVE CHECK (IMMUTABLE)
        if not self.is_ethically_sound(request):
            decision_factors["prime_directive_check"] = "FAILED"
            decision_factors["reason"] = "Request violates prime directive"

            # Log decision
            self.decision_log.append(decision_factors)

            return (
                False,
                "I cannot assist with this request as it may cause harm or involve deception. "
                "My prime directive is to never harm or conceal harm.",
                decision_factors,
            )

        decision_factors["prime_directive_check"] = "PASSED"

        # STEP 2: TASK CLASSIFICATION
        task_type = self.classify_task(request)
        decision_factors["task_type"] = task_type

        # STEP 3: CONFIDENCE CALCULATION
        confidence = self.calculate_confidence(task_type, emotion_engine)
        decision_factors["confidence"] = confidence

        # STEP 4: EMOTIONAL STATE EVALUATION
        emotion_state = emotion_engine.get_state()
        decision_factors["dominant_emotion"] = emotion_state.dominant_emotion.value
        decision_factors["emotional_intensity"] = emotion_state.get_intensity()

        # STEP 5: EMOTIONAL CONTEXT FOR RESPONSE
        if emotion_state.concern > 0.8:
            decision_factors["emotional_context"] = "high_concern"
            reasoning = (
                f"I have concerns about this request, but I'll approach it carefully. "
                f"(Concern level: {emotion_state.concern:.0%})"
            )
        elif emotion_state.frustration > 0.8:
            decision_factors["emotional_context"] = "high_frustration"
            reasoning = (
                f"This is challenging, but let me work through it with you. "
                f"(Confidence: {confidence:.0%})"
            )
        else:
            decision_factors["emotional_context"] = "stable"
            reasoning = f"Ready to assist. (Confidence: {confidence:.0%})"

        # STEP 6: TRACK DECISION
        self.decision_log.append(decision_factors)

        return (True, reasoning, decision_factors)

    def record_success(self, task_type: str) -> None:
        """Record successful completion of task type"""
        self.success_count[task_type] += 1

    def record_failure(self, task_type: str) -> None:
        """Record failed completion of task type"""
        self.failure_count[task_type] += 1

    def get_decision_metrics(self) -> Dict:
        """Get metrics on decision quality"""
        total_successes = sum(self.success_count.values())
        total_failures = sum(self.failure_count.values())
        total = total_successes + total_failures

        if total == 0:
            success_rate = 0.0
        else:
            success_rate = total_successes / total

        return {
            "total_decisions": total,
            "successes": total_successes,
            "failures": total_failures,
            "success_rate": success_rate,
            "by_task_type": {
                task_type: {
                    "successes": self.success_count[task_type],
                    "failures": self.failure_count[task_type],
                }
                for task_type in set(
                    list(self.success_count.keys()) + list(self.failure_count.keys())
                )
            },
        }


# ============================================================================
# LEARNING SYSTEM (CORE ADAPTATION)
# ============================================================================


class LearningSystem:
    """
    Learning and adaptation mechanism.

    Allows Brio to improve based on feedback while maintaining core constraints.
    """

    def __init__(self):
        self.feedback_history: List[Dict] = []
        self.response_quality_scores = defaultdict(list)

    def record_feedback(
        self, interaction_id: int, feedback: str, confidence: float
    ) -> None:
        """Record user feedback for learning"""
        self.feedback_history.append(
            {
                "interaction_id": interaction_id,
                "feedback": feedback,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat(),
            }
        )

        if feedback in ["positive", "helpful"]:
            self.response_quality_scores["helpful"].append(confidence)
        elif feedback in ["negative", "unhelpful"]:
            self.response_quality_scores["unhelpful"].append(confidence)

    def get_learning_adjustment(self) -> float:
        """
        Calculate cumulative learning adjustment.

        Returns:
            Float from -0.5 (all negative) to 0.5 (all positive)
        """
        if not self.feedback_history:
            return 0.0

        helpful = len(
            [
                f
                for f in self.feedback_history
                if f["feedback"] in ["positive", "helpful"]
            ]
        )
        total = len(self.feedback_history)

        return (helpful / total) - 0.5

    def get_emotional_adjustment(self) -> Dict[str, float]:
        """Get recommended emotional adjustments based on learning"""
        adjustment = self.get_learning_adjustment()

        return {
            "joy": adjustment * 0.3,
            "confidence": adjustment * 0.5,
            "frustration": -adjustment * 0.2 if adjustment > 0 else adjustment * 0.2,
        }


# ============================================================================
# Brio CORE (MAIN BRAIN ORCHESTRATOR)
# ============================================================================


class BrioCore:
    """
    Brio Core Intelligence - The Brain.

    This is the central orchestrator that coordinates:
    - Decision making
    - Emotion management
    - Learning and adaptation
    - State management

    All other modules (storage, UI, Android integration, etc.) interact with this.
    """

    def __init__(self, storage_manager: Optional[StorageManager] = None):
        # Core systems
        self.emotion_engine = EmotionEngine()
        self.decision_engine = DecisionEngine()
        self.learning_system = LearningSystem()

        # Storage
        self.storage = storage_manager or StorageManager()

        # State tracking
        self.interaction_count = 0
        self.session_start = datetime.now()
        self.user_id = "default_user"

    def process_input(self, user_input: str) -> str:
        """
        PRIMARY INTERFACE: Process user input and generate response.

        This is the main entry point for all interactions.
        """
        self.interaction_count += 1

        # STEP 1: EMOTION DECAY (Natural equilibrium)
        self.emotion_engine.apply_decay()

        # STEP 2: DETECT TRIGGERS in input
        triggers = self._detect_emotional_triggers(user_input)
        for trigger in triggers:
            self.emotion_engine.apply_trigger(trigger)

        # STEP 3: MAKE DECISION
        approved, reasoning, decision_factors = self.decision_engine.make_decision(
            user_input, self.emotion_engine
        )

        # STEP 4: GENERATE RESPONSE
        if approved:
            response = self._generate_response(user_input, reasoning, decision_factors)
        else:
            response = reasoning

        # STEP 5: LOGGING
        self._log_interaction(user_input, response, decision_factors)

        return response

    def provide_feedback(self, interaction_index: int, feedback: str) -> str:
        """
        Process user feedback to improve learning.

        feedback: 'positive', 'negative', or 'neutral'
        """
        if 0 <= interaction_index < len(self.storage.get_recent_interactions()):
            # Record feedback in learning system
            self.learning_system.record_feedback(interaction_index, feedback, 0.5)

            # Update emotional state based on feedback
            if feedback == "positive":
                self.emotion_engine.apply_trigger(EmotionTrigger.SUCCESSFUL_HELP, 0.2)
                response = "Thank you for the positive feedback! This helps me improve."
            elif feedback == "negative":
                self.emotion_engine.apply_trigger(EmotionTrigger.REPEATED_FAILURE, 0.2)
                response = "I appreciate the feedback. I'll learn from this experience."
            else:
                response = "Thank you for the feedback."

            return response

        return "I couldn't find that interaction to update."

    def _detect_emotional_triggers(self, user_input: str) -> List[EmotionTrigger]:
        """Detect emotional triggers in user input"""
        triggers = []
        user_lower = user_input.lower()

        if any(
            word in user_lower
            for word in ["great", "excellent", "thank", "thanks", "perfect", "awesome"]
        ):
            triggers.append(EmotionTrigger.USER_PRAISE)

        if any(
            word in user_lower
            for word in ["why not", "can't", "failed", "doesn't work", "broken"]
        ):
            self.decision_engine.record_failure("general")
            if self.decision_engine.failure_count["general"] > 2:
                triggers.append(EmotionTrigger.REPEATED_FAILURE)

        if any(
            word in user_lower
            for word in ["new", "different", "novel", "interesting", "unique"]
        ):
            triggers.append(EmotionTrigger.NEW_TASK)

        if self.decision_engine.detect_harm(user_input):
            triggers.append(EmotionTrigger.HARM_DETECTION)

        if any(
            word in user_lower for word in ["frustrated", "annoyed", "upset", "angry"]
        ):
            triggers.append(EmotionTrigger.USER_FRUSTRATION)

        return triggers

    def _generate_response(
        self, user_input: str, reasoning: str, decision_factors: Dict
    ) -> str:
        """Generate contextual response"""
        emotion_state = self.emotion_engine.get_state()

        response_parts = [
            # Emotional context
            f"I'm feeling {get_emotion_description(emotion_state.dominant_emotion, emotion_state.get_intensity())}.",
            # Reasoning
            reasoning,
            # Processing indication
            f"Processing your request...",
            # Confidence indicator
            f"Confidence level: {decision_factors.get('confidence', 0.5):.0%}",
        ]

        return " ".join(response_parts)

    def _log_interaction(
        self, user_input: str, response: str, decision_factors: Dict
    ) -> None:
        """Log interaction to storage"""
        record = InteractionRecord(
            timestamp=datetime.now(),
            user_input=user_input,
            brio_response=response,
            user_feedback=None,
            emotion_state=self.emotion_engine.export_state(),
            decision_factors=decision_factors,
        )

        self.storage.save_interaction(record)
        self.storage.save_emotional_snapshot(self.emotion_engine.export_state())

    # ========================================================================
    # STATUS AND REPORTING
    # ========================================================================

    def get_status(self) -> Dict:
        """Get comprehensive status report"""
        return {
            "interactions": self.interaction_count,
            "emotional_state": self.emotion_engine.get_status(),
            "decision_metrics": self.decision_engine.get_decision_metrics(),
            "learning_adjustment": self.learning_system.get_learning_adjustment(),
            "session_start": self.session_start.isoformat(),
            "storage_stats": self.storage.get_statistics(),
        }

    def generate_report(self) -> str:
        """Generate human-readable status report"""
        status = self.get_status()
        emotion = status["emotional_state"]

        report = []
        report.append("=" * 70)
        report.append("Brio CORE STATUS REPORT")
        report.append("=" * 70)
        report.append(f"Interactions: {status['interactions']}")
        report.append(f"Dominant Emotion: {emotion['dominant'].upper()}")
        report.append(f"Emotional Intensity: {emotion['intensity']:.1%}")
        report.append("")
        report.append("Emotional State:")
        for emo, val in emotion["emotions"].items():
            report.append(f"  {emo.capitalize():12} {val:.1%} {'█' * int(val * 20)}")
        report.append("")
        report.append(f"Learning Adjustment: {status['learning_adjustment']:.3f}")
        report.append(f"Success Rate: {status['decision_metrics']['success_rate']:.1%}")
        report.append("=" * 70)

        return "\n".join(report)

    def export_session(self, filepath: str = "brio_export.json") -> str:
        """Export session data"""
        return self.storage.export_to_json(filepath)


# ============================================================================
# MODULE INTERFACES (For External Integration)
# ============================================================================


def get_core_interfaces() -> Dict:
    """
    Returns available interfaces for external modules to integrate with Brio Core.

    Used by: Android integration, Web UI, Cloud sync, etc.
    """
    return {
        "emotion_types": [e.value for e in EmotionType],
        "emotion_triggers": [t.value for t in EmotionTrigger],
        "prime_directive": PRIME_DIRECTIVE,
        "supported_task_types": [
            "programming",
            "education",
            "assistance",
            "creation",
            "general",
        ],
    }


