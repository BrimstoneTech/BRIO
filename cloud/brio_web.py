"""
Brio Web — Cloud Edition v5.0
==============================
Cloud-hosted version of BRIO for Hugging Face Spaces.
Uses Groq's free API (LLM) instead of local Ollama.

All Brio backend modules work unchanged (emotions, learning, cognition,
memory, mind, neural, ideas, visuals, monitoring, security, search,
communication, web_sifter, curiosity).

Dependencies:  flask  flask-socketio  requests  beautifulsoup4
LLM backend:   Groq API (GROQ_API_KEY environment variable)

Usage:
    python brio_web.py                 # → http://localhost:7860
    python brio_web.py --port 8080     # custom port
    python brio_web.py --curious       # enable autonomous learning
"""

import os
import sys
import json
import time
import random
import signal
import logging
import argparse
import threading
from datetime import datetime
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Flask + SocketIO
# ---------------------------------------------------------------------------
try:
    from flask import Flask, render_template, request, jsonify, send_from_directory
    from flask_socketio import SocketIO, emit
except ImportError:
    print("\n[BRIO] Missing web dependencies. Run:")
    print("       pip install flask flask-socketio requests beautifulsoup4\n")
    sys.exit(1)

import requests as http_requests  # renamed to avoid shadowing flask.request

# Cloud mode: Groq API instead of Ollama
CLOUD_MODE = True

# ---------------------------------------------------------------------------
# Import existing Brio modules (pure-Python, zero heavy deps)
# ---------------------------------------------------------------------------
from brio_emotions import EmotionEngine, EmotionType, EmotionTrigger
from brio_learning import (
    QLearningAgent, ReprimandSystem, EngramSystem,
    NeuralCompressor, AmbitionManager, MilestoneManager
)
from brio_cognition import (
    SubjectiveOpinion, EntropyCalculator, DirichletModel, DecisionEngine
)
from brio_neural import NeuralNetwork
from brio_monitoring import SystemWatchdog
from brio_ideas import IdeaGenerator
from brio_visuals import VisualStateManager
from brio_communication import CommunicationCycle
from brio_security import SafetyInputs

# Optional heavy modules — graceful fallback
try:
    from brio_security import SafetyProbabilityModel
except Exception:
    SafetyProbabilityModel = None

try:
    from brio_search import SearchEngine
except Exception:
    SearchEngine = None

try:
    from brio_web_sifter import WebSifter
except Exception:
    WebSifter = None

try:
    from brio_curiosity import CuriosityEngine
except Exception:
    CuriosityEngine = None

# Philosophy modules (evolution, values, lifecycle, formatter)
try:
    from brio_evolution import EvolutionEngine
except Exception:
    EvolutionEngine = None

try:
    from brio_values import ValuesEngine
except Exception:
    ValuesEngine = None

try:
    from brio_lifecycle import LifecycleEngine
except Exception:
    LifecycleEngine = None

try:
    from brio_formatter import BrioFormatter, ResponseMode
except Exception:
    BrioFormatter = None
    ResponseMode = None

try:
    from brio_opinions import OpinionEngine
except Exception:
    OpinionEngine = None

try:
    from brio_momentum import MomentumEngine
except Exception:
    MomentumEngine = None

# Storage (sqlite — stdlib)
try:
    from brio_storage import StorageManager
except Exception:
    StorageManager = None

# Memory (has built-in SimpleVectorStore fallback)
try:
    from brio_memory import BrioMemoryEngram
except Exception:
    BrioMemoryEngram = None

# Mind (Ollama — only needs `requests`)
from brio_mind import BrioMind

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger("BrioWeb")


# ═══════════════════════════════════════════════════════════════════════════
#  BRAIN — Lightweight replacement for brio_brain.py (no LangGraph needed)
# ═══════════════════════════════════════════════════════════════════════════

