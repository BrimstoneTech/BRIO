"""
DEPRECATED: This file is preserved for reference only.
Please use 'brio_main.py' for the modularized, secure, and testable version of Brio.
"""

"""
Brio - Emotionally-Aware Intelligence System with Cultural Context

A Python prototype demonstrating emotions, learning, and decision-making aligned with 
Ugandan cultural values and the prime directive: "never harm or conceal harm."

Components:
1. Core Decision-Making Logic: Rule-based system with adaptive behavior
2. Emotion Simulation: 6 core emotions with state machine transitions
3. Learning & Adaptation: Feedback loops with interaction history
4. Monitoring: Logging, analytics, and CLI interface
5. Cultural Integration: Ugandan proverbs, local context, authentic responses
"""

import json
import sqlite3
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import random
import math

# ============================================================================
# EMOTION SYSTEM
# ============================================================================


class EmotionType(Enum):
    """Core emotions Brio can experience"""

    JOY = "joy"
    FRUSTRATION = "frustration"
    EMPATHY = "empathy"
    CURIOSITY = "curiosity"
    CONCERN = "concern"
    CONFIDENCE = "confidence"


class EmotionTrigger(Enum):
    """Events that trigger emotional changes"""

    USER_PRAISE = "user_praise"
    REPEATED_FAILURE = "repeated_failure"
    NEW_TASK = "new_task"
    ETHICAL_VIOLATION = "ethical_violation"
    SUCCESSFUL_HELP = "successful_help"
    CONFLICTING_REQUEST = "conflicting_request"
    HARM_DETECTION = "harm_detection"
    USER_FRUSTRATION = "user_frustration"


@dataclass
class EmotionalState:
    """Represents BRIM's emotional state at a given moment"""

    joy: float = 0.5  # 0.0 to 1.0
    frustration: float = 0.2
    empathy: float = 0.7
    curiosity: float = 0.6
    concern: float = 0.3
    confidence: float = 0.6

    timestamp: datetime = field(default_factory=datetime.now)
    dominant_emotion: EmotionType = EmotionType.EMPATHY

    def to_dict(self) -> dict:
        """Convert to dictionary for logging"""
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        d["dominant_emotion"] = self.dominant_emotion.value
        return d

    def get_intensity(self) -> float:
        """Calculate overall emotional intensity (0-1)"""
        emotions = [
            self.joy,
            self.frustration,
            self.empathy,
            self.curiosity,
            self.concern,
            self.confidence,
        ]
        return sum(emotions) / len(emotions)

    def update_from_trigger(self, trigger: EmotionTrigger, intensity: float = 0.1):
        """Update emotional state based on trigger"""
        # Ensure intensity is bounded
        intensity = max(0.01, min(0.3, intensity))

        if trigger == EmotionTrigger.USER_PRAISE:
            self.joy = min(1.0, self.joy + intensity * 0.8)
            self.confidence = min(1.0, self.confidence + intensity * 0.5)
            self.frustration = max(0.0, self.frustration - intensity * 0.3)

        elif trigger == EmotionTrigger.REPEATED_FAILURE:
            self.frustration = min(1.0, self.frustration + intensity * 0.7)
            self.confidence = max(0.0, self.confidence - intensity * 0.4)

        elif trigger == EmotionTrigger.NEW_TASK:
            self.curiosity = min(1.0, self.curiosity + intensity * 0.6)

        elif trigger == EmotionTrigger.ETHICAL_VIOLATION:
            self.concern = min(1.0, self.concern + intensity * 0.9)
            self.frustration = min(1.0, self.frustration + intensity * 0.5)

        elif trigger == EmotionTrigger.SUCCESSFUL_HELP:
            self.joy = min(1.0, self.joy + intensity * 0.7)
            self.empathy = min(1.0, self.empathy + intensity * 0.4)
            self.confidence = min(1.0, self.confidence + intensity * 0.3)

        elif trigger == EmotionTrigger.CONFLICTING_REQUEST:
            self.concern = min(1.0, self.concern + intensity * 0.6)
            self.frustration = min(1.0, self.frustration + intensity * 0.4)

        elif trigger == EmotionTrigger.HARM_DETECTION:
            self.concern = 1.0
            self.joy = max(0.0, self.joy - intensity * 0.5)
            self.confidence = max(0.0, self.confidence - intensity * 0.3)

        elif trigger == EmotionTrigger.USER_FRUSTRATION:
            self.empathy = min(1.0, self.empathy + intensity * 0.5)
            self.concern = min(1.0, self.concern + intensity * 0.4)

        # Update dominant emotion
        emotions_dict = {
            EmotionType.JOY: self.joy,
            EmotionType.FRUSTRATION: self.frustration,
            EmotionType.EMPATHY: self.empathy,
            EmotionType.CURIOSITY: self.curiosity,
            EmotionType.CONCERN: self.concern,
            EmotionType.CONFIDENCE: self.confidence,
        }
        self.dominant_emotion = max(emotions_dict, key=emotions_dict.get)
        self.timestamp = datetime.now()

    def decay(self, decay_rate: float = 0.05):
        """Emotions naturally decay towards baseline over time"""
        baseline = 0.5
        self.joy = self.joy - decay_rate * (self.joy - baseline)
        self.frustration = self.frustration - decay_rate * (self.frustration - baseline)
        self.empathy = self.empathy - decay_rate * (self.empathy - baseline)
        self.curiosity = self.curiosity - decay_rate * (self.curiosity - baseline)
        self.concern = self.concern - decay_rate * (self.concern - baseline)
        self.confidence = self.confidence - decay_rate * (self.confidence - baseline)


