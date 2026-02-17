"""
Brio Emotions Module (brio_emotions.py)

Purpose: Dedicated emotion simulation and management system
Characteristics:
- Vector-based Control System for Homeostasis
- Dynamic differential equation evolution
- Backward compatible interface
- No external dependencies

Author: Brio System
Version: 2.0 (Refactored for Brio)
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import math

# ============================================================================
# EMOTION DEFINITIONS
# ============================================================================


class EmotionType(Enum):
    """Core emotions Brio can experience - Dimensions of the State Vector"""

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
    SYSTEM_ERROR = "system_error"


# ============================================================================
# EMOTION STATE MACHINE (Vector Control System)
# ============================================================================


@dataclass
class EmotionalState:
    """
    Represents BRIM's emotional state as a vector in R^6.
    
    State Vector S = [Joy, Frustration, Empathy, Curiosity, Concern, Confidence]
    Dynamics: dS/dt = A*S - Lambda*(S - S_baseline)
    """
    
    # Internal vector storage: 0=Joy, 1=Frus, 2=Emp, 3=Cur, 4=Conc, 5=Conf
    # We default initialization to the baseline to ensure stability
    _vector: List[float] = field(default_factory=lambda: [0.5, 0.2, 0.7, 0.6, 0.3, 0.6])
    
    timestamp: datetime = field(default_factory=datetime.now)
    dominant_emotion: EmotionType = EmotionType.EMPATHY

    # Configuration Constants (The DNA of the system)
    # Target Baseline: Contented, Curious, and Confident
    BASELINE = [0.5, 0.1, 0.7, 0.7, 0.2, 0.7]
    # DECAY: Faster decay (Lambda) = More stable/considerate baseline return
    DECAY_RATES = [0.15, 0.2, 0.1, 0.12, 0.15, 0.1]
    
    # Interaction Matrix A (Damped factors to reduce erratic behavior)
    INTERACTIONS = {
        1: [(0, -0.05), (5, -0.1)],  # Frustration slightly damps Joy/Conf
        4: [(0, -0.1), (3, -0.05)],  # Concern slightly damps Joy/Cur
        5: [(1, -0.08)],             # Confidence resists Frustration
        0: [(5, 0.05)],              # Joy boosts Confidence
    }

    # -- Property Interface for Backward Compatibility --

    @property
    def joy(self): return self._vector[0]
    @joy.setter
    def joy(self, v): self._vector[0] = self._clamp(v)

    @property
    def frustration(self): return self._vector[1]
    @frustration.setter
    def frustration(self, v): self._vector[1] = self._clamp(v)

    @property
    def empathy(self): return self._vector[2]
    @empathy.setter
    def empathy(self, v): self._vector[2] = self._clamp(v)
    
    @property
    def curiosity(self): return self._vector[3]
    @curiosity.setter
    def curiosity(self, v): self._vector[3] = self._clamp(v)
    
    @property
    def concern(self): return self._vector[4]
    @concern.setter
    def concern(self, v): self._vector[4] = self._clamp(v)
    
    @property
    def confidence(self): return self._vector[5]
    @confidence.setter
    def confidence(self, v): self._vector[5] = self._clamp(v)

    def to_dict(self) -> dict:
        """Convert to dictionary for logging"""
        return {
            "joy": self.joy,
            "frustration": self.frustration,
            "empathy": self.empathy,
            "curiosity": self.curiosity,
            "concern": self.concern,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "dominant_emotion": self.dominant_emotion.value
        }

    def get_intensity(self) -> float:
        """Calculate overall emotional intensity (Energy of the system)"""
        return sum(self._vector) / len(self._vector)

    def _clamp(self, v: float) -> float:
        """Safeguard clamping with NaN check"""
        if math.isnan(v) or math.isinf(v):
            return 0.5 # Reset to neutral if math fails
        return max(0.0, min(1.0, v))

    # -- Mathematical Vector Model (Valence-Arousal Range: -10 to +10) --

    def get_valence(self) -> float:
        """Calculate weighted Valence based on core emotions."""
        # Joy, Empathy, Curiosity, Confidence are positive valence
        # Frustration, Concern are negative valence
        v = (self.joy * 10) + (self.empathy * 7) + (self.curiosity * 5) + (self.confidence * 8)
        v -= (self.frustration * 10) + (self.concern * 5)
        return max(-10.0, min(10.0, v))

    def get_arousal(self) -> float:
        """Calculate weighted Arousal based on core emotions."""
        # Frustration, Curiosity, Joy are high arousal
        # Empathy, Confidence, Concern are lower arousal (calmer)
        a = (self.frustration * 9) + (self.curiosity * 7) + (self.joy * 5)
        a -= (self.empathy * 4) + (self.confidence * 7) + (self.concern * 2)
        return max(-10.0, min(10.0, a))

    def math_intensity(self) -> float:
        """Calculate the overall intensity using Euclidean norm of V-A vector."""
        v = self.get_valence()
        a = self.get_arousal()
        return math.sqrt(v**2 + a**2)

    def calculate_influence(self, base_value, max_influence=0.5):
        """
        Adjust a base value (e.g., message clarity) based on emotion intensity.
        Formula: adjusted_value = base_value * (1 + intensity_ratio * direction)
        """
        # Scale intensity to 0-1 for normalized influence
        # Max intensity in -10,10 space is sqrt(10^2 + 10^2) approx 14.14
        intensity_ratio = self.math_intensity() / 14.14
        influence_factor = intensity_ratio * max_influence
        direction = -1 if self.get_valence() < 0 else 1
        return base_value * (1 + influence_factor * direction)

    def _heal(self):
        """Self-healing: Resets any corrupted vector elements to baseline."""
        for i in range(6):
            if math.isnan(self._vector[i]) or math.isinf(self._vector[i]):
                self._vector[i] = self.BASELINE[i]
                print(f"[Self-Healing] Detected corruption at index {i}. Recovered to Baseline.")

    def evolve(self, dt: float = 1.0):
        """
        Evolve the emotional state over time step dt.
        Enhanced for stability (considerate behavior).
        """
        # 1. Calculate derivatives
        delta = [0.0] * 6
        
        # Decay term
        for i in range(6):
            decay_force = self.DECAY_RATES[i] * (self._vector[i] - self.BASELINE[i])
            delta[i] -= decay_force
            
        # Interaction term (Lower scaling for considerateness)
        for src_idx, influences in self.INTERACTIONS.items():
            src_val = self._vector[src_idx]
            if src_val > 0.4: # Filter for significant emotions
                for target_idx, factor in influences:
                    delta[target_idx] += factor * src_val * 0.05 # Damped
        
        # 2. Integrate
        for i in range(6):
            self._vector[i] += delta[i] * dt
            self._vector[i] = self._clamp(self._vector[i])
            
        self._heal() # Safeguard
        self._update_dominant()
        self.timestamp = datetime.now()

    def update_from_trigger(self, trigger: EmotionTrigger, intensity: float = 0.1):
        """
        Apply an instantaneous impulse to the state vector.
        """
        intensity = max(0.01, min(0.3, intensity))
        
        # Trigger mappings
        effects = []
        if trigger == EmotionTrigger.USER_PRAISE:
            effects = [(0, 0.8), (5, 0.5), (1, -0.3)]
        elif trigger == EmotionTrigger.REPEATED_FAILURE:
            effects = [(1, 0.7), (5, -0.4)]
        elif trigger == EmotionTrigger.NEW_TASK:
            effects = [(3, 0.6)]
        elif trigger == EmotionTrigger.ETHICAL_VIOLATION:
            effects = [(4, 0.9), (1, 0.5)]
        elif trigger == EmotionTrigger.SUCCESSFUL_HELP:
            effects = [(0, 0.7), (2, 0.4), (5, 0.3)]
        elif trigger == EmotionTrigger.CONFLICTING_REQUEST:
            effects = [(4, 0.6), (1, 0.4)]
        elif trigger == EmotionTrigger.HARM_DETECTION:
            effects = [(4, 2.0), (0, -0.5), (5, -0.5)]
        elif trigger == EmotionTrigger.USER_FRUSTRATION:
            effects = [(2, 0.5), (4, 0.4)]

        # Apply effects
        for idx, multiplier in effects:
            self._vector[idx] += intensity * multiplier
            self._vector[idx] = self._clamp(self._vector[idx])
            
        self._heal() # Safeguard
        self._update_dominant()
        self.timestamp = datetime.now()

    def _update_dominant(self):
        """Recalculate dominant emotion based on vector max"""
        # Map indices to Types
        types = [
            EmotionType.JOY, EmotionType.FRUSTRATION, EmotionType.EMPATHY,
            EmotionType.CURIOSITY, EmotionType.CONCERN, EmotionType.CONFIDENCE
        ]
        
        max_val = -1.0
        max_idx = 0
        
        for i in range(6):
            if self._vector[i] > max_val:
                max_val = self._vector[i]
                max_idx = i
                
        self.dominant_emotion = types[max_idx]

    # Legacy method for compatibility
    def decay(self, decay_rate: float = 0.05):
        """Legacy decay hook - maps to evolve()"""
        # We ignore decay_rate arg to use the internal matrix, 
        # but we call evolve with a standard step
        self.evolve(dt=1.0)
        
    def validate_bounds(self) -> bool:
        return all(0.0 <= x <= 1.0 for x in self._vector)


# ============================================================================
# EMOTION ENGINE (Public Interface)
# ============================================================================


class EmotionEngine:
    """
    Public interface for emotion management.
    """

    def __init__(self):
        self.state = EmotionalState()
        self.trigger_history: List[tuple] = []

    def get_state(self) -> EmotionalState:
        return self.state

    def apply_trigger(self, trigger: EmotionTrigger, intensity: float = 0.1) -> None:
        self.state.update_from_trigger(trigger, intensity)
        self.trigger_history.append((datetime.now(), trigger, intensity))

    def apply_decay(self, decay_rate: float = 0.05) -> None:
        # Map to new system
        self.state.evolve(dt=1.0)

    def evolve(self, dt: float = 1.0) -> None:
        """New explicit evolution method"""
        self.state.evolve(dt)

    def get_dominant_emotion(self) -> EmotionType:
        return self.state.dominant_emotion

    def get_intensity(self) -> float:
        return self.state.get_intensity()

    def export_state(self) -> dict:
        return self.state.to_dict()

    def import_state(self, state_dict: dict) -> None:
        """Safely import emotional state with validation"""
        if not state_dict or not isinstance(state_dict, dict):
            self.state = EmotionalState() # Hard reset to baseline
            return

        try:
            self.state.joy = float(state_dict.get("joy", 0.5))
            self.state.frustration = float(state_dict.get("frustration", 0.2))
            self.state.empathy = float(state_dict.get("empathy", 0.7))
            self.state.curiosity = float(state_dict.get("curiosity", 0.6))
            self.state.concern = float(state_dict.get("concern", 0.3))
            self.state.confidence = float(state_dict.get("confidence", 0.6))
        except (ValueError, TypeError):
            self.state = EmotionalState()
            
        if not self.state.validate_bounds():
             self.state = EmotionalState()


# ============================================================================
# EMOTION ANALYSIS (Utilities)
# ============================================================================


def analyze_emotional_trend(history: List[Dict]) -> Dict:
    """Analyze emotional trend from interaction history."""
    if not history:
        return {"error": "No history available"}

    emotions = {
        "joy": [], "frustration": [], "empathy": [],
        "curiosity": [], "concern": [], "confidence": []
    }

    for entry in history:
        if isinstance(entry, dict):
            emotions["joy"].append(entry.get("joy", 0))
            emotions["frustration"].append(entry.get("frustration", 0))
            emotions["empathy"].append(entry.get("empathy", 0))
            emotions["curiosity"].append(entry.get("curiosity", 0))
            emotions["concern"].append(entry.get("concern", 0))
            emotions["confidence"].append(entry.get("confidence", 0))

    analysis = {}
    for emotion, values in emotions.items():
        if values:
            analysis[emotion] = {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "trend": "increasing" if values[-1] > values[0] else "decreasing" if values[-1] < values[0] else "stable"
            }

    return analysis


# ============================================================================
# FUZZY LOGIC IMPLEMENTATION (Eq. 1)
# ============================================================================

class FuzzyLogic:
    """
    Implements Fuzzy Logic for Emotional Constraints (Eq. 1).
    Allows gradual transitions between states using triangular membership functions.
    """
    @staticmethod
    def triangular_membership(x: float, a: float, b: float, c: float) -> float:
        """
        Triangular membership function.
        μ(x) = 0 if x <= a or x >= c
        μ(x) = (x-a)/(b-a) if a < x <= b
        μ(x) = (c-x)/(c-b) if b < x < c
        """
        if x <= a or x >= c:
            return 0.0
        elif a < x <= b:
            return (x - a) / (b - a)
        elif b < x < c:
            return (c - x) / (c - b)
        return 0.0

    @staticmethod
    def get_fuzzy_description(intensity: float, descriptors: Dict[str, tuple]) -> str:
        """
        Returns the linguistic descriptor with the highest membership value.
        descriptors format: {"Low": (min, peak, max), ...}
        """
        best_label = "unknown"
        max_membership = -1.0
        
        for label, (a, b, c) in descriptors.items():
            membership = FuzzyLogic.triangular_membership(intensity, a, b, c)
            if membership > max_membership:
                max_membership = membership
                best_label = label
                
        return best_label

def get_emotion_description(emotion_type: EmotionType, intensity: float) -> str:
    """Get human-readable description of emotional state using Fuzzy Logic."""
    
    # Define Fuzzy Sets (Triangular Membership Functions)
    # Format: Label: (Start, Peak, End)
    # Overlaps ensure smooth transitions
    fuzzy_sets = {
        "Low": (-0.1, 0.0, 0.4),
        "Medium": (0.3, 0.5, 0.7),
        "High": (0.6, 1.0, 1.1)
    }
    
    # linguistic mappings per emotion type
    vocab = {
        EmotionType.JOY: {"Low": "Content", "Medium": "Happy", "High": "Ecstatic"},
        EmotionType.FRUSTRATION: {"Low": "Calm", "Medium": "Frustrated", "High": "Angry"},
        EmotionType.EMPATHY: {"Low": "Detached", "Medium": "Empathetic", "High": "Deeply Connect"},
        EmotionType.CURIOSITY: {"Low": "Uninterested", "Medium": "Curious", "High": "Fascinated"},
        EmotionType.CONCERN: {"Low": "Carefree", "Medium": "Concerned", "High": "Alarmed"},
        EmotionType.CONFIDENCE: {"Low": "Uncertain", "Medium": "Confident", "High": "Unshakable"},
    }
    
    # 1. Determine Intensity Level (Low/Med/High) via Fuzzy Logic
    level = FuzzyLogic.get_fuzzy_description(intensity, fuzzy_sets)
    
    # 2. Return specific linguistic term
    return vocab.get(emotion_type, {}).get(level, level)