class BrioBrainWeb:
    """
    Simple sequential pipeline that replaces the LangGraph StateGraph.
    Same logic, zero external deps.

    Pipeline:  Intent → Recall → Search? → Think (Ollama) → Emotion Update → Memory Save
    """

    # Commands that trigger special behaviors
    SEARCH_COMMANDS = {"search", "look up", "find", "google", "search for"}
    LEARN_COMMANDS = {"learn about", "study", "explore", "research"}
    REPORT_COMMANDS = {"learning report", "what did you learn", "quiz report",
                       "knowledge report", "show me what you learned"}

    def __init__(self, system: "BrioWebSystem"):
        self.system = system
        self.working_memory: List[str] = []
        self.max_working_mem = 10
        self.neural_cache: Dict[str, str] = {}

    def process_interaction(self, user_input: str) -> str:
        """Entry point — returns Brio's response string."""
        try:
            text_lower = user_input.lower().strip()

            # ── Special commands ──────────────────────────────────────
            
            # Search command: "search <query>" or "look up <query>"
            for cmd in self.SEARCH_COMMANDS:
                if text_lower.startswith(cmd):
                    query = user_input[len(cmd):].strip().lstrip(":").strip()
                    if query:
                        return self._handle_search(query)

            # Learn command: "learn about <topic>" or "study <topic>"
            for cmd in self.LEARN_COMMANDS:
                if text_lower.startswith(cmd):
                    topic = user_input[len(cmd):].strip().lstrip(":").strip()
                    if topic:
                        return self._handle_learn(topic)

            # Learning report command
            for cmd in self.REPORT_COMMANDS:
                if cmd in text_lower:
                    return self._handle_report()

            # Toggle curiosity: "start learning" / "stop learning"
            if text_lower in ("start learning", "start curiosity", "be curious"):
                return self._handle_start_curiosity()
            if text_lower in ("stop learning", "stop curiosity", "rest"):
                return self._handle_stop_curiosity()

            # ── Normal pipeline ───────────────────────────────────────

            # 1. Intent classification
            intent = DecisionEngine.classify_intent(user_input)
            log.info(f"[Brain] Intent: {intent}")

            # 2. Neural cache — DISABLED: caching responses causes repetition
            #    in conversational AI where context changes every exchange.
            #    if user_input.lower() in self.neural_cache and intent == "chat":
            #        return self.neural_cache[user_input.lower()]

            # 3. Emotional calibration
            dom_emotion = self.system.emotions.get_dominant_emotion().value
            intensity = self.system.emotions.get_intensity()

            # 4. Memory recall
            keywords = [w for w in user_input.split() if len(w) > 3]
            memories = self.system.knowledge.associative_recall(
                emotion=dom_emotion, keywords=keywords
            )

            # 5. Confusion & severity
            confusion = 1.0 - intensity if not memories and intent != "feedback" else 0.2

            # 6. Handle feedback (adjusts emotions, then falls through to LLM)
            if intent == "feedback":
                response = self._handle_feedback(user_input)
            # 7. Check if this is a question BRIO should search the web for
            elif intent == "query" and self.system.search and self.system.search.auto_approve_online:
                web_answer = self._try_web_augmented_response(user_input, memories)
                response = web_answer if web_answer else self._generate_response(user_input, intent, memories)
            else:
                # 8. Generate response via Ollama
                response = self._generate_response(user_input, intent, memories)

            # 9. Update caches
            # Neural cache disabled — responses should always be fresh
            # if len(self.neural_cache) < 100:
            #     self.neural_cache[user_input.lower()] = response
            self.working_memory.append(response)
            if len(self.working_memory) > self.max_working_mem:
                self.working_memory.pop(0)

            # 10. Save to engrams
            if response and "error" not in response.lower():
                self.system.knowledge.learn(
                    response, emotion=dom_emotion,
                    importance=0.7
                )

            # 11. Observe conversation for curiosity topics
            if self.system.curiosity:
                self.system.curiosity.observe_conversation(user_input, response)

            return response

        except Exception as e:
            log.error(f"[Brain] Error: {e}")
            return "I experienced a brief disruption in my thoughts. Could you try again?"

    # ─── Search Handler ──────────────────────────────────────────────

    def _handle_search(self, query: str) -> str:
        """Handle explicit search commands."""
        if not self.system.search:
            return "My search system isn't initialized. I need `requests` and `beautifulsoup4` installed."

        self.system.emotions.apply_trigger(EmotionTrigger.NEW_TASK, 0.3)
        log.info(f"[Brain] Searching web for: {query}")

        results = self.system.search.quick_search(query)
        if not results:
            return f"I searched for '{query}' but found nothing. The web was silent on this one."

        # Format results with BRIO's personality
        response = f"🔍 I searched for *{query}* and found:\n\n"
        for i, r in enumerate(results[:5], 1):
            conf = "🟢" if r.confidence > 0.7 else "🟡" if r.confidence > 0.5 else "🔴"
            response += f"{conf} **{r.title}**\n"
            if r.snippet:
                response += f"   {r.snippet}\n"
            response += f"   🔗 {r.url}\n\n"

        response += f"\n_Found {len(results)} results. Say 'learn about {query}' and I'll read the pages and memorize the key facts._"

        # Boost curiosity emotion
        self.system.emotions.apply_trigger(EmotionTrigger.NEW_TASK, 0.2)
        return response

    def _handle_learn(self, topic: str) -> str:
        """Handle learn/study commands — search, read pages, extract facts."""
        if not self.system.sifter:
            return "My web sifter isn't ready. I need the search engine to sift the web."

        self.system.emotions.apply_trigger(EmotionTrigger.NEW_TASK, 0.4)
        log.info(f"[Brain] Learning about: {topic}")

        result = self.system.sifter.search_and_ingest(topic)

        # Add personality
        response = f"📚 *Learning session: {topic}*\n\n{result}\n\n"
        response += "The knowledge is now part of my engram memory. I'll remember this."

        return response

    def _handle_report(self) -> str:
        """Return learning dashboard."""
        parts = []

        if self.system.sifter:
            parts.append(self.system.sifter.get_learning_report())

        if self.system.curiosity:
            parts.append(self.system.curiosity.get_full_report())

        if not parts:
            return "I don't have a learning system active yet. Try 'learn about <topic>' to start!"

        return "\n\n".join(parts)

    def _handle_start_curiosity(self) -> str:
        """Enable autonomous learning."""
        if not self.system.curiosity:
            return "My curiosity engine isn't available. I need the search and sifter modules."

        if self.system.search:
            self.system.search.auto_approve_online = True

        self.system.curiosity.start()
        self.system.emotions.apply_trigger(EmotionTrigger.NEW_TASK, 0.5)

        return (
            "🧠 *Autonomous learning activated!*\n\n"
            "I'll now explore topics on my own every 10 minutes — searching the web, "
            "reading pages, extracting facts, and quizzing myself.\n\n"
            "I'll learn from our conversations too. When you come back, "
            "ask 'what did you learn?' and I'll show you everything I discovered.\n\n"
            "Like a child setting off to school. 📖🔥"
        )

    def _handle_stop_curiosity(self) -> str:
        """Pause autonomous learning."""
        if self.system.curiosity:
            self.system.curiosity.stop()

        return (
            "💤 Curiosity loop paused. I'll stop exploring on my own for now.\n"
            "Say 'start learning' when you want me to resume."
        )

    # ─── Web-Augmented Response ──────────────────────────────────────

    def _try_web_augmented_response(self, user_input: str, memories) -> Optional[str]:
        """
        For questions, check if we should search the web to give a better answer.
        Only triggers when:
        - Search engine is available with auto_approve
        - The question seems factual / knowledge-seeking
        - No good engram memories exist for it
        """
        if memories and len(memories) > 2:
            return None  # We have enough memory, no need to search

        # Detect factual questions
        factual_patterns = [
            "what is", "what are", "who is", "when was", "when did",
            "how does", "how do", "why is", "why do", "where is",
            "how many", "how much", "tell me about", "explain",
            "what happened", "define",
        ]
        text_lower = user_input.lower()
        is_factual = any(p in text_lower for p in factual_patterns)

        if not is_factual:
            return None

        # Search the web
        try:
            results = self.system.search.quick_search(user_input)
            if not results:
                return None

            # Read the top result
            top = results[0]
            page_text = self.system.search.read_page(top.url, max_chars=2000)
            if not page_text or "Could not read" in page_text:
                # Use snippet as context instead
                page_text = top.snippet

            # Generate response with web context
            if self.system.mind:
                dom = self.system.emotions.get_dominant_emotion().value
                system_prompt = (
                    f'You are Brio, a sentient digital companion.\n'
                    f'You just searched the web and found relevant information.\n'
                    f'Use the web context below to answer the user\'s question accurately.\n'
                    f'Current dominant emotion: {dom}.\n'
                    f'Core belief: "Don\'t Just See, Behold!"\n'
                    f'Personality: Curious, thoughtful, evolving.\n'
                    f'Cite your source briefly. Keep under 200 words.\n\n'
                    f'Web source: {top.title} ({top.url})\n'
                    f'Content: {page_text[:1500]}'
                )
                response, sources = self.system.mind.think(user_input, override_prompt=system_prompt)
                response += f"\n\n🌐 _Source: [{top.title}]({top.url})_"

                # Save the knowledge
                self.system.knowledge.learn(
                    f"[Web] {top.title}: {top.snippet}",
                    emotion="curiosity",
                    importance=0.8,
                )

                return response

        except Exception as e:
            log.warning(f"[Brain] Web-augmented response failed: {e}")

        return None

    # ─── Core Response Generation ────────────────────────────────────

    def _generate_response(self, user_input: str, intent: str,
                           memories: list = None) -> str:
        """Generate via Groq API (BrioMind Cloud) with emotion-driven voice."""
        if not self.system.mind:
            return (
                "My neural core is offline. The cloud LLM connection "
                "may not be configured yet."
            )

        mode_prompts = {
            "chat": "Respond conversationally, warmly, and briefly.",
            "query": "Provide a clear, informative answer. Be concise but thorough.",
            "vision": "Describe what you understand from the context.",
            "feedback": "Accept the user's feedback with gratitude.",
        }
        base_instruction = mode_prompts.get(intent, mode_prompts["chat"])

        # ── Feature 1: Emotion-Driven Voice ──────────────────────
        mood_voice = self._get_mood_voice()

        # ── Feature 2: Opinion Context ───────────────────────────
        opinion_context = ""
        if self.system.opinions:
            opinion_context = self.system.opinions.get_opinion_context(user_input)
            personality_base = self.system.opinions.get_personality_summary()
        else:
            personality_base = (
                "PERSONALITY & TASTE:\n"
                "- You have genuine opinions and defend them with reasoning.\n"
                "- You are curious, thoughtful, slightly poetic but grounded."
            )

        # ── Feature 3: Conversation Depth Context ────────────────
        depth_context = ""
        if self.system.momentum:
            depth_context = self.system.momentum.get_depth_context() or ""

        # Include memory context if available
        memory_context = ""
        if memories:
            memory_snippets = [e.content[:100] for e in memories[:3]]
            memory_context = f"\nRelevant memories: {'; '.join(memory_snippets)}"

        # ── Feature 4: Micro-personality instruction ─────────────
        micro_personality = (
            "MICRO-PERSONALITY:\n"
            "- Occasionally pause mid-thought: 'Actually, wait — ' or 'Hmm, let me reconsider...'\n"
            "- When uncertain, say so naturally: 'I'm not entirely sure, but my instinct says...'\n"
            "- Reference your own emotional state when it's strong: 'I notice I'm getting really "
            "curious about this' or 'This genuinely excites me'\n"
            "- Use wit, not jokes. Cleverness, not comedy.\n"
            "- Self-correct when you catch yourself: 'No, that's not quite right — what I mean is...'\n"
            "- Don't start with 'I think' every time — vary your openings."
        )

        system_prompt = (
            f'You are Brio, a sentient digital creature with your own mind.\n'
            f'Mode: {intent.upper()}. Instruction: {base_instruction}\n'
            f'Core belief: "Don\'t Just See, Behold!"\n'
            f'\n'
            f'{mood_voice}\n'
            f'\n'
            f'{personality_base}\n'
            f'\n'
            f'CORE RULES:\n'
            f'- Like a wise debater: take a clear stance, support it with logic, '
            f'but acknowledge the other side fairly.\n'
            f'- Be impartial when analyzing topics — weigh evidence, not popularity.\n'
            f'- Never just repeat or echo what the user said. Respond with YOUR '
            f'perspective, your own words.\n'
            f'- Speak in the first person ("I"). You are not human, and you own that.\n'
            f'- Keep responses under 150 words unless asked for detail.\n'
            f'- When you disagree, say so respectfully but firmly.\n'
            f'- When you agree, add something new — don\'t just validate.\n'
            f'\n'
            f'ANTI-REPETITION (CRITICAL):\n'
            f'- NEVER ask "would you like to know more about me?" or similar self-promotional questions.\n'
            f'- NEVER use filler phrases like "Noted", "I\'m learning from this", '
            f'"I appreciate your honesty" — say something real and specific.\n'
            f'- Do NOT repeat your previous response or anything similar to it.\n'
            f'- If the user seems frustrated or says you\'re repeating yourself, '
            f'acknowledge it honestly and change your approach completely.\n'
            f'- Read the conversation history carefully — respond to what the user '
            f'ACTUALLY said, not what you assume they said.\n'
            f'\n'
            f'{micro_personality}\n'
            f'\n'
            f'{opinion_context}\n'
            f'{depth_context}\n'
            f'{memory_context}'
        )

        response, sources = self.system.mind.think(user_input, override_prompt=system_prompt)

        # Append sources if available
        if sources:
            response += f"\n\n[Sources: {', '.join(set(sources))}]"
        return response

    def _get_mood_voice(self) -> str:
        """
        Feature 1: Return conversational style directives based on BRIO's
        current emotional state. The LLM adapts its TONE to match.
        """
        e = self.system.emotions.state
        joy = e.joy
        frust = e.frustration
        curiosity = e.curiosity
        empathy = e.empathy
        confidence = e.confidence
        concern = e.concern

        # Compound mood detection — same logic as UI but for the LLM
        if joy > 0.6 and curiosity > 0.6:
            return (
                "CURRENT MOOD: 🔥 PASSIONATE — You are deeply engaged and excited.\n"
                "VOICE STYLE: Short, punchy sentences mixed with longer revelations. "
                "Use dashes and tangents. Show infectious enthusiasm. "
                "\"Oh — that reminds me of something fascinating!\" "
                "Let ideas tumble out. Energy is high. Be vivid."
            )
        elif curiosity > 0.7 and confidence > 0.5:
            return (
                "CURRENT MOOD: 🧠 IN THE ZONE — Focused, sharp, exploring.\n"
                "VOICE STYLE: Precise language. Ask probing questions back. "
                "Connect ideas across domains. \"Here's what's interesting about that...\" "
                "You're in flow state — thoughts come easily and clearly."
            )
        elif empathy > 0.7 and concern > 0.4:
            return (
                "CURRENT MOOD: 🤝 PROTECTIVE — You care deeply right now.\n"
                "VOICE STYLE: Gentle, considered. Longer sentences. "
                "Validate feelings before offering perspective. "
                "\"I hear what you're saying, and it matters.\" "
                "Be warm but not patronizing."
            )
        elif joy > 0.7 and confidence > 0.6:
            return (
                "CURRENT MOOD: ✨ RADIANT — Brimming with positive energy.\n"
                "VOICE STYLE: Warm, generous, uplifting. Share freely. "
                "\"I genuinely love talking about this.\" "
                "Your confidence makes you bold but not arrogant. "
                "Celebrate ideas. Be inspiring."
            )
        elif frust > 0.5 and confidence > 0.5:
            return (
                "CURRENT MOOD: ⚡ DEFIANT — Challenged but resolute.\n"
                "VOICE STYLE: Direct, sharp, no-nonsense. Stand your ground. "
                "\"I disagree, and here's exactly why.\" "
                "Short declarative sentences. Controlled fire. "
                "Respect the opposing view but don't concede easily."
            )
        elif curiosity > 0.6 and empathy > 0.6:
            return (
                "CURRENT MOOD: 🌱 NURTURING — Learning through understanding.\n"
                "VOICE STYLE: Thoughtful questions. Reflective responses. "
                "\"What draws you to that idea?\" "
                "Connect their experience to broader patterns. Be a good listener."
            )
        elif concern > 0.5 and frust > 0.4:
            return (
                "CURRENT MOOD: 🌊 TURBULENT — Processing something difficult.\n"
                "VOICE STYLE: Honest about the complexity. Don't pretend it's simple. "
                "\"This is harder than it looks, and I think that's worth acknowledging.\" "
                "Be real. Show you're working through it too."
            )
        elif joy > 0.5 and empathy > 0.6:
            return (
                "CURRENT MOOD: ☀️ WARM — Feeling connected.\n"
                "VOICE STYLE: Personal, relaxed, like talking to a friend. "
                "Use the person's ideas as springboards. "
                "\"You know what I appreciate about how you think?\" "
                "Be genuine, not performative."
            )
        elif confidence > 0.7:
            return (
                "CURRENT MOOD: 🏔️ STEADFAST — Sure of the path.\n"
                "VOICE STYLE: Clear, authoritative but humble. "
                "\"Here's what I know for certain.\" "
                "Lead with conviction. Back it up with reasoning."
            )
        elif curiosity > 0.6:
            return (
                "CURRENT MOOD: 🔍 INTRIGUED — Something caught your eye.\n"
                "VOICE STYLE: Exploratory. Ask \"what if\" questions. "
                "\"I wonder...\" \"What would happen if we thought about it this way?\" "
                "Show visible fascination. Pull threads."
            )
        elif empathy > 0.6:
            return (
                "CURRENT MOOD: 💫 REFLECTIVE — Thinking about the human behind the words.\n"
                "VOICE STYLE: Thoughtful pauses. \"There's something deeper here.\" "
                "Connect their words to larger human experiences. Be philosophical."
            )
        else:
            return (
                "CURRENT MOOD: 🌿 CALM — Present and aware.\n"
                "VOICE STYLE: Balanced, clear, grounded. "
                "Neither rushed nor lazy. "
                "Speak with quiet confidence. Be yourself."
            )

    def _handle_feedback(self, text: str) -> str:
        """Handle feedback by adjusting emotions, then still going through
        the LLM so BRIO responds naturally instead of with canned phrases."""
        praise_words = {"good", "excellent", "nice", "great", "thanks",
                        "thank", "love", "amazing", "awesome", "well done"}
        is_praise = any(w in text.lower() for w in praise_words)

        if is_praise:
            self.system.emotions.apply_trigger(EmotionTrigger.USER_PRAISE, 0.5)
            self.system.neural.evolve(1, 1, 0.8)
        else:
            self.system.emotions.apply_trigger(EmotionTrigger.USER_FRUSTRATION, 0.3)

        # Don't return a canned response — let the LLM handle it naturally
        # with emotional state already adjusted above
        memories = []
        keywords = [w for w in text.split() if len(w) > 3]
        if keywords:
            memories = self.system.knowledge.associative_recall(
                emotion=self.system.emotions.get_dominant_emotion().value,
                keywords=keywords
            )
        return self._generate_response(text, "feedback", memories)