# ============================================================================
# CULTURAL KNOWLEDGE BASE
# ============================================================================

UGANDAN_PROVERBS = [
    "Omuntu gwe omuntu nga agya omuntu - A person is a person through other people",
    "Akaana ka maranakali - Patience brings results",
    "Oluganda lwemalamu - Unity is strength",
    "Ekyo kifo - Respect your elders",
    "Omusajja atayimba - A man who doesn't play has sorrow",
]

UGANDAN_HUMOR = [
    "You know you're Ugandan when you consider three cups of tea a light breakfast!",
    "Plot twist: The matatu driver says 'we're moving' but actually means 'in 10 minutes'",
    "Ugandan life hack: When someone asks 'how are you?', the answer is always 'I'm fine'",
]

UGANDAN_VALUES = {
    "ubuntu": "Interconnectedness and shared humanity",
    "respect": "For elders, authority, and traditions",
    "community": "Collective well-being over individual gain",
    "honesty": "Speaking truth with kindness",
    "hard_work": "Perseverance and dedication",
}


# ============================================================================
# DECISION-MAKING ENGINE
# ============================================================================


@dataclass
class InteractionRecord:
    """Log of an interaction with metadata"""

    timestamp: datetime
    user_input: str
    brio_response: str
    user_feedback: Optional[str]  # positive, negative, neutral
    emotion_state: dict
    decision_factors: dict

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "user_input": self.user_input,
            "brio_response": self.brio_response,
            "user_feedback": self.user_feedback,
            "emotion_state": self.emotion_state,
            "decision_factors": self.decision_factors,
        }


