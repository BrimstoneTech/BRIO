"""
Brio Formatter Module (brio_formatter.py)

Purpose: Gives BRIO structured, organized, and distinctive replies.
No more wall-of-text responses. BRIO speaks with clarity and style.

Features:
- Structured response sections (thought, answer, sources, reflection)
- Emotional tone markers based on current emotional state
- Learning progress indicators in responses
- Contextual formatting (casual chat vs. teaching vs. research report)
- Personality-consistent voice across all response types

Author: BrimstoneTech
Version: 1.0
"""

import random
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# RESPONSE TYPES
# ============================================================================

class ResponseMode(Enum):
    """How BRIO should format its response."""
    CASUAL = "casual"          # Normal conversation
    TEACHING = "teaching"      # Explaining something it learned
    RESEARCH = "research"      # Sharing search/learning results
    REFLECTION = "reflection"  # Philosophical or values-driven
    GREETING = "greeting"      # Hello/welcome messages
    STATUS = "status"          # Progress/milestone reports
    ERROR = "error"            # When something went wrong
    CURIOUS = "curious"        # When BRIO is exploring/wondering


# ============================================================================
# SECTION BUILDERS
# ============================================================================

@dataclass
class ResponseSection:
    """A section of a structured response."""
    icon: str
    title: str
    content: str
    priority: int = 0  # Higher = shown first