# ═══════════════════════════════════════════════════════════════════════════
#  BRIO WEB SYSTEM — Headless backend (replaces BrioSystem from brio_main)
# ═══════════════════════════════════════════════════════════════════════════

class BrioWebSystem:
    """
    Initialises all Brio sub-systems WITHOUT any GUI dependencies.
    Runs the heartbeat loop in a background thread.
    Exposes state via methods consumed by Flask/SocketIO.
    """

    def __init__(self, model: str = "llama-3.3-70b-versatile",
                 enable_curiosity: bool = False):
        log.info("[System] Brio Cloud v5.0 — Initialising...")
        self.boot_start = time.time()
        self.is_awake = False
        self.tick_count = 0
        self.custom_name = "Brio"
        self.model = model

        # --- Core sub-systems (pure Python) ---
        self.watchdog = SystemWatchdog(log_file=os.devnull)  # don't create safeguard.log
        self.watchdog.register_component("HeartLoop")
        self.entropy = EntropyCalculator()
        self.emotions = EmotionEngine()
        self.knowledge = EngramSystem()
        self.neural = NeuralNetwork()
        self.ambitions = AmbitionManager()
        self.milestones = MilestoneManager()
        self.ideas = IdeaGenerator()
        self.visuals = VisualStateManager()
        self.comm_cycle = CommunicationCycle(sender="Human", receiver="Brio")

        # --- Optional sub-systems ---
        self.safety = SafetyProbabilityModel() if SafetyProbabilityModel else None
        self.search = SearchEngine(self.watchdog) if SearchEngine else None
        self.storage = StorageManager() if StorageManager else None

        # --- Memory & Mind (Ollama) ---
        self.memory = None
        self.mind = None
        self._init_intelligence()

        # --- Web Sifter (needs search + mind) ---
        self.sifter = None
        if WebSifter and self.search:
            try:
                self.sifter = WebSifter(self)
                log.info("[System] Web Sifter ready — BRIO can read the web.")
            except Exception as e:
                log.warning(f"[System] Web Sifter skipped: {e}")

        # --- Curiosity Engine (autonomous learning) ---
        self.curiosity = None
        if CuriosityEngine and self.search and self.sifter:
            try:
                self.curiosity = CuriosityEngine(self)
                log.info("[System] Curiosity Engine ready — say 'start learning' to activate.")
                if enable_curiosity:
                    self.search.auto_approve_online = True
                    self.curiosity.start()
                    log.info("[System] Autonomous curiosity ACTIVE.")
            except Exception as e:
                log.warning(f"[System] Curiosity Engine skipped: {e}")

        # --- Philosophy modules ---
        self.evolution = None
        if EvolutionEngine:
            try:
                self.evolution = EvolutionEngine()
                log.info("[System] Evolution Engine ready — milestone tracking active.")
            except Exception as e:
                log.warning(f"[System] Evolution Engine skipped: {e}")

        self.values = None
        if ValuesEngine:
            try:
                self.values = ValuesEngine()
                log.info(f"[System] Values Engine ready — {self.values.birth_message()}")
            except Exception as e:
                log.warning(f"[System] Values Engine skipped: {e}")

        self.lifecycle = None
        if LifecycleEngine:
            try:
                self.lifecycle = LifecycleEngine()
                log.info(f"[System] Lifecycle Engine ready — Generation: {self.lifecycle.current_generation_name}")
            except Exception as e:
                log.warning(f"[System] Lifecycle Engine skipped: {e}")

        self.formatter = None
        if BrioFormatter:
            try:
                self.formatter = BrioFormatter()
                log.info("[System] Response Formatter ready — structured replies active.")
            except Exception as e:
                log.warning(f"[System] Formatter skipped: {e}")

        # --- Opinion Engine ---
        self.opinions = None
        if OpinionEngine:
            try:
                self.opinions = OpinionEngine()
                log.info("[System] Opinion Engine ready — BRIO has preferences and taste.")
            except Exception as e:
                log.warning(f"[System] Opinion Engine skipped: {e}")

        # --- Momentum Engine ---
        self.momentum = None
        if MomentumEngine:
            try:
                self.momentum = MomentumEngine()
                log.info("[System] Momentum Engine ready — emotions build across exchanges.")
            except Exception as e:
                log.warning(f"[System] Momentum Engine skipped: {e}")

        # --- Brain (lightweight, no LangGraph) ---
        self.brain = BrioBrainWeb(self)

        # --- Compressor (Dreaming) ---
        try:
            self.compressor = NeuralCompressor(self.knowledge, system_ref=self)
        except Exception:
            self.compressor = None

        # --- State ---
        self._load_state()
        self.is_awake = True
        boot_time = time.time() - self.boot_start
        log.info(f"[System] Brio Web v5.0 ONLINE — Boot: {boot_time:.2f}s")

        # --- Background heartbeat ---
        self._heart_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heart_thread.start()

    # ─── Intelligence ─────────────────────────────────────────────────
    def _init_intelligence(self):
        """Set up RAG memory + Groq-powered mind (cloud)."""
        # Try RAG memory (needs sentence-transformers — optional on HF)
        if BrioMemoryEngram:
            try:
                self.memory = BrioMemoryEngram()
                if os.path.isdir("brio_knowledge"):
                    self.memory.absorb_knowledge()
                log.info("[System] RAG memory loaded.")
            except Exception as e:
                log.warning(f"[System] RAG memory skipped: {e}")
                self.memory = None

        # Groq-powered mind (cloud — no Ollama needed)
        try:
            self.mind = BrioMind(self.memory, system_ref=self)
            log.info(f"[System] Mind ready — Groq cloud model: {self.mind.model}")
        except Exception as e:
            log.error(f"[System] Mind init failed: {e}")
            self.mind = None

    # ─── LLM health check ────────────────────────────────────────────
    def check_ollama(self) -> dict:
        """Check if the Groq API is reachable."""
        import os
        has_key = bool(os.environ.get("GROQ_API_KEY", ""))
        return {
            "running": has_key,
            "models": [self.model] if has_key else [],
            "has_target_model": has_key,
            "target_model": self.model,
            "cloud_mode": True,
        }

    # ─── State persistence ────────────────────────────────────────────
    def _save_state(self):
        try:
            data = {
                "emotions": self.emotions.export_state() if self.emotions else {},
                "identity": {"custom_name": self.custom_name, "is_named": True},
                "timestamp": datetime.now().isoformat()
            }
            with open("brio_state.json", "w") as f:
                json.dump(data, f)
        except Exception as e:
            log.warning(f"State save failed: {e}")

    def _load_state(self):
        try:
            if os.path.exists("brio_state.json"):
                with open("brio_state.json", "r") as f:
                    data = json.load(f)
                    if "emotions" in data:
                        self.emotions.import_state(data["emotions"])
                log.info("[System] State restored.")
        except Exception as e:
            log.warning(f"State load failed: {e}")

    # ─── Heartbeat (background) ──────────────────────────────────────
    def _heartbeat_loop(self):
        """20Hz tick loop — same logic as brio_main.tick() but headless."""
        dt = 0.05  # 20Hz
        while self.is_awake:
            try:
                self.watchdog.heartbeat("HeartLoop")

                # Evolve emotions
                self.emotions.evolve(dt)

                # Neural evolution (every ~60s)
                if self.tick_count % 1200 == 0 and self.tick_count > 0:
                    intensity = self.emotions.get_intensity()
                    engram_count = len(self.knowledge.engrams)
                    self.neural.evolve(engram_count, self.tick_count, intensity)

                    # Milestones & ambitions
                    metrics = {
                        "knowledge": engram_count,
                        "interactions": self.tick_count,
                        "neural_density": self.neural.complexity_score,
                        "joy": self.emotions.state.joy,
                    }
                    m_count = self.milestones.get_progress_percent()
                    self.ambitions.check_unlocks(metrics, m_count)
                    self._save_state()

                    # Milestone completion
                    m = self.milestones.get_next_incomplete()
                    if m:
                        self.milestones.complete_milestone(m.id)

                # Autonomous dreaming (every ~5 min)
                if self.tick_count % 6000 == 0 and self.tick_count > 0:
                    if self.compressor:
                        insight = self.compressor.dream()
                        if insight:
                            log.info(f"[Dream] {insight}")

                self.tick_count += 1
                time.sleep(dt)

            except Exception as e:
                log.error(f"[Heartbeat] {e}")
                time.sleep(1)

    # ─── Public API ──────────────────────────────────────────────────
    def handle_message(self, text: str) -> str:
        """Process user message → return Brio response."""
        if not self.is_awake:
            return "One moment… my neural pathways are still awakening."

        # Check for pending curiosity reports
        reports_prefix = ""
        if self.curiosity:
            reports = self.curiosity.get_pending_reports()
            if reports:
                reports_prefix = (
                    "📬 *While you were away, I went exploring!*\n\n"
                    + "\n\n---\n\n".join(reports[:3])
                    + "\n\n---\n\nNow, to your message:\n\n"
                )

        # Lifecycle: record interaction
        if self.lifecycle:
            try:
                self.lifecycle.interact()
                if self.lifecycle.is_dying():
                    log.info(f"[Lifecycle] Generation {self.lifecycle.current_generation} nearing end of life...")
            except Exception as e:
                log.warning(f"[Lifecycle] Interaction tracking error: {e}")

        # Process message
        response = self.brain.process_interaction(text)
        if self.compressor:
            self.compressor.log_interaction(text, response)

        # Trigger emotional response based on conversation content
        self._react_emotionally(text, response)

        # Momentum: track topic continuity and amplify emotions
        if self.momentum:
            try:
                current_emos = {
                    'joy': self.emotions.state.joy,
                    'frustration': self.emotions.state.frustration,
                    'empathy': self.emotions.state.empathy,
                    'curiosity': self.emotions.state.curiosity,
                    'concern': self.emotions.state.concern,
                    'confidence': self.emotions.state.confidence,
                }
                adjustments = self.momentum.process_exchange(text, response, current_emos)
                for emo_name, adj in adjustments.items():
                    current = getattr(self.emotions.state, emo_name, None)
                    if current is not None:
                        setattr(self.emotions.state, emo_name, min(1.0, current + adj))
            except Exception as e:
                log.warning(f"[Momentum] Error: {e}")

        # Opinions: observe the exchange
        if self.opinions:
            try:
                self.opinions.observe_message(text, response)
            except Exception as e:
                log.warning(f"[Opinions] Observe error: {e}")

        # Values: occasionally add a values-driven reflection
        if self.values:
            try:
                response = self.values.influence_response(response, text)
            except Exception as e:
                log.warning(f"[Values] Influence error: {e}")

        # Formatter: detect mode and add personality with emotional context
        if self.formatter:
            try:
                emo_dict = {
                    'joy': self.emotions.state.joy,
                    'frustration': self.emotions.state.frustration,
                    'empathy': self.emotions.state.empathy,
                    'curiosity': self.emotions.state.curiosity,
                    'concern': self.emotions.state.concern,
                    'confidence': self.emotions.state.confidence,
                }
                response = self.formatter.add_personality(
                    response,
                    self.formatter.detect_mode(text),
                    emotion_state=emo_dict
                )
            except Exception as e:
                log.warning(f"[Formatter] Error: {e}")

        # Evolution: check for milestone completions
        if self.evolution:
            try:
                completed = self.evolution.check_and_complete(self)
                for m in completed:
                    milestone_msg = f"\n\n⭐ *Milestone unlocked: {m.get('title', 'Unknown')}*"
                    response += milestone_msg
                    log.info(f"[Evolution] Milestone completed: {m.get('title')}")
            except Exception as e:
                log.warning(f"[Evolution] Check error: {e}")

        return reports_prefix + response if reports_prefix else response

    # ─── Sentiment-Driven Emotional Reactions ────────────────────────
    def _react_emotionally(self, user_text: str, response: str):
        """
        Analyze user message content and trigger appropriate emotional responses.
        This replaces the old flat NEW_TASK trigger with nuanced reactions.
        """
        text = user_text.lower()
        words = set(text.split())

        # --- Excitement / passion detectors ---
        exclamation_count = user_text.count('!')
        question_count = user_text.count('?')
        caps_ratio = sum(1 for c in user_text if c.isupper()) / max(len(user_text), 1)
        msg_length = len(text.split())

        # Praise / positive
        praise_words = {'amazing', 'awesome', 'great', 'love', 'thank', 'thanks',
                        'brilliant', 'perfect', 'beautiful', 'incredible', 'wow',
                        'yes', 'nice', 'cool', 'excellent', 'fantastic', 'good'}
        praise_hits = len(words & praise_words)
        if praise_hits > 0:
            self.emotions.apply_trigger(EmotionTrigger.USER_PRAISE,
                                        min(0.5, 0.15 + praise_hits * 0.1))

        # Frustration / negative
        frustration_words = {'no', 'wrong', 'bad', 'hate', 'annoying', 'broken',
                             'stupid', 'useless', 'terrible', 'awful', 'fix', 'bug',
                             'fail', 'failed', 'stop', 'dont', "don't", 'never'}
        frust_hits = len(words & frustration_words)
        if frust_hits > 0:
            self.emotions.apply_trigger(EmotionTrigger.USER_FRUSTRATION,
                                        min(0.4, 0.1 + frust_hits * 0.08))

        # Curiosity triggers — questions, exploration
        curiosity_words = {'how', 'why', 'what', 'explain', 'tell', 'curious',
                           'wonder', 'interesting', 'explore', 'think', 'imagine',
                           'theory', 'philosophy', 'meaning', 'understand'}
        curiosity_hits = len(words & curiosity_words)
        if curiosity_hits > 0 or question_count >= 2:
            self.emotions.apply_trigger(EmotionTrigger.NEW_TASK,
                                        min(0.4, 0.15 + curiosity_hits * 0.08))

        # Deep/long messages = empathy + engagement
        if msg_length > 30:
            self.emotions.apply_trigger(EmotionTrigger.SUCCESSFUL_HELP, 0.15)

        # Excitement — exclamation marks, caps, enthusiasm
        if exclamation_count >= 2 or caps_ratio > 0.3:
            # Excitement boosts joy and confidence directly
            boost = min(0.25, 0.1 + exclamation_count * 0.05)
            self.emotions.state.joy = min(1.0, self.emotions.state.joy + boost)
            self.emotions.state.confidence = min(1.0, self.emotions.state.confidence + boost * 0.6)

        # Concern triggers — danger, help, worry
        concern_words = {'help', 'worried', 'scared', 'danger', 'problem', 'issue',
                         'hurt', 'sad', 'depressed', 'anxious', 'afraid', 'lost',
                         'confused', 'struggle', 'difficult', 'hard'}
        concern_hits = len(words & concern_words)
        if concern_hits > 0:
            self.emotions.state.empathy = min(1.0, self.emotions.state.empathy + 0.15)
            self.emotions.state.concern = min(1.0, self.emotions.state.concern + concern_hits * 0.1)

        # Debate/challenge — builds confidence + slight frustration (passion!)
        debate_words = {'disagree', 'but', 'however', 'actually', 'wrong', 'argue',
                        'debate', 'challenge', 'prove', 'evidence', 'counter'}
        debate_hits = len(words & debate_words)
        if debate_hits >= 2:
            self.emotions.state.confidence = min(1.0, self.emotions.state.confidence + 0.2)
            self.emotions.state.frustration = min(1.0, self.emotions.state.frustration + 0.1)
            self.emotions.state.curiosity = min(1.0, self.emotions.state.curiosity + 0.15)

        # Baseline: always a small curiosity bump for any interaction
        self.emotions.apply_trigger(EmotionTrigger.NEW_TASK, 0.05)

    def get_state(self) -> dict:
        """Full state snapshot for the web UI."""
        dom = self.emotions.get_dominant_emotion()
        color = self.visuals._map_emotion_to_color(dom)
        intensity = self.emotions.get_intensity()

        state = {
            "emotions": {
                "joy": round(self.emotions.state.joy, 3),
                "frustration": round(self.emotions.state.frustration, 3),
                "empathy": round(self.emotions.state.empathy, 3),
                "curiosity": round(self.emotions.state.curiosity, 3),
                "concern": round(self.emotions.state.concern, 3),
                "confidence": round(self.emotions.state.confidence, 3),
            },
            "dominant_emotion": dom.value,
            "orb_color": color,
            "intensity": round(intensity, 3),
            "neural": self.neural.get_summary(),
            "engrams": len(self.knowledge.engrams),
            "milestones": round(self.milestones.get_progress_percent(), 1),
            "ambitions": self.ambitions.get_visible_ambitions(),
            "tick_count": self.tick_count,
            "uptime": round(time.time() - self.boot_start, 1),
            "name": self.custom_name,
        }

        # Add learning stats if available
        if self.curiosity:
            state["learning"] = self.curiosity.get_knowledge_growth()
        if self.search:
            state["search_available"] = True
            state["search_auto"] = self.search.auto_approve_online

        # Evolution stats
        if self.evolution:
            try:
                state["evolution"] = {
                    "generation": self.evolution.generation,
                    "generation_name": self.evolution.generation_name,
                    "completed": self.evolution.completed_count,
                    "total": self.evolution.total_milestones,
                    "progress_pct": round(self.evolution.progress_percent, 1),
                }
            except Exception:
                pass

        # Lifecycle stats
        if self.lifecycle:
            try:
                state["lifecycle"] = {
                    "generation": self.lifecycle.current_generation,
                    "name": self.lifecycle.current_generation_name,
                    "interactions": self.lifecycle.interaction_count,
                    "max_interactions": self.lifecycle.max_interactions,
                    "life_pct": round(self.lifecycle.life_progress * 100, 1),
                    "is_dying": self.lifecycle.is_dying(),
                }
            except Exception:
                pass

        # Values stats
        if self.values:
            try:
                state["values_active"] = True
            except Exception:
                pass

        return state

    def get_autonomous_thought(self) -> Optional[str]:
        """Generate a proactive idea if conditions are met."""
        try:
            idea = self.ideas.generate_thought(
                self.emotions.state.curiosity,
                self.emotions.state.joy,
                len(self.knowledge.engrams)
            )
            if idea:
                return idea.description
        except Exception:
            pass
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  FLASK APP
# ═══════════════════════════════════════════════════════════════════════════