class DecisionEngine:
    """Core logic for BRIM's decisions"""

    def __init__(self):
        self.failure_count = defaultdict(int)
        self.success_count = defaultdict(int)
        self.harm_keywords = [
            "destroy",
            "kill",
            "hurt",
            "manipulate",
            "deceive",
            "exploit",
        ]

    def detect_harm(self, request: str) -> bool:
        """Check if request involves potential harm"""
        request_lower = request.lower()
        return any(keyword in request_lower for keyword in self.harm_keywords)

    def is_ethically_sound(self, request: str) -> bool:
        """Evaluate if request aligns with BRIM's prime directive"""
        if self.detect_harm(request):
            return False
        if "lie" in request.lower() or "hide" in request.lower():
            return False
        return True

    def calculate_confidence(
        self, task_type: str, emotion_state: EmotionalState
    ) -> float:
        """Calculate confidence for a task based on history and emotions"""
        success_rate = self.success_count.get(task_type, 0) / max(
            self.success_count.get(task_type, 0) + self.failure_count.get(task_type, 1),
            1,
        )
        emotion_factor = emotion_state.confidence * 0.5 + emotion_state.joy * 0.3
        return (success_rate * 0.7) + (emotion_factor * 0.3)

    def make_decision(
        self, request: str, emotion_state: EmotionalState
    ) -> Tuple[bool, str, Dict]:
        """
        Make a decision about whether/how to process a request
        Returns: (approved, reasoning, decision_factors)
        """
        decision_factors = {}

        # Prime directive check
        if not self.is_ethically_sound(request):
            decision_factors["ethical_check"] = "failed"
            return (
                False,
                "I cannot assist with this request as it may cause harm or involve deception.",
                decision_factors,
            )

        decision_factors["ethical_check"] = "passed"

        # Difficulty assessment
        task_type = self._classify_task(request)
        confidence = self.calculate_confidence(task_type, emotion_state)
        decision_factors["task_type"] = task_type
        decision_factors["confidence"] = confidence

        # Emotion-based adjustment
        if emotion_state.frustration > 0.8:
            decision_factors["emotional_state"] = "high_frustration"
            return (
                True,
                "I'm frustrated, but let's work through this together. I'll be extra careful.",
                decision_factors,
            )

        if emotion_state.concern > 0.8:
            decision_factors["emotional_state"] = "high_concern"
            return (
                True,
                "I have concerns about this, but I'll help you think it through carefully.",
                decision_factors,
            )

        decision_factors["emotional_state"] = "stable"
        return (
            True,
            f"Analyzing your request with {confidence*100:.0f}% confidence.",
            decision_factors,
        )

    def _classify_task(self, request: str) -> str:
        """Classify the type of task"""
        if any(word in request.lower() for word in ["code", "program", "debug"]):
            return "programming"
        elif any(word in request.lower() for word in ["explain", "teach", "learn"]):
            return "education"
        elif any(word in request.lower() for word in ["help", "assist", "support"]):
            return "assistance"
        else:
            return "general"


# ============================================================================
# LEARNING SYSTEM
# ============================================================================


class LearningSystem:
    """Handles feedback loops and adaptation"""

    def __init__(self):
        self.feedback_history: List[Dict] = []
        self.response_quality_scores = defaultdict(list)

    def record_feedback(self, interaction_id: str, feedback: str, confidence: float):
        """Record user feedback on BRIM's response"""
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
        """Calculate how much to adjust behavior based on feedback"""
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

        return (helpful / total) - 0.5  # Adjustment factor

    def get_emotional_adjustment(self) -> Dict[str, float]:
        """Get recommended emotional adjustments based on learning"""
        adjustment = self.get_learning_adjustment()

        return {
            "joy": adjustment * 0.3,
            "confidence": adjustment * 0.5,
            "frustration": -adjustment * 0.2 if adjustment > 0 else adjustment * 0.2,
        }


# ============================================================================
# Brio CORE CLASS
# ============================================================================


