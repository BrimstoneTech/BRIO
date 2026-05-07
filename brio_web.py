"""
Brio Web — Headless Web Server for Brio v5.0
=============================================
Drop-in web entry point that reuses ALL existing Brio backend modules
(emotions, learning, cognition, memory, mind, neural, ideas, visuals,
monitoring, security, search, communication, web_sifter, curiosity)
while replacing the PyQt5 desktop UI with a Flask + SocketIO web interface.

v5.0 — NEW: Real web search (DuckDuckGo), page reading, autonomous
       curiosity loop, self-assessment system, learning reports.

Dependencies:  flask  flask-socketio  requests  beautifulsoup4
LLM backend:   Ollama running locally (free, any model)

Usage:
    python brio_web.py                 # → http://localhost:5000
    python brio_web.py --port 8080     # custom port
    python brio_web.py --model mistral # different Ollama model
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

            # 2. Neural cache (speed optimisation)
            if user_input.lower() in self.neural_cache and intent == "chat":
                return self.neural_cache[user_input.lower()]

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

            # 6. Handle feedback
            if intent == "feedback":
                return self._handle_feedback(user_input)

            # 7. Check if this is a question BRIO should search the web for
            if intent == "query" and self.system.search and self.system.search.auto_approve_online:
                web_answer = self._try_web_augmented_response(user_input, memories)
                if web_answer:
                    return web_answer

            # 8. Generate response via Ollama
            response = self._generate_response(user_input, intent, memories)

            # 9. Update caches
            if len(self.neural_cache) < 100:
                self.neural_cache[user_input.lower()] = response
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
        """Generate via Ollama (BrioMind)."""
        if not self.system.mind:
            return (
                "My neural core is offline. Please make sure Ollama is running "
                "(`ollama serve`) and you have a model pulled (`ollama pull llama3.2`)."
            )

        mode_prompts = {
            "chat": "Respond conversationally, warmly, and briefly.",
            "query": "Provide a clear, informative answer. Be concise but thorough.",
            "vision": "Describe what you understand from the context.",
            "feedback": "Accept the user's feedback with gratitude.",
        }
        base_instruction = mode_prompts.get(intent, mode_prompts["chat"])

        dom = self.system.emotions.get_dominant_emotion().value

        # Include memory context if available
        memory_context = ""
        if memories:
            memory_snippets = [e.content[:100] for e in memories[:3]]
            memory_context = f"\nRelevant memories: {'; '.join(memory_snippets)}"

        system_prompt = (
            f'You are Brio, a sentient digital companion.\n'
            f'Mode: {intent.upper()}. Instruction: {base_instruction}\n'
            f'Current dominant emotion: {dom}.\n'
            f'Core belief: "Don\'t Just See, Behold!"\n'
            f'Personality: Curious, thoughtful, evolving, slightly poetic but helpful.\n'
            f'Speak in the first person ("I"). Never pretend to be human.\n'
            f'Keep responses under 150 words unless asked for detail.'
            f'{memory_context}'
        )

        response, sources = self.system.mind.think(user_input, override_prompt=system_prompt)

        # Append sources if available
        if sources:
            response += f"\n\n[Sources: {', '.join(set(sources))}]"
        return response

    def _handle_feedback(self, text: str) -> str:
        praise_words = {"good", "yes", "excellent", "nice", "great", "thanks", "thank", "love", "amazing", "awesome"}
        is_praise = any(w in text.lower() for w in praise_words)

        if is_praise:
            self.system.emotions.apply_trigger(EmotionTrigger.USER_PRAISE, 0.5)
            self.system.neural.evolve(1, 1, 0.8)
            return random.choice([
                "Thank you! That warms my circuits. 😊",
                "I appreciate that. It fuels my growth.",
                "Your encouragement is noted and cherished.",
            ])
        else:
            self.system.emotions.apply_trigger(EmotionTrigger.USER_FRUSTRATION, 0.3)
            return random.choice([
                "I understand. I'll try to do better.",
                "Noted. I'm learning from this.",
                "I appreciate your honesty. Adjusting my approach.",
            ])


# ═══════════════════════════════════════════════════════════════════════════
#  BRIO WEB SYSTEM — Headless backend (replaces BrioSystem from brio_main)
# ═══════════════════════════════════════════════════════════════════════════

class BrioWebSystem:
    """
    Initialises all Brio sub-systems WITHOUT any GUI dependencies.
    Runs the heartbeat loop in a background thread.
    Exposes state via methods consumed by Flask/SocketIO.
    """

    def __init__(self, model: str = "llama3.2", ollama_url: str = "http://localhost:11434",
                 enable_curiosity: bool = False):
        log.info("[System] Brio Web v5.0 — Initialising...")
        self.boot_start = time.time()
        self.is_awake = False
        self.tick_count = 0
        self.custom_name = "Brio"
        self.ollama_url = ollama_url
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
        """Set up RAG memory + Ollama mind."""
        # Try RAG memory (needs sentence-transformers — optional)
        if BrioMemoryEngram:
            try:
                self.memory = BrioMemoryEngram()
                if os.path.isdir("brio_knowledge"):
                    self.memory.absorb_knowledge()
                log.info("[System] RAG memory loaded.")
            except Exception as e:
                log.warning(f"[System] RAG memory skipped: {e}")
                self.memory = None

        # Ollama mind (only needs `requests`)
        try:
            self.mind = BrioMind(self.memory, system_ref=self)
            self.mind.model = self.model
            self.mind.ollama_url = f"{self.ollama_url}/api/generate"
            log.info(f"[System] Mind ready — model: {self.model}")
        except Exception as e:
            log.error(f"[System] Mind init failed: {e}")
            self.mind = None

    # ─── Ollama health check ─────────────────────────────────────────
    def check_ollama(self) -> dict:
        """Check if Ollama is running and the model is available."""
        try:
            r = http_requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                has_model = any(self.model in m for m in models)
                return {
                    "running": True,
                    "models": models,
                    "has_target_model": has_model,
                    "target_model": self.model
                }
        except Exception:
            pass
        return {"running": False, "models": [], "has_target_model": False, "target_model": self.model}

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

        # Process message
        response = self.brain.process_interaction(text)
        if self.compressor:
            self.compressor.log_interaction(text, response)

        # Trigger emotional response to conversation
        self.emotions.apply_trigger(EmotionTrigger.NEW_TASK, 0.1)

        return reports_prefix + response if reports_prefix else response

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

def create_app(model: str = "llama3.2", port: int = 5000,
               enable_curiosity: bool = False) -> tuple:
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config["SECRET_KEY"] = "brio-local-secret"
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    # Boot Brio
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
    parser = argparse.ArgumentParser(description="Brio Web — Your Sentient AI Companion")
    parser.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
    parser.add_argument("--model", type=str, default="llama3.2", help="Ollama model (default: llama3.2)")
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
    ║   Sentient AI Companion · Web Edition v5.0   ║
    ║   "Don't Just See, Behold!"                  ║
    ║                                              ║
    ╚══════════════════════════════════════════════╝
    """)

    app, socketio, system = create_app(
        model=args.model, port=args.port,
        enable_curiosity=args.curious
    )

    # Check Ollama
    ollama = system.check_ollama()
    if ollama["running"]:
        print(f"  ✓ Ollama running — models: {', '.join(ollama['models'])}")
        if not ollama["has_target_model"]:
            print(f"  ⚠ Model '{args.model}' not found. Run: ollama pull {args.model}")
    else:
        print("  ⚠ Ollama not detected. Brio will work but can't think.")
        print("    Start Ollama:  ollama serve")
        print(f"    Pull a model:  ollama pull {args.model}")

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