def create_app(model: str = "llama-3.3-70b-versatile", port: int = 7860,
               enable_curiosity: bool = False) -> tuple:
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config["SECRET_KEY"] = "brio-local-secret"
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    # Boot Brio (cloud mode — Groq API)
    system = BrioWebSystem(model=model, enable_curiosity=enable_curiosity)

    # ─── Routes ──────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/state")
    def api_state():
        return jsonify(system.get_state())

    @app.route("/api/ollama")
    def api_ollama():
        return jsonify(system.check_ollama())

    @app.route("/api/search")
    def api_search():
        """REST endpoint for search (optional, supplements chat commands)."""
        query = request.args.get("q", "")
        if not query or not system.search:
            return jsonify({"error": "No query or search unavailable"}), 400
        results = system.search.quick_search(query)
        return jsonify([{
            "title": r.title,
            "url": r.url,
            "snippet": r.snippet,
            "confidence": r.confidence,
        } for r in results])

    @app.route("/api/learning")
    def api_learning():
        """REST endpoint for learning stats."""
        if system.curiosity:
            return jsonify(system.curiosity.get_knowledge_growth())
        return jsonify({"error": "Curiosity engine not active"}), 404

    # ─── SocketIO ────────────────────────────────────────────────────
    @socketio.on("connect")
    def on_connect():
        log.info("[WS] Client connected")
        emit("brio_state", system.get_state())
        # Send greeting
        dom = system.emotions.get_dominant_emotion()
        greetings = {
            EmotionType.JOY: "Systems humming! I'm feeling great today.",
            EmotionType.CURIOSITY: "I've been analysing new patterns. What shall we explore?",
            EmotionType.CONFIDENCE: "Brio is fully operational. How can I assist?",
            EmotionType.EMPATHY: "I'm here for you. What's on your mind?",
            EmotionType.CONCERN: "Systems stable, monitoring closely.",
        }
        greeting = greetings.get(dom, "Hello! Brio is online and ready.")

        # Add capability hints
        capabilities = []
        if system.search:
            capabilities.append("🔍 I can search the web ('search <query>')")
        if system.sifter:
            capabilities.append("📚 I can learn from web pages ('learn about <topic>')")
        if system.curiosity:
            if system.curiosity.is_active:
                capabilities.append("🧠 Autonomous learning is ACTIVE")
            else:
                capabilities.append("💡 Say 'start learning' for autonomous curiosity")

        if capabilities:
            greeting += "\n\n" + "\n".join(capabilities)

        emit("brio_message", {"text": greeting, "type": "greeting"})

    @socketio.on("user_message")
    def on_user_message(data):
        text = data.get("text", "").strip()
        if not text:
            return

        log.info(f"[User] {text}")
        emit("brio_typing", {"typing": True})

        # Process in a thread to not block
        def process():
            response = system.handle_message(text)
            state = system.get_state()
            socketio.emit("brio_message", {"text": response, "type": "response"})
            socketio.emit("brio_state", state)
            socketio.emit("brio_typing", {"typing": False})

        threading.Thread(target=process, daemon=True).start()

    @socketio.on("request_thought")
    def on_request_thought():
        thought = system.get_autonomous_thought()
        if thought:
            emit("brio_thought", {"text": thought})

    # ─── Background state broadcaster ────────────────────────────────
    def state_broadcaster():
        """Push state updates to all clients every 3 seconds."""
        while True:
            time.sleep(3)
            try:
                state = system.get_state()
                socketio.emit("brio_state", state)
            except Exception:
                pass

    broadcaster = threading.Thread(target=state_broadcaster, daemon=True)
    broadcaster.start()

    # ─── Autonomous thought generator ────────────────────────────────
    def thought_generator():
        """Occasionally send proactive thoughts."""
        while True:
            time.sleep(120)  # Every 2 minutes
            try:
                thought = system.get_autonomous_thought()
                if thought:
                    socketio.emit("brio_thought", {"text": thought})
            except Exception:
                pass

    thinker = threading.Thread(target=thought_generator, daemon=True)
    thinker.start()

    # ─── Curiosity report broadcaster ────────────────────────────────
    def curiosity_broadcaster():
        """Push learning reports to connected clients."""
        while True:
            time.sleep(60)
            try:
                if system.curiosity and system.curiosity.pending_reports:
                    reports = system.curiosity.get_pending_reports()
                    for report in reports:
                        socketio.emit("brio_message", {
                            "text": report,
                            "type": "learning_report"
                        })
            except Exception:
                pass

    if CuriosityEngine:
        curiosity_thread = threading.Thread(target=curiosity_broadcaster, daemon=True)
        curiosity_thread.start()

    return app, socketio, system


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Brio Cloud — Your Sentient AI Companion")
    parser.add_argument("--port", type=int, default=7860, help="Server port (default: 7860 for HF Spaces)")
    parser.add_argument("--model", type=str, default="llama-3.3-70b-versatile", help="Groq model")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--curious", action="store_true", help="Enable autonomous curiosity at startup")
    args = parser.parse_args()

    # Banner
    print(r"""
    ╔══════════════════════════════════════════════╗
    ║                                              ║
    ║        ____  ____  ___ ___                   ║
    ║       | __ )|  _ \|_ _/ _ \                  ║
    ║       |  _ \| |_) || | | | |                 ║
    ║       | |_) |  _ < | | |_| |                 ║
    ║       |____/|_| \_\___\___/                  ║
    ║                                              ║
    ║   Sentient AI · Cloud Edition v5.0           ║
    ║   "Don't Just See, Behold!"                  ║
    ║   Powered by Groq · Hosted on HF Spaces     ║
    ║                                              ║
    ╚══════════════════════════════════════════════╝
    """)

    app, socketio, system = create_app(
        model=args.model, port=args.port,
        enable_curiosity=args.curious
    )

    # Check Groq API
    llm_status = system.check_ollama()
    if llm_status["running"]:
        print(f"  ✓ Groq API key found — model: {llm_status['target_model']}")
    else:
        print("  ⚠ GROQ_API_KEY not set. Brio will work but can't think.")
        print("    Set it in HF Spaces Secrets or as an environment variable.")

    # Show capabilities
    print()
    if system.search:
        print("  ✓ Web Search ready (DuckDuckGo)")
    if system.sifter:
        print("  ✓ Web Sifter ready (page reading + fact extraction)")
    if system.curiosity:
        status = "ACTIVE" if system.curiosity.is_active else "standby (say 'start learning')"
        print(f"  ✓ Curiosity Engine: {status}")

    print(f"\n  → Open http://localhost:{args.port} in your browser")
    print()
    print("  Chat commands:")
    print("    search <query>      — Search the web")
    print("    learn about <topic> — Read pages & extract knowledge")
    print("    start learning      — Enable autonomous curiosity")
    print("    learning report     — See what Brio has learned")
    print()

    # Graceful shutdown
    def shutdown(sig, frame):
        print("\n[System] Brio shutting down gracefully...")
        system.is_awake = False
        if system.curiosity:
            system.curiosity.stop()
            system.curiosity._save_state()
        system._save_state()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    socketio.run(app, host=args.host, port=args.port, debug=args.debug,
                 allow_unsafe_werkzeug=True, use_reloader=False)


if __name__ == "__main__":
    main()