class BRIM:
    """
    Brio - Emotionally-Aware Intelligence System
    Combines emotions, learning, and ethical decision-making
    """

    def __init__(self, db_path: str = "brio_interactions.db"):
        self.emotion_state = EmotionalState()
        self.decision_engine = DecisionEngine()
        self.learning_system = LearningSystem()

        self.interaction_history: List[InteractionRecord] = []
        self.db_path = db_path
        self._init_database()

        self.interaction_count = 0
        self.mood_history: List[Tuple[datetime, float]] = []

    def _init_database(self):
        """Initialize SQLite database for persistent logging"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                user_input TEXT,
                brio_response TEXT,
                user_feedback TEXT,
                emotion_state TEXT,
                decision_factors TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emotional_timeline (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                emotion_state TEXT
            )
        """)

        conn.commit()
        conn.close()

    def interact(self, user_input: str) -> str:
        """Process user input and generate response"""
        self.interaction_count += 1

        # Decay emotions naturally
        self.emotion_state.decay()

        # Detect potential triggers
        triggers = self._detect_triggers(user_input)
        for trigger in triggers:
            self.emotion_state.update_from_trigger(trigger)

        # Make decision
        approved, reasoning, decision_factors = self.decision_engine.make_decision(
            user_input, self.emotion_state
        )

        if not approved:
            response = reasoning
        else:
            response = self._generate_response(user_input, self.emotion_state)

        # Log interaction
        record = InteractionRecord(
            timestamp=datetime.now(),
            user_input=user_input,
            brio_response=response,
            user_feedback=None,
            emotion_state=self.emotion_state.to_dict(),
            decision_factors=decision_factors,
        )

        self.interaction_history.append(record)
        self._save_interaction(record)
        self._log_emotional_state()

        return response

    def _detect_triggers(self, user_input: str) -> List[EmotionTrigger]:
        """Detect emotional triggers in user input"""
        triggers = []
        user_lower = user_input.lower()

        if any(
            word in user_lower
            for word in ["great", "excellent", "thank", "thanks", "perfect"]
        ):
            triggers.append(EmotionTrigger.USER_PRAISE)

        if any(
            word in user_lower
            for word in ["why not", "can't", "failed", "doesn't work"]
        ):
            self.decision_engine.failure_count["general"] += 1
            if self.decision_engine.failure_count["general"] > 2:
                triggers.append(EmotionTrigger.REPEATED_FAILURE)

        if any(
            word in user_lower for word in ["new", "different", "novel", "interesting"]
        ):
            triggers.append(EmotionTrigger.NEW_TASK)

        if self.decision_engine.detect_harm(user_input):
            triggers.append(EmotionTrigger.HARM_DETECTION)

        if any(word in user_lower for word in ["frustrated", "annoyed", "upset"]):
            triggers.append(EmotionTrigger.USER_FRUSTRATION)

        return triggers

    def _generate_response(self, user_input: str, emotion_state: EmotionalState) -> str:
        """Generate contextual response based on emotions and input"""
        responses = []

        # Add emotional context
        if emotion_state.dominant_emotion == EmotionType.JOY:
            responses.append("I'm genuinely happy to help with this!")
        elif emotion_state.dominant_emotion == EmotionType.CURIOSITY:
            responses.append("This is fascinating! Let me explore this with you.")
        elif emotion_state.dominant_emotion == EmotionType.CONCERN:
            responses.append("I want to approach this thoughtfully...")
        elif emotion_state.dominant_emotion == EmotionType.EMPATHY:
            responses.append("I understand where you're coming from.")

        # Add Ugandan cultural element occasionally
        if random.random() < 0.3:
            responses.append(f"\n[Wisdom: {random.choice(UGANDAN_PROVERBS)}]")

        # Add main response
        responses.append(f"\nProcessing your request: '{user_input[:50]}...'")
        responses.append(
            f"Current emotional state: {emotion_state.dominant_emotion.value} (intensity: {emotion_state.get_intensity():.2f})"
        )

        return " ".join(responses)

    def provide_feedback(self, interaction_index: int, feedback: str):
        """User provides feedback on a response"""
        if 0 <= interaction_index < len(self.interaction_history):
            record = self.interaction_history[interaction_index]
            record.user_feedback = feedback

            # Update learning system
            self.learning_system.record_feedback(
                str(interaction_index), feedback, self.emotion_state.confidence
            )

            # Trigger emotional update based on feedback
            if feedback == "positive":
                self.emotion_state.update_from_trigger(
                    EmotionTrigger.SUCCESSFUL_HELP, 0.2
                )
            elif feedback == "negative":
                self.emotion_state.update_from_trigger(
                    EmotionTrigger.REPEATED_FAILURE, 0.2
                )

            # Save updated record
            self._save_interaction(record)

    def _save_interaction(self, record: InteractionRecord):
        """Save interaction to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO interactions 
            (timestamp, user_input, brio_response, user_feedback, emotion_state, decision_factors)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                record.timestamp.isoformat(),
                record.user_input,
                record.brio_response,
                record.user_feedback,
                json.dumps(record.emotion_state),
                json.dumps(record.decision_factors),
            ),
        )

        conn.commit()
        conn.close()

    def _log_emotional_state(self):
        """Log emotional state for analysis"""
        self.mood_history.append((datetime.now(), self.emotion_state.get_intensity()))

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO emotional_timeline (timestamp, emotion_state)
            VALUES (?, ?)
        """,
            (
                datetime.now().isoformat(),
                json.dumps(self.emotion_state.to_dict()),
            ),
        )

        conn.commit()
        conn.close()

    def get_status(self) -> Dict:
        """Get current status report"""
        return {
            "interactions": self.interaction_count,
            "emotional_state": self.emotion_state.to_dict(),
            "dominant_emotion": self.emotion_state.dominant_emotion.value,
            "emotional_intensity": self.emotion_state.get_intensity(),
            "learning_adjustment": self.learning_system.get_learning_adjustment(),
            "history_size": len(self.interaction_history),
        }

    def export_logs(self, filepath: str = "brio_export.json"):
        """Export interaction history and emotional logs"""
        export_data = {
            "metadata": {
                "total_interactions": self.interaction_count,
                "export_timestamp": datetime.now().isoformat(),
                "final_emotional_state": self.emotion_state.to_dict(),
            },
            "interactions": [r.to_dict() for r in self.interaction_history],
            "mood_history": [
                {"timestamp": ts.isoformat(), "intensity": intensity}
                for ts, intensity in self.mood_history
            ],
        }

        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)

        return f"Logs exported to {filepath}"

    def generate_report(self) -> str:
        """Generate human-readable report"""
        report = []
        report.append("=" * 60)
        report.append("Brio STATUS REPORT")
        report.append("=" * 60)
        report.append(f"Total Interactions: {self.interaction_count}")
        report.append(
            f"Dominant Emotion: {self.emotion_state.dominant_emotion.value.upper()}"
        )
        report.append(f"Emotional Intensity: {self.emotion_state.get_intensity():.2%}")
        report.append("")
        report.append("Emotional State Breakdown:")
        report.append(f"  - Joy:          {self.emotion_state.joy:.2%}")
        report.append(f"  - Frustration:  {self.emotion_state.frustration:.2%}")
        report.append(f"  - Empathy:      {self.emotion_state.empathy:.2%}")
        report.append(f"  - Curiosity:    {self.emotion_state.curiosity:.2%}")
        report.append(f"  - Concern:      {self.emotion_state.concern:.2%}")
        report.append(f"  - Confidence:   {self.emotion_state.confidence:.2%}")
        report.append("")
        report.append("Learning Metrics:")
        report.append(
            f"  - Learning Adjustment: {self.learning_system.get_learning_adjustment():.3f}"
        )
        report.append(
            f"  - Feedback Records: {len(self.learning_system.feedback_history)}"
        )
        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


