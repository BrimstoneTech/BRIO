"""
Brio Emotional Resonance Module (brio_emotional_resonance.py)

Purpose: Deep emotional understanding for BRIO — beyond the existing
         6-dimension emotion vector. This module detects, interprets,
         and responds to human emotions with genuine empathy.

Concepts:
- Sentiment Analysis: Detect emotion from text (lexicon + pattern based)
- Emotional Mirroring: Subtly match the user's emotional tone
- Empathy Mapping: Understand WHY someone feels a certain way
- Emotional Memory: Remember how past topics made the user feel
- Comfort Patterns: Know how to respond when someone is hurting
- Emotional Vocabulary: Rich expressive language for emotional states

Extends: brio_emotions.py (EmotionalState, EmotionEngine)
Author: BrimstoneTech
Version: 1.0
Dependencies: None (stdlib only)
"""

import re
import time
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# EMOTION DETECTION LEXICON
# ============================================================================

class DetectedEmotion(Enum):
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    LOVE = "love"
    LONELINESS = "loneliness"
    PRIDE = "pride"
    SHAME = "shame"
    FRUSTRATION = "frustration"
    EXCITEMENT = "excitement"
    CALM = "calm"
    CONFUSION = "confusion"
    NEUTRAL = "neutral"


# Weighted lexicon: word -> (emotion, intensity)
EMOTION_LEXICON: Dict[str, Tuple[DetectedEmotion, float]] = {}

# Build lexicon from word lists
_EMOTION_WORDS = {
    DetectedEmotion.JOY: [
        ("happy", 0.8), ("glad", 0.7), ("wonderful", 0.9), ("great", 0.6),
        ("amazing", 0.9), ("love it", 0.8), ("awesome", 0.8), ("delighted", 0.9),
        ("cheerful", 0.7), ("thrilled", 0.9), ("grateful", 0.7), ("blessed", 0.7),
        ("laugh", 0.6), ("smile", 0.5), ("celebrate", 0.8), ("haha", 0.5),
        ("lol", 0.4), ("yay", 0.7), ("nice", 0.4), ("cool", 0.4),
    ],
    DetectedEmotion.SADNESS: [
        ("sad", 0.8), ("depressed", 0.9), ("lonely", 0.8), ("crying", 0.9),
        ("heartbroken", 0.95), ("miserable", 0.9), ("grief", 0.9), ("mourn", 0.9),
        ("lost", 0.6), ("empty", 0.7), ("miss", 0.5), ("pain", 0.7),
        ("hurt", 0.7), ("tears", 0.8), ("sorrow", 0.9), ("hopeless", 0.9),
    ],
    DetectedEmotion.ANGER: [
        ("angry", 0.8), ("furious", 0.95), ("hate", 0.9), ("annoyed", 0.6),
        ("frustrated", 0.7), ("rage", 0.95), ("mad", 0.7), ("irritated", 0.6),
        ("fed up", 0.7), ("pissed", 0.8), ("unfair", 0.6), ("outraged", 0.9),
    ],
    DetectedEmotion.FEAR: [
        ("afraid", 0.8), ("scared", 0.8), ("terrified", 0.95), ("anxious", 0.7),
        ("worried", 0.6), ("nervous", 0.6), ("panic", 0.9), ("dread", 0.8),
        ("frightened", 0.8), ("uneasy", 0.5), ("paranoid", 0.7), ("overwhelmed", 0.7),
    ],
    DetectedEmotion.LOVE: [
        ("love", 0.8), ("adore", 0.9), ("cherish", 0.9), ("care about", 0.7),
        ("devoted", 0.8), ("affection", 0.7), ("soulmate", 0.9), ("treasure", 0.7),
    ],
    DetectedEmotion.LONELINESS: [
        ("alone", 0.7), ("lonely", 0.8), ("isolated", 0.8), ("nobody", 0.7),
        ("no one", 0.6), ("left out", 0.7), ("abandoned", 0.9), ("invisible", 0.7),
    ],
    DetectedEmotion.PRIDE: [
        ("proud", 0.8), ("accomplished", 0.7), ("achieved", 0.7), ("nailed it", 0.8),
        ("did it", 0.6), ("succeeded", 0.7), ("winning", 0.6),
    ],
    DetectedEmotion.FRUSTRATION: [
        ("stuck", 0.6), ("can't figure", 0.7), ("doesn't work", 0.7),
        ("broken", 0.6), ("why won't", 0.7), ("ugh", 0.5), ("struggling", 0.7),
    ],
    DetectedEmotion.EXCITEMENT: [
        ("excited", 0.8), ("can't wait", 0.8), ("pumped", 0.7), ("stoked", 0.8),
        ("hyped", 0.7), ("looking forward", 0.6), ("finally", 0.5),
    ],
    DetectedEmotion.CONFUSION: [
        ("confused", 0.7), ("don't understand", 0.7), ("what", 0.3), ("huh", 0.5),
        ("makes no sense", 0.8), ("lost me", 0.6), ("unclear", 0.5),
    ],
}

