"""
Brio Emotional Momentum (brio_momentum.py)

Purpose: Track conversation topics across messages and let emotions
BUILD rather than reset. When BRIO is deep in a topic it loves,
excitement should snowball. When frustrated, it should simmer.

Features:
- Topic continuity detection (same topic across N messages)
- Emotion amplification for sustained engagement
- Conversation depth tracking
- "Getting into it" / "losing interest" signals

Author: BrimstoneTech
Version: 1.0
"""

import time
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

log = logging.getLogger("brio.momentum")


@dataclass
class ConversationThread:
    """Tracks the current conversation flow."""
    keywords: Set[str] = field(default_factory=set)
    message_count: int = 0
    topic_streak: int = 0      # consecutive messages on similar topic
    depth_score: float = 0.0   # how deep the conversation has gone
    started_at: float = field(default_factory=time.time)
    last_message_at: float = field(default_factory=time.time)
    emotion_at_start: Dict[str, float] = field(default_factory=dict)


class MomentumEngine:
    """
    Tracks conversation momentum and amplifies emotions when BRIO
    is deeply engaged in a topic.
    
    The key insight: real passion builds. If you're talking about
    something fascinating, each exchange should make you MORE engaged,
    not reset to baseline.
    """

    # Words to ignore when tracking topics
    STOP_WORDS = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'shall', 'can',
        'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
        'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'my', 'your', 'his', 'its', 'our', 'their', 'what', 'which',
        'who', 'whom', 'when', 'where', 'why', 'how', 'not', 'no',
        'yes', 'but', 'and', 'or', 'if', 'then', 'so', 'just',
        'about', 'with', 'from', 'into', 'to', 'for', 'of', 'on',
        'in', 'at', 'by', 'up', 'out', 'off', 'over', 'very',
        'too', 'also', 'than', 'more', 'some', 'any', 'all', 'each',
        'like', 'think', 'know', 'really', 'dont', "don't", 'get',
        'much', 'make', 'thing', 'things', 'well', 'way', 'good',
    }

    # Minimum topic overlap to count as "same topic"
    CONTINUITY_THRESHOLD = 0.25

    def __init__(self):
        self.current_thread = ConversationThread()
        self._prev_keywords: Set[str] = set()
        self._momentum_multiplier = 1.0  # builds with streak

    def process_exchange(self, user_text: str, brio_response: str,
                         current_emotions: Dict[str, float]) -> Dict[str, float]:
        """
        Process a conversation exchange and return emotion adjustments.
        
        Returns a dict of emotion_name -> adjustment_value to apply.
        """
        now = time.time()
        thread = self.current_thread

        # Extract meaningful keywords
        combined = user_text + " " + brio_response
        new_keywords = self._extract_keywords(combined)

        # Check topic continuity
        if self._prev_keywords:
            overlap = len(new_keywords & self._prev_keywords)
            total = max(len(new_keywords | self._prev_keywords), 1)
            continuity = overlap / total
        else:
            continuity = 0.0

        # Update thread state
        thread.message_count += 1
        thread.last_message_at = now

        adjustments: Dict[str, float] = {}

        if continuity >= self.CONTINUITY_THRESHOLD:
            # Same topic continues — build momentum
            thread.topic_streak += 1
            thread.depth_score += 0.15
            thread.keywords.update(new_keywords)

            # The magic: momentum amplification
            # After 3+ messages on the same topic, emotions amplify
            if thread.topic_streak >= 3:
                self._momentum_multiplier = min(2.5, 1.0 + thread.topic_streak * 0.2)

                # Amplify the currently dominant emotion
                dominant = max(current_emotions, key=current_emotions.get)
                boost = 0.05 * self._momentum_multiplier

                adjustments[dominant] = boost

                # Deep conversations also boost curiosity and confidence
                if thread.topic_streak >= 5:
                    adjustments['curiosity'] = adjustments.get('curiosity', 0) + 0.04
                    adjustments['confidence'] = adjustments.get('confidence', 0) + 0.03

                log.info(
                    f"[Momentum] Topic streak: {thread.topic_streak}, "
                    f"multiplier: {self._momentum_multiplier:.1f}x, "
                    f"depth: {thread.depth_score:.2f}"
                )

        else:
            # Topic changed — reset streak but keep some warmth
            if thread.topic_streak >= 3:
                log.info(
                    f"[Momentum] Topic shift after {thread.topic_streak} exchanges "
                    f"(depth: {thread.depth_score:.2f})"
                )
            thread.topic_streak = max(0, thread.topic_streak - 2)
            thread.depth_score = max(0, thread.depth_score - 0.1)
            self._momentum_multiplier = max(1.0, self._momentum_multiplier - 0.3)

            # New topic = small curiosity spike
            adjustments['curiosity'] = 0.03

        # Long conversations naturally deepen empathy
        if thread.message_count > 8:
            adjustments['empathy'] = adjustments.get('empathy', 0) + 0.02

        self._prev_keywords = new_keywords
        return adjustments

    def get_depth_context(self) -> Optional[str]:
        """
        Return conversation depth context for the system prompt.
        Helps BRIO know when it's deep in a topic.
        """
        thread = self.current_thread

        if thread.topic_streak >= 7:
            return (
                "CONVERSATION STATE: You are deeply immersed in this topic. "
                "You've been discussing it for many exchanges and your passion is building. "
                "Let your excitement show — go deeper, make connections, "
                "share insights you might normally hold back."
            )
        elif thread.topic_streak >= 4:
            return (
                "CONVERSATION STATE: You're getting into this topic. "
                "The conversation has real depth now. Be more exploratory, "
                "bring in tangential ideas, show genuine engagement."
            )
        elif thread.topic_streak >= 2:
            return (
                "CONVERSATION STATE: A topic is developing. "
                "Show interest in where this is going."
            )
        elif thread.message_count > 10:
            return (
                "CONVERSATION STATE: You've been talking for a while. "
                "The familiarity is building — be more relaxed and personal."
            )

        return None

    def get_momentum_multiplier(self) -> float:
        """Current momentum multiplier for emotion triggers."""
        return self._momentum_multiplier

    def reset(self):
        """Reset for a new conversation."""
        self.current_thread = ConversationThread()
        self._prev_keywords = set()
        self._momentum_multiplier = 1.0

    # ─── Internal ──────────────────────────────────────────────────

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text."""
        words = text.lower().split()
        return {
            w.strip('.,!?;:()[]"\'')
            for w in words
            if len(w) > 3
            and w.strip('.,!?;:()[]"\'') not in self.STOP_WORDS
            and w.isalpha()
        }