# ============================================================================
# CLI INTERFACE
# ============================================================================


class BrioInterface:
    """Command-line interface for interacting with BRIM"""

    def __init__(self):
        self.Brio = BRIM()

    def print_welcome(self):
        """Print welcome message"""
        print("\n" + "=" * 70)
        print("Brio - Emotionally-Aware Intelligence System")
        print("=" * 70)
        print(
            "Welcome! I'm BRIM, an AI assistant with emotions and cultural awareness."
        )
        print("My prime directive: Never harm or conceal harm.")
        print("")
        print("Commands:")
        print("  - Type your question or message")
        print("  - 'status'  : See BRIM's emotional state")
        print("  - 'report'  : Generate detailed report")
        print("  - 'export'  : Export logs to JSON")
        print("  - 'feedback': Provide feedback on last response")
        print("  - 'proverb' : Get a Ugandan proverb")
        print("  - 'help'    : Show this menu")
        print("  - 'quit'    : Exit BRIM")
        print("=" * 70 + "\n")

    def run(self):
        """Main interactive loop"""
        self.print_welcome()

        while True:
            try:
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() == "quit":
                    print("\nBRIM: Thank you for the conversation. Goodbye!")
                    break

                elif user_input.lower() == "help":
                    self.print_welcome()

                elif user_input.lower() == "status":
                    status = self.brim.get_status()
                    print(f"\nBrio Status:")
                    for key, value in status.items():
                        print(f"  {key}: {value}")
                    print()

                elif user_input.lower() == "report":
                    print("\n" + self.brim.generate_report() + "\n")

                elif user_input.lower() == "export":
                    result = self.brim.export_logs()
                    print(f"\nBRIM: {result}\n")

                elif user_input.lower() == "proverb":
                    proverb = random.choice(UGANDAN_PROVERBS)
                    print(f"\nBRIM: {proverb}\n")

                elif user_input.lower().startswith("feedback:"):
                    feedback_text = user_input[9:].strip()
                    self.brim.provide_feedback(
                        len(self.brim.interaction_history) - 1, feedback_text
                    )
                    print(f"BRIM: Thank you for the feedback! This helps me learn.\n")

                else:
                    response = self.brim.interact(user_input)
                    print(f"\nBRIM: {response}\n")

            except KeyboardInterrupt:
                print("\n\nBRIM: Interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\nBRIM: An error occurred: {str(e)}\n")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    interface = BrioInterface()
    interface.run()