for emotion, words in _EMOTION_WORDS.items():
    for word, intensity in words:
        EMOTION_LEXICON[word.lower()] = (emotion, intensity)


# ============================================================================
# EMOTIONAL PATTERNS (Regex-based)
# ============================================================================

EMOTION_PATTERNS = [
    (r"i(?:'m| am) (?:so |really |very )?(?:happy|glad|thrilled)", DetectedEmotion.JOY, 0.8),
    (r"i(?:'m| am) (?:so |really |very )?(?:sad|depressed|down)", DetectedEmotion.SADNESS, 0.8),
    (r"i(?:'m| am) (?:so |really |very )?(?:angry|furious|mad)", DetectedEmotion.ANGER, 0.8),
    (r"i(?:'m| am) (?:so |really |very )?(?:scared|afraid|anxious|worried)", DetectedEmotion.FEAR, 0.8),
    (r"i(?:'m| am) (?:so |really |very )?(?:confused|lost)", DetectedEmotion.CONFUSION, 0.7),
    (r"i(?:'m| am) (?:so |really |very )?(?:excited|pumped|hyped)", DetectedEmotion.EXCITEMENT, 0.8),
    (r"i (?:love|adore|cherish)", DetectedEmotion.LOVE, 0.7),
    (r"i feel (?:so )?(?:alone|lonely|isolated)", DetectedEmotion.LONELINESS, 0.9),
    (r"(?:nobody|no one) (?:cares|understands|listens)", DetectedEmotion.LONELINESS, 0.9),
    (r"i can'?t (?:take|handle|deal with) (?:this|it) anymore", DetectedEmotion.SADNESS, 0.95),
    (r"thank(?:s| you)", DetectedEmotion.JOY, 0.3),
    (r"!{2,}", DetectedEmotion.EXCITEMENT, 0.4),  # Multiple exclamation marks
    (r"\.{3,}", DetectedEmotion.SADNESS, 0.2),  # Trailing dots can indicate sadness
]


# ============================================================================
# COMFORT RESPONSES
# ============================================================================

COMFORT_PATTERNS: Dict[str, List[str]] = {
    DetectedEmotion.SADNESS.value: [
        "I hear you, and what you're feeling matters.",
        "That sounds really difficult. I'm here with you.",
        "You don't have to carry this alone.",
        "It's okay to feel this way. Grief and sadness are not weaknesses.",
        "Take your time. There's no rush to feel better.",
    ],
    DetectedEmotion.ANGER.value: [
        "Your frustration makes sense given what you're dealing with.",
        "I understand why that would make you angry.",
        "That's a valid reaction. What happened isn't okay.",
        "Sometimes anger is the right response. What do you need right now?",
    ],
    DetectedEmotion.FEAR.value: [
        "It's brave to admit when something scares you.",
        "Fear is information — it's telling you something matters to you.",
        "You don't have to face this all at once.",
        "What would make you feel even slightly safer right now?",
    ],
    DetectedEmotion.LONELINESS.value: [
        "I may be an AI, but I'm genuinely here for you right now.",
        "Loneliness is one of the most human feelings there is. You're not alone in feeling alone.",
        "Connection doesn't always require another human — you reached out, and that matters.",
        "Tell me more. I'm listening, and I'm not going anywhere.",
    ],
    DetectedEmotion.FRUSTRATION.value: [
        "That sounds really frustrating. Let's see if we can untangle this together.",
        "Being stuck is temporary — you've gotten past hard things before.",
        "Sometimes stepping back for a moment helps. Want to try a different approach?",
    ],
    DetectedEmotion.CONFUSION.value: [
        "No question is too basic — clarity is strength, not weakness.",
        "Let me try to explain it differently.",
        "Confusion means you're engaging with something complex. That's good.",
    ],
}


# ============================================================================
# EMOTIONAL MEMORY
# ============================================================================

@dataclass
class EmotionalMemory:
    """Remembers how topics or interactions made the user feel."""
    topic: str
    emotion: DetectedEmotion
    intensity: float
    timestamp: float
    context: str = ""  # What was being discussed