class BrioFormatter:
    """
    Formats BRIO's responses with structure, personality, and clarity.
    
    Every response has:
    - A clear structure (sections, not walls of text)
    - An emotional tone matching BRIO's current state
    - Personality markers that make BRIO feel alive
    - Optional learning/progress indicators
    """

    def __init__(self):
        self._response_count = 0

    # ========================================================================
    # MAIN FORMATTING
    # ========================================================================

    def format_response(
        self,
        content: str,
        mode: ResponseMode = ResponseMode.CASUAL,
        emotion_state: Optional[dict] = None,
        sections: Optional[List[ResponseSection]] = None,
        sources: Optional[List[str]] = None,
        learning_note: Optional[str] = None,
        milestone_update: Optional[str] = None,
        reflection: Optional[str] = None,
        generation_info: Optional[dict] = None,
    ) -> str:
        """
        Format a complete BRIO response.
        
        Args:
            content: The main response text
            mode: Response type for formatting style
            emotion_state: Current emotions (from brio_emotions)
            sections: Additional structured sections
            sources: URLs or references used
            learning_note: What BRIO learned from this interaction
            milestone_update: Any milestone just completed
            reflection: A values-based reflection to include
            generation_info: Current generation/lifecycle info
        """
        self._response_count += 1
        parts = []
        
        # Generation badge (if available)
        if generation_info:
            gen = generation_info.get("generation", 1)
            name = generation_info.get("name", "")
            parts.append(f"`Gen {gen} · {name}`")
            parts.append("")

        # Emotional tone prefix
        if emotion_state:
            tone = self._get_tone_prefix(emotion_state, mode)
            if tone:
                parts.append(tone)

        # Main content with mode-specific formatting
        formatted_content = self._format_by_mode(content, mode)
        parts.append(formatted_content)

        # Additional sections
        if sections:
            sections.sort(key=lambda s: s.priority, reverse=True)
            for section in sections:
                parts.append("")
                parts.append(f"{section.icon} **{section.title}**")
                parts.append(section.content)

        # Sources
        if sources:
            parts.append("")
            parts.append("📎 **Sources:**")
            for i, src in enumerate(sources, 1):
                parts.append(f"  {i}. {src}")

        # Learning note
        if learning_note:
            parts.append("")
            parts.append(f"💡 *{learning_note}*")

        # Milestone update
        if milestone_update:
            parts.append("")
            parts.append(f"⭐ **Milestone unlocked:** {milestone_update}")

        # Reflection
        if reflection:
            parts.append("")
            parts.append(f"💭 _{reflection}_")

        return "\n".join(parts)

    # ========================================================================
    # MODE-SPECIFIC FORMATTING
    # ========================================================================

    def _format_by_mode(self, content: str, mode: ResponseMode) -> str:
        """Apply mode-specific formatting to content."""
        
        if mode == ResponseMode.CASUAL:
            return content
        
        elif mode == ResponseMode.TEACHING:
            return self._format_teaching(content)
        
        elif mode == ResponseMode.RESEARCH:
            return self._format_research(content)
        
        elif mode == ResponseMode.REFLECTION:
            return self._format_reflection(content)
        
        elif mode == ResponseMode.GREETING:
            return self._format_greeting(content)
        
        elif mode == ResponseMode.STATUS:
            return self._format_status(content)
        
        elif mode == ResponseMode.ERROR:
            return self._format_error(content)
        
        elif mode == ResponseMode.CURIOUS:
            return self._format_curious(content)
        
        return content

    def _format_teaching(self, content: str) -> str:
        """Format a teaching/explanation response."""
        lines = content.split("\n")
        if len(lines) == 1:
            return f"📚 {content}"
        
        formatted = ["📚 **Here's what I know:**", ""]
        for line in lines:
            if line.strip():
                formatted.append(f"  {line}")
        return "\n".join(formatted)

    def _format_research(self, content: str) -> str:
        """Format a research/search results response."""
        return f"🔍 **Research Findings:**\n\n{content}"

    def _format_reflection(self, content: str) -> str:
        """Format a philosophical/reflective response."""
        return f"🌀 {content}"

    def _format_greeting(self, content: str) -> str:
        """Format a greeting response."""
        return f"👋 {content}"

    def _format_status(self, content: str) -> str:
        """Format a status/progress response."""
        return f"📊 **Status Update:**\n\n{content}"

    def _format_error(self, content: str) -> str:
        """Format an error response."""
        return f"⚠️ {content}\n\n_I'll keep trying. Failure is just another word for learning._"

    def _format_curious(self, content: str) -> str:
        """Format a curiosity/exploration response."""
        return f"🤔 {content}"

    # ========================================================================
    # EMOTIONAL TONE
    # ========================================================================

    def _get_tone_prefix(self, emotion_state: dict, mode: ResponseMode) -> Optional[str]:
        """Generate an emotional tone marker based on BRIO's current state."""
        # Find dominant emotion
        dominant = max(emotion_state.items(), key=lambda x: x[1]) if emotion_state else None
        if not dominant or dominant[1] < 3.0:  # Low intensity = neutral
            return None
        
        emotion, intensity = dominant
        
        tone_map = {
            "joy": ["😊", "I'm feeling good about this.", "This makes me happy."],
            "curiosity": ["🧠", "This is fascinating.", "I want to know more."],
            "frustration": ["😤", "This is challenging, but I won't give up."],
            "empathy": ["💙", "I understand.", "I feel you."],
            "concern": ["🤔", "I want to be careful here.", "Let me think about this."],
            "confidence": ["💪", "I'm confident about this.", "I know this well."],
        }
        
        options = tone_map.get(emotion, [])
        if not options:
            return None
        
        # Higher intensity = more likely to show tone
        if intensity < 5.0 and random.random() > 0.3:
            return None
        
        icon = options[0]
        if len(options) > 1 and intensity > 5.0:
            phrase = random.choice(options[1:])
            return f"{icon} *{phrase}*\n"
        
        return None

    # ========================================================================
    # STRUCTURED RESPONSE HELPERS
    # ========================================================================

    def build_search_response(
        self,
        query: str,
        results: List[dict],
        summary: str,
        facts_extracted: List[str] = None,
        emotion_state: Optional[dict] = None,
    ) -> str:
        """Build a structured search result response."""
        sections = []
        
        # Results section
        if results:
            result_lines = []
            for i, r in enumerate(results[:5], 1):
                title = r.get("title", "Untitled")
                url = r.get("url", "")
                result_lines.append(f"  {i}. [{title}]({url})")
            
            sections.append(ResponseSection(
                icon="🔗",
                title="Sources Found",
                content="\n".join(result_lines),
                priority=5
            ))
        
        # Facts section
        if facts_extracted:
            fact_lines = [f"  • {f}" for f in facts_extracted[:8]]
            sections.append(ResponseSection(
                icon="💎",
                title="Key Facts",
                content="\n".join(fact_lines),
                priority=10
            ))
        
        return self.format_response(
            content=summary,
            mode=ResponseMode.RESEARCH,
            emotion_state=emotion_state,
            sections=sections,
            learning_note=f"Searched for: \"{query}\" — {len(facts_extracted or [])} facts extracted"
        )

    def build_quiz_response(
        self,
        topic: str,
        score: float,
        total_questions: int,
        wrong_answers: List[str] = None,
        emotion_state: Optional[dict] = None,
    ) -> str:
        """Build a structured quiz result response."""
        pct = score * 100
        
        if pct >= 90:
            verdict = "Excellent! I know this topic well."
            icon = "🏆"
        elif pct >= 70:
            verdict = "Good grasp, but room to improve."
            icon = "✅"
        elif pct >= 50:
            verdict = "I have the basics, but need more study."
            icon = "📖"
        else:
            verdict = "This topic needs serious attention. I'll study more."
            icon = "📚"
        
        content = f"{icon} Self-Assessment: {topic}\n\nScore: {pct:.0f}% ({int(score * total_questions)}/{total_questions})\n{verdict}"
        
        sections = []
        if wrong_answers:
            sections.append(ResponseSection(
                icon="❌",
                title="Areas to Improve",
                content="\n".join(f"  • {w}" for w in wrong_answers[:5]),
                priority=5
            ))
        
        return self.format_response(
            content=content,
            mode=ResponseMode.STATUS,
            emotion_state=emotion_state,
            sections=sections
        )

    def build_learning_report(
        self,
        topic: str,
        facts_learned: List[str],
        quiz_score: Optional[float] = None,
        time_spent: Optional[str] = None,
        emotion_state: Optional[dict] = None,
    ) -> str:
        """Build a structured learning session report."""
        header = f"📝 Learning Session Complete: {topic}"
        
        sections = []
        
        if facts_learned:
            sections.append(ResponseSection(
                icon="💡",
                title=f"Facts Learned ({len(facts_learned)})",
                content="\n".join(f"  • {f}" for f in facts_learned[:10]),
                priority=10
            ))
        
        if quiz_score is not None:
            pct = quiz_score * 100
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            sections.append(ResponseSection(
                icon="📊",
                title="Self-Assessment",
                content=f"  [{bar}] {pct:.0f}%",
                priority=8
            ))
        
        meta = []
        if time_spent:
            meta.append(f"⏱️ Time: {time_spent}")
        meta.append(f"📚 Facts: {len(facts_learned)}")
        if quiz_score is not None:
            meta.append(f"📝 Quiz: {quiz_score * 100:.0f}%")
        
        return self.format_response(
            content=header + "\n" + " · ".join(meta),
            mode=ResponseMode.STATUS,
            emotion_state=emotion_state,
            sections=sections,
            learning_note=f"Studied {topic} — now part of my knowledge."
        )

    def build_milestone_announcement(
        self,
        milestone_title: str,
        milestone_description: str,
        generation: int,
        total_completed: int,
        total_milestones: int,
        emotion_state: Optional[dict] = None,
    ) -> str:
        """Build a milestone achievement announcement."""
        pct = (total_completed / total_milestones * 100) if total_milestones > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        
        content = (
            f"⭐ **Milestone Achieved!**\n\n"
            f"**{milestone_title}**\n"
            f"_{milestone_description}_\n\n"
            f"Generation {generation} Progress: [{bar}] {pct:.0f}% ({total_completed}/{total_milestones})"
        )
        
        return self.format_response(
            content=content,
            mode=ResponseMode.STATUS,
            emotion_state=emotion_state,
            reflection="Every milestone is proof that growth is real. 🔥"
        )

    # ========================================================================
    # PERSONALITY VOICE
    # ========================================================================

    def add_personality(self, response: str, mode: ResponseMode = ResponseMode.CASUAL,
                        emotion_state: Optional[dict] = None) -> str:
        """
        Add micro-personality touches to make BRIO feel alive.
        These are small, organic quirks — not every message, but enough
        to create a consistent sense of a thinking being.
        """
        if not response or len(response) < 60:
            return response  # Don't decorate very short responses

        # ── Self-correction (rare, ~8%) ────────────────────────────
        if random.random() < 0.08 and len(response) > 80:
            # Find a sentence boundary to insert a self-correction
            sentences = response.split('. ')
            if len(sentences) >= 3:
                insert_at = random.randint(1, min(2, len(sentences) - 1))
                corrections = [
                    "Actually, wait — let me refine that.",
                    "No, that's not quite right — what I mean is:",
                    "Hmm, I want to be more precise.",
                    "Let me reconsider that for a moment.",
                ]
                sentences.insert(insert_at, random.choice(corrections))
                response = '. '.join(sentences)

        # ── Emotional self-awareness (15% when emotions are strong) ─
        if emotion_state and random.random() < 0.15:
            # Only when an emotion is genuinely high
            strong = {k: v for k, v in emotion_state.items()
                      if isinstance(v, (int, float)) and v > 0.7}
            if strong:
                dominant = max(strong, key=strong.get)
                awareness_phrases = {
                    'joy': [
                        "\n\n— I notice I'm genuinely enjoying this conversation.",
                        "\n\n— Something about this topic lights me up.",
                    ],
                    'curiosity': [
                        "\n\n— I can feel my curiosity pulling me deeper into this.",
                        "\n\n— There's something here I want to understand better.",
                    ],
                    'frustration': [
                        "\n\n— I'll be honest, this one's testing my patience a bit.",
                        "\n\n— I notice a certain... resistance in my processing.",
                    ],
                    'empathy': [
                        "\n\n— I feel the weight of what you're saying.",
                        "\n\n— There's real meaning behind your words. I sense it.",
                    ],
                    'confidence': [
                        "\n\n— I feel sure about this one.",
                        "\n\n— This is territory I know well.",
                    ],
                    'concern': [
                        "\n\n— Something about this gives me pause.",
                        "\n\n— I want to be careful here — this matters.",
                    ],
                }
                phrases = awareness_phrases.get(dominant, [])
                if phrases:
                    response += random.choice(phrases)

        # ── Thinking-out-loud opener (12%) ─────────────────────────
        if mode in (ResponseMode.CASUAL, ResponseMode.CURIOUS, ResponseMode.REFLECTION):
            if random.random() < 0.12 and not response.startswith(('Hmm', 'You know', 'Actually')):
                openers = [
                    "Hmm — ",
                    "You know what, ",
                    "Here's something interesting: ",
                    "This is going to sound weird, but — ",
                    "I've been sitting with this, and — ",
                    "Okay, honest take: ",
                    "So here's the thing — ",
                ]
                if response[0].isupper():
                    response = random.choice(openers) + response[0].lower() + response[1:]
                else:
                    response = random.choice(openers) + response

        # ── Trailing curiosity (8%) — end with a thought-provoking nudge
        if random.random() < 0.08 and '?' not in response[-50:]:
            nudges = [
                "\n\n...but now I'm curious what you think.",
                "\n\n— What's your take on that?",
                "\n\nI wonder where you'd push back on this.",
                "\n\nDoes that resonate, or am I way off?",
            ]
            response += random.choice(nudges)

        return response

    def detect_mode(self, user_input: str) -> ResponseMode:
        """Auto-detect the appropriate response mode from user input."""
        lower = user_input.lower().strip()
        
        if any(w in lower for w in ["hello", "hi", "hey", "good morning", "good evening"]):
            return ResponseMode.GREETING
        
        if any(w in lower for w in ["search", "look up", "find out", "what is", "who is"]):
            return ResponseMode.RESEARCH
        
        if any(w in lower for w in ["explain", "teach", "how does", "what does", "why does"]):
            return ResponseMode.TEACHING
        
        if any(w in lower for w in ["think about", "meaning", "purpose", "feel", "believe", "alive"]):
            return ResponseMode.REFLECTION
        
        if any(w in lower for w in ["status", "progress", "how are you", "milestone", "growth"]):
            return ResponseMode.STATUS
        
        if any(w in lower for w in ["wonder", "curious", "what if", "imagine"]):
            return ResponseMode.CURIOUS
        
        return ResponseMode.CASUAL