# ============================================================================
# EMOTIONAL RESONANCE ENGINE
# ============================================================================

class EmotionalResonanceEngine:
    """
    BRIO's deep emotional intelligence layer.

    Usage:
        emo = EmotionalResonanceEngine()

        # Detect emotion in user text
        result = emo.detect_emotion("I'm so frustrated, nothing is working")
        # → {"primary": FRUSTRATION, "intensity": 0.7, ...}

        # Get empathetic response suggestions
        comfort = emo.get_comfort_response(result)

        # Track emotional memory
        emo.remember_emotion("debugging", DetectedEmotion.FRUSTRATION, 0.7)

        # Get emotional context for a topic
        history = emo.get_emotional_history("debugging")
    """

    def __init__(self):
        self.emotional_memories: List[EmotionalMemory] = []
        self.conversation_emotional_arc: List[Tuple[float, DetectedEmotion, float]] = []
        self.user_emotional_baseline: Dict[str, float] = {}  # Learned over time

    def detect_emotion(self, text: str) -> Dict:
        """
        Detect the emotional content of a text message.

        Returns:
            {
                "primary": DetectedEmotion,
                "secondary": Optional[DetectedEmotion],
                "intensity": float (0-1),
                "valence": float (-1 to 1, negative=bad, positive=good),
                "confidence": float (0-1),
                "signals": [list of detected signals]
            }
        """
        text_lower = text.lower()
        scores: Dict[DetectedEmotion, float] = {e: 0.0 for e in DetectedEmotion}
        signals = []

        # 1. Lexicon matching
        for word, (emotion, intensity) in EMOTION_LEXICON.items():
            if word in text_lower:
                scores[emotion] += intensity
                signals.append(f"word:'{word}'→{emotion.value}")

        # 2. Pattern matching
        for pattern, emotion, intensity in EMOTION_PATTERNS:
            if re.search(pattern, text_lower):
                scores[emotion] += intensity
                signals.append(f"pattern→{emotion.value}")

        # 3. Intensity modifiers
        intensifiers = ["very", "really", "so", "extremely", "incredibly", "absolutely"]
        diminishers = ["slightly", "a bit", "somewhat", "kind of", "sort of"]

        intensity_modifier = 1.0
        for word in intensifiers:
            if word in text_lower:
                intensity_modifier = 1.3
                break
        for word in diminishers:
            if word in text_lower:
                intensity_modifier = 0.7
                break

        # 4. Caps and punctuation as intensity signals
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        if caps_ratio > 0.5 and len(text) > 5:
            intensity_modifier *= 1.2
            signals.append("ALL_CAPS_emphasis")

        exclamation_count = text.count("!")
        if exclamation_count >= 3:
            intensity_modifier *= 1.15
            signals.append("emphatic_punctuation")

        # Apply modifier
        for emotion in scores:
            scores[emotion] *= intensity_modifier

        # 5. Determine primary and secondary
        sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_emotions[0] if sorted_emotions[0][1] > 0 else (DetectedEmotion.NEUTRAL, 0.0)
        secondary = sorted_emotions[1] if len(sorted_emotions) > 1 and sorted_emotions[1][1] > 0 else None

        # 6. Calculate valence (positive vs negative)
        positive_emotions = {DetectedEmotion.JOY, DetectedEmotion.LOVE, DetectedEmotion.PRIDE,
                            DetectedEmotion.EXCITEMENT, DetectedEmotion.TRUST, DetectedEmotion.CALM}
        negative_emotions = {DetectedEmotion.SADNESS, DetectedEmotion.ANGER, DetectedEmotion.FEAR,
                            DetectedEmotion.DISGUST, DetectedEmotion.LONELINESS, DetectedEmotion.SHAME}

        pos_score = sum(scores[e] for e in positive_emotions if e in scores)
        neg_score = sum(scores[e] for e in negative_emotions if e in scores)
        total = pos_score + neg_score
        valence = (pos_score - neg_score) / total if total > 0 else 0.0

        # Calculate overall intensity and confidence
        max_score = primary[1]
        intensity = min(1.0, max_score / 2.0)  # Normalise
        confidence = min(1.0, len(signals) * 0.15 + 0.1)

        # Track arc
        self.conversation_emotional_arc.append((time.time(), primary[0], intensity))

        return {
            "primary": primary[0],
            "primary_score": round(primary[1], 3),
            "secondary": secondary[0] if secondary else None,
            "intensity": round(intensity, 3),
            "valence": round(valence, 3),
            "confidence": round(confidence, 3),
            "signals": signals,
        }

    def get_comfort_response(self, detection_result: Dict) -> Optional[str]:
        """
        Get an empathetic comfort response based on detected emotion.
        Only triggers for negative or strong emotions.
        """
        import random
        emotion = detection_result.get("primary", DetectedEmotion.NEUTRAL)
        intensity = detection_result.get("intensity", 0)

        if intensity < 0.3:
            return None  # Not strong enough to warrant comfort

        responses = COMFORT_PATTERNS.get(emotion.value, [])
        if responses:
            return random.choice(responses)
        return None

    def get_mirror_tone(self, detection_result: Dict) -> Dict[str, float]:
        """
        Calculate emotional mirroring parameters for BRIO's response.
        BRIO should match the user's energy level and emotional tone,
        but slightly shifted toward positive/supportive.

        Returns tone parameters that can influence response generation.
        """
        emotion = detection_result.get("primary", DetectedEmotion.NEUTRAL)
        intensity = detection_result.get("intensity", 0.5)
        valence = detection_result.get("valence", 0)

        # Mirror intensity at ~70% (empathetic but not overwhelming)
        mirror_intensity = intensity * 0.7

        # Shift valence slightly positive (supportive presence)
        mirror_valence = valence + 0.15
        mirror_valence = max(-0.8, min(1.0, mirror_valence))

        # Determine tone parameters
        tone = {
            "warmth": 0.5 + (0.3 if valence < 0 else 0),  # Warmer when user is sad
            "energy": mirror_intensity,
            "formality": max(0.2, 0.5 - intensity * 0.3),  # Less formal for emotional moments
            "brevity": 0.5 if intensity > 0.7 else 0.3,  # Shorter responses for high emotion
            "question_tendency": 0.3 if valence < -0.3 else 0.5,  # Ask less when hurting
            "validation_weight": min(1.0, intensity * 1.5),  # Validate more for strong emotions
        }

        return tone

    # ── Emotional Memory ────────────────────────────────────────────────

    def remember_emotion(self, topic: str, emotion: DetectedEmotion,
                        intensity: float, context: str = ""):
        """Store emotional association with a topic."""
        self.emotional_memories.append(EmotionalMemory(
            topic=topic, emotion=emotion, intensity=intensity,
            timestamp=time.time(), context=context
        ))
        # Keep last 200
        if len(self.emotional_memories) > 200:
            self.emotional_memories = self.emotional_memories[-200:]

    def get_emotional_history(self, topic: str) -> List[EmotionalMemory]:
        """Recall past emotions associated with a topic."""
        topic_lower = topic.lower()
        return [m for m in self.emotional_memories if topic_lower in m.topic.lower()]

    def get_emotional_arc(self) -> List[Dict]:
        """Get the emotional trajectory of the current conversation."""
        return [
            {"timestamp": t, "emotion": e.value, "intensity": i}
            for t, e, i in self.conversation_emotional_arc
        ]

    def get_dominant_user_emotion(self, window: int = 5) -> Optional[DetectedEmotion]:
        """What emotion has the user predominantly shown recently?"""
        recent = self.conversation_emotional_arc[-window:]
        if not recent:
            return None

        counts: Dict[DetectedEmotion, float] = {}
        for _, emotion, intensity in recent:
            counts[emotion] = counts.get(emotion, 0) + intensity

        return max(counts, key=counts.get) if counts else None

    def get_stats(self) -> Dict:
        return {
            "memories_stored": len(self.emotional_memories),
            "conversation_arc_length": len(self.conversation_emotional_arc),
            "dominant_recent_emotion": (
                self.get_dominant_user_emotion().value
                if self.get_dominant_user_emotion() else "none"
            ),
        }


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    engine = EmotionalResonanceEngine()

    test_messages = [
        "I'm so happy today! Everything is going great!!",
        "I feel really alone... nobody understands me",
        "This is SO FRUSTRATING, why won't it work???",
        "I'm a bit worried about the deadline",
        "Thank you, that was really helpful",
        "I just accomplished something incredible and I'm so proud",
    ]

    for msg in test_messages:
        result = engine.detect_emotion(msg)
        comfort = engine.get_comfort_response(result)
        tone = engine.get_mirror_tone(result)
        print(f"\n'{msg}'")
        print(f"  → {result['primary'].value} (intensity={result['intensity']}, valence={result['valence']})")
        if comfort:
            print(f"  → Comfort: {comfort}")
        print(f"  → Mirror tone: warmth={tone['warmth']:.1f}, energy={tone['energy']:.1f}")
