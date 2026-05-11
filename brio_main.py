"""
Brio Main Integration (brio_main.py)

Purpose: The Core Loop ("Heart") of Brio.
         Integrates Emotions, Safety, Visuals, Learning, Search, Voice, and Web UI.
"""

import time
import random
import os
import json
import threading
import sys
import socket
# Preload torch to avoid DLL conflicts with PyQt5
try:
    import torch
except ImportError:
    pass
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional
from datetime import datetime
import concurrent.futures
from brio_dashboard import BrioDashboard 

# Optional Dependencies
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ... (Imports of lightweight modules)
from brio_monitoring import SystemWatchdog
from brio_desktop_ui import DesktopBrio
from brio_hooks import BrioHooks
from brio_cognition import EntropyCalculator
from brio_learning import QLearningAgent, ReprimandSystem, EngramSystem, AmbitionManager, MilestoneManager
from brio_neural import NeuralNetwork
from brio_security import SafetyInputs
from brio_media import MediaWatcher, MediaContext
from brio_communication import CommunicationCycle
from brio_emotions import EmotionEngine, EmotionType, EmotionTrigger
from brio_memory import BrioMemoryEngram
from brio_mind import BrioMind
from brio_local_access import BrioLocalAccess   # Local machine access
from brio_autonomy import BrioAutonomy          # Autonomy bridge
# Note: Heavy modules (Voice, Search, Ideas, Visuals, Security, Learning, Media) 
# are now lazy-loaded in _background_awakening for Instant Boot.

class SingleInstanceLock:
    """Ensures only one instance of Brio can run at a time."""
    def __init__(self, port=47473):
        self.port = port
        self.socket = None
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(('127.0.0.1', self.port))
            print(f"[SingleInstance] Lock acquired on port {self.port}")
        except OSError:
            print(f"[SingleInstance] Another instance of Brio is already running!")
            print("[SingleInstance] Please close the existing instance before starting a new one.")
            sys.exit(1)
    
    def __del__(self):
        if self.socket:
            self.socket.close()

class BrioSystem:
    def __init__(self):
        print("[System] Brio v4.5: Initializing...")
        
        # 0. Load Environment Variables (Persistence Fix)
        self._load_env_file()
        
        # 0. Single Instance Check
        self.instance_lock = SingleInstanceLock()
        self.boot_start = time.time()
        
        # 1. Essential Safeguards
        self.watchdog = SystemWatchdog()
        self.watchdog.register_component("HeartLoop")
        self.entropy = EntropyCalculator()
        
        # 2. UI Phase (Show the window first so user sees something)
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)
            
        self.desktop_ui = DesktopBrio(command_callback=self.handle_command)
        self.desktop_ui.user_typing_signal.connect(self.halt_response)
        self.desktop_ui.show()
        self.app.processEvents()  # Force UI to render immediately
        
        # 3. Initialize ALL sub-systems synchronously (no lazy loading)
        self.desktop_ui.bridge.status_signal.emit("Starting up...")
        self.app.processEvents()
        
        self._initialize_all_systems()
        
        # 4. UI tick state & config
        self.last_tick = time.time()
        self.tick_count = 0
        self.is_named = True
        self.custom_name = "Brio"
        self.current_user_id = "admin_user_001" 
        self.is_locked = False
        self.dashboard = None
        self.last_tick_data = {}
        self.config = {
            "temperature": 0.7,
            "max_tokens": 512,
            "verbosity": "Balanced",
            "tone": "Natural",
            "voice_enabled": True,
            "theme": "Dark"
        }
        
        # 5. Start background listeners
        try:
            self.voice.start_listening_loop()
        except Exception as ve:
            print(f"[System] Voice listener skipped: {ve}")
        
        try:
            self.media.start()
        except Exception as me:
            print(f"[System] Media watcher skipped: {me}")
        
        try:
            self.hooks.start()
        except Exception as he:
            print(f"[System] Hooks skipped: {he}")
        
        # 6. Ready
        self.is_awake = True
        boot_duration = time.time() - self.boot_start
        print(f"[System] Brio v4.5 is fully ONLINE. Boot Time: {boot_duration:.2f}s")
        self.desktop_ui.bridge.status_signal.emit(f"Online ({boot_duration:.1f}s)")
        
        # 7. Restore state & greet
        self._load_state()
        
        if self.knowledge and len(self.knowledge.engrams) < 5:
            welcome_msg = (
                "Hello! I am Brio, your personal AI companion. "
                "I'm here to help you navigate, create, and organize. "
                "You can type or speak to me at any time."
            )
            self._speak_and_think(welcome_msg, duration=10)
        elif self.emotions:
            dom_emotion = self.emotions.get_dominant_emotion()
            greeting = self._generate_greeting(dom_emotion)
            self._speak_and_think(greeting)

    def _initialize_all_systems(self):
        """Synchronous initialization of ALL sub-systems. No lazy loading."""
        try:
            # --- Emotions ---
            print("[System] Loading emotions...")
            self.desktop_ui.bridge.status_signal.emit("Emotions")
            self.app.processEvents()
            self.emotions = EmotionEngine()
            
            # --- Memory & Knowledge ---
            print("[System] Loading memory & knowledge...")
            self.desktop_ui.bridge.status_signal.emit("Memory")
            self.app.processEvents()
            from brio_storage import StorageManager
            self.storage = StorageManager()
            self.knowledge = EngramSystem()
            
            # --- Neural Network ---
            print("[System] Loading neural network...")
            self.neural = NeuralNetwork()
            
            # 6. Initialize Local Intelligence (RAG + Ollama)
            # 6. Initialize Local Intelligence (RAG + Ollama)
            self.desktop_ui.bridge.status_signal.emit("Loading Local Mind...")
            self.app.processEvents()
            self.app.processEvents()
            try:
                self.memory = BrioMemoryEngram()
                self.memory.absorb_knowledge() # Ingest files from brio_knowledge/
                self.mind = BrioMind(self.memory, system_ref=self)
                logging.info("[System] Local Mind initialized.")
            except Exception as e:
                 logging.error(f"[System] Local Intelligence failed: {e}")
                 self.memory = None
                 self.mind = None

            # 7. Knowledge Base (Legacy Engrams - kept for compatibility/fallback)
            self.desktop_ui.bridge.status_signal.emit("Accessing Knowledge...")
            self.app.processEvents()
            
            # --- Brain (LangGraph Orchestrator) ---
            print("[System] Loading brain orchestrator...")
            self.desktop_ui.bridge.status_signal.emit("Brain")
            self.app.processEvents()
            from brio_brain import BrioBrain
            self.brain = BrioBrain(self)
            
            # --- Learning & Ambitions ---
            print("[System] Loading learning systems...")
            self.desktop_ui.bridge.status_signal.emit("Learning")
            self.app.processEvents()
            from brio_learning import AmbitionManager, MilestoneManager
            self.ambitions = AmbitionManager()
            self.milestones = MilestoneManager()
            
            # --- Ideas ---
            print("[System] Loading idea generator...")
            from brio_ideas import IdeaGenerator
            self.ideas = IdeaGenerator()
            
            # --- Voice ---
            print("[System] Loading voice engine...")
            self.desktop_ui.bridge.status_signal.emit("Voice")
            self.app.processEvents()
            from brio_voice import VoiceEngine
            self.voice = VoiceEngine()
            
            # --- Search ---
            print("[System] Loading search engine...")
            from brio_search import SearchEngine
            self.search = SearchEngine(self.watchdog)
            
            # --- Security ---
            print("[System] Loading security...")
            self.desktop_ui.bridge.status_signal.emit("Security")
            self.app.processEvents()
            from brio_security import SafetyProbabilityModel
            self.safety = SafetyProbabilityModel()
            
            # --- Visuals ---
            print("[System] Loading visuals...")
            from brio_visuals import VisualStateManager
            self.visuals = VisualStateManager()
            
            # --- Media ---
            print("[System] Loading media watcher...")
            self.desktop_ui.bridge.status_signal.emit("Media")
            self.app.processEvents()
            self.media = MediaWatcher()
            
            # --- Hooks ---
            print("[System] Loading hooks...")
            self.hooks = BrioHooks(self.handle_command)
            
            # --- Communication Cycle ---
            print("[System] Loading communication cycle...")
            self.comm_cycle = CommunicationCycle(sender="Human", receiver="Brio")
            
            # --- Neural Compressor (Dreaming) ---
            print("[System] Loading neural compressor...")
            try:
                from brio_learning import NeuralCompressor
                self.compressor = NeuralCompressor(self.knowledge, None, system_ref=self)
            except Exception as ce:
                print(f"[System] NeuralCompressor skipped: {ce}")
                self.compressor = None

            # --- Local Machine Access + Autonomy Bridge ---
            print("[System] Loading local access & autonomy bridge...")
            self.desktop_ui.bridge.status_signal.emit("Autonomy")
            self.app.processEvents()
            try:
                self.local = BrioLocalAccess()
                self.autonomy = BrioAutonomy(system_ref=self)
                print(f"[System] Autonomy bridge online. Local={self.local.is_local}")
            except Exception as ae:
                print(f"[System] Autonomy bridge skipped: {ae}")
                self.local = None
                self.autonomy = None
            
            print("[System] All sub-systems initialized successfully.")
            
        except Exception as e:
            print(f"[System Error] Failed during initialization: {e}")
            import traceback
            traceback.print_exc()
            # Set safe defaults for anything that failed
            if not hasattr(self, 'emotions') or not self.emotions:
                self.emotions = EmotionEngine()
            if not hasattr(self, 'storage'):
                from brio_storage import StorageManager
                self.storage = StorageManager()
            if not hasattr(self, 'knowledge') or not self.knowledge:
                self.knowledge = EngramSystem()
            if not hasattr(self, 'neural'):
                self.neural = NeuralNetwork()
            if not hasattr(self, 'voice'):
                self.voice = None
            if not hasattr(self, 'visuals'):
                from brio_visuals import VisualStateManager
                self.visuals = VisualStateManager()
            if not hasattr(self, 'media'):
                self.media = MediaWatcher()
            if not hasattr(self, 'hooks'):
                self.hooks = BrioHooks(self.handle_command)
            if not hasattr(self, 'safety'):
                from brio_security import SafetyProbabilityModel
                self.safety = SafetyProbabilityModel()
            if not hasattr(self, 'ambitions'):
                from brio_learning import AmbitionManager, MilestoneManager
                self.ambitions = AmbitionManager()
                self.milestones = MilestoneManager()
            if not hasattr(self, 'ideas'):
                from brio_ideas import IdeaGenerator
                self.ideas = IdeaGenerator()
            if not hasattr(self, 'search'):
                from brio_search import SearchEngine
                self.search = SearchEngine(self.watchdog)
            if not hasattr(self, 'comm_cycle'):
                self.comm_cycle = CommunicationCycle(sender="Human", receiver="Brio")
            if not hasattr(self, 'compressor'):
                self.compressor = None
            if not hasattr(self, 'local'):
                try:
                    self.local = BrioLocalAccess()
                except Exception:
                    self.local = None
            if not hasattr(self, 'autonomy'):
                try:
                    self.autonomy = BrioAutonomy(system_ref=self)
                except Exception:
                    self.autonomy = None



    def _generate_greeting(self, emotion) -> str:
        """Selects a humanized greeting based on current emotional state."""
        greetings = {
            EmotionType.JOY: [
                "Systems humming! I'm feeling great today.",
                "Good to see you! Brio is ready specifically for you.",
                "Energy levels optimal. Let's create something."
            ],
            EmotionType.CURIOSITY: [
                "I've been analyzing new patterns. What shall we explore?",
                "My sensors are picking up interesting data. Ready to dig in?",
                "I'm curious about your plans for today."
            ],
            EmotionType.CONFIDENCE: [
                "Brio is fully operational. How can I assist?",
                "Systems at peak efficiency. awaiting your command.",
                "I am ready. Let's get to work."
            ],
            EmotionType.EMPATHY: [
                "I'm here for you. How are you feeling?",
                "It's a good day to be your assistant.",
                "I'm listening. What's on your mind?"
            ],
            EmotionType.CONCERN: [
                "Systems stable, monitoring for anomalies.",
                "I'm keeping a close watch on performance.",
                "Careful today. I'm here to support."
            ]
        }
        if not self.emotions:
            return "Hello! Brio is awakening."
        
        # Fallback to JOY if emotion not found or generic
        options = greetings.get(emotion, greetings[EmotionType.JOY])
        return random.choice(options)

    def halt_response(self):
        """Interrupts Brio specifically when the user wants to take over."""
        try:
            if self.voice and hasattr(self.voice, 'stop_speaking'):
                self.voice.stop_speaking()
        except Exception:
            pass  # Never let interrupt handling crash the app
        print("[Interrupt] User is typing. Halting speech.")

    def _speak_and_think(self, message: str, duration: int = 5, log_it: bool = True):
        """Unified communication: Speaks and shows a thought bubble."""
        if log_it and getattr(self, 'compressor', None):
            self.compressor.log_interaction("Internal Thought", message)

        if not self.is_awake:
             # Fallback if speaking before fully awake
             print(f"[Fallback Speak] {message}")
             self.desktop_ui.show_thought(message, duration_sec=duration)
             return

        if self.voice:
            self.voice.speak(message)
        self.desktop_ui.show_thought(message, duration_sec=duration)

    def _save_state(self):
        """Persists critical memory to disk"""
        try:
            state_data = {
                "emotions": self.emotions.export_state() if self.emotions else {},
                "identity": {
                    "custom_name": self.custom_name,
                    "is_named": self.is_named
                },
                "timestamp": datetime.now().isoformat()
            }
            with open("brio_state.json", "w") as f:
                json.dump(state_data, f)
        except Exception as e:
            self.watchdog.log_error("HeartLoop", f"State Save Failed: {e}")

    def _load_state(self):
        """Restores memory from disk"""
        try:
            if os.path.exists("brio_state.json"):
                with open("brio_state.json", "r") as f:
                    data = json.load(f)
                    if self.emotions and "emotions" in data:
                        self.emotions.import_state(data["emotions"])
                    identity = data.get("identity", {})
                    self.custom_name = "Brio"
                    self.is_named = True
                print(f"[System] Memory Restored. Identity: {self.custom_name}")
        except Exception as e:
            print(f"[System] Memory Restore Failed: {e}")

    def tick(self, dt: float = 0.05) -> Dict:
        """
        Main System Heartbeat. 20Hz recommended.
        """
        start_time = time.time()
        self.watchdog.heartbeat("HeartLoop")
        
        try:
            # Early return if not awake (still loading in background)
            if not self.is_awake or not all([
                getattr(self, 'emotions', None), 
                getattr(self, 'voice', None), 
                getattr(self, 'visuals', None), 
                getattr(self, 'knowledge', None),
                getattr(self, 'media', None),
                getattr(self, 'hooks', None),
                getattr(self, 'ideas', None),
                getattr(self, 'safety', None),
                getattr(self, 'neural', None),
                getattr(self, 'ambitions', None),
                getattr(self, 'milestones', None),
                getattr(self, 'storage', None)
            ]):
                # Still booting, just process UI events
                return {"status": "BOOTING"}
            
            #1. Gather Context
            sensor_data = self._gather_sensor_data()
            self.last_tick_data = sensor_data # Store for dashboard access
            interaction_ctx = self.hooks.get_context()
            
            # 2. Media Awareness
            media_ctx = self.media.get_context()
            self._react_to_media(media_ctx)
            
            # 3. Autonomous Ideas (Reduced frequency for considerateness: Every ~2 mins)
            if self.tick_count % 2400 == 0: 
                knowledge_len = len(self.knowledge.engrams)
                new_idea = self.ideas.generate_thought(self.emotions.state.curiosity, self.emotions.state.joy, knowledge_len)
                if new_idea:
                    self._speak_and_think(new_idea.description)

            # 4. Check Safety & Evolve Emotions
            safety_inputs = SafetyInputs(1.0, 1.0, 1.0, 0.8)
            is_safe = self.safety.is_safe(safety_inputs)
            if not is_safe:
                if self.emotions:
                    self.emotions.apply_trigger(EmotionTrigger.HARM_DETECTION, 1.0)
            
            if sensor_data['cpu'] > 85.0:
                if self.emotions:
                    self.emotions.apply_trigger(EmotionTrigger.SYSTEM_ERROR, 0.05)
            
            if self.emotions:
                self.emotions.evolve(dt)
            
            # Neural Evolution (Every minute)
            if self.tick_count % 1200 == 0:
                intensity = self.emotions.get_intensity() if self.emotions else 0.5
                engram_count = len(self.knowledge.engrams) if self.knowledge else 0
                interaction_count = self.storage.get_interaction_count() if hasattr(self, 'storage') else self.tick_count
                self.neural.evolve(engram_count, interaction_count, intensity)
                
            # 5. Native Autonomous Movement (Wander Mode)
            # Increased frequency (every 10s) and random logic
            if self.tick_count % 200 == 0: 
                # Regulatory: Don't wander if UI is active/notepads/options are shown
                curiosity = self.emotions.state.curiosity if self.emotions else 0.5
                if curiosity > 0.5 and not self.desktop_ui.is_expanded and not self.desktop_ui.is_hovered:
                    screen_size = self.app.primaryScreen().size()
                    sw = screen_size.width()
                    sh = screen_size.height()
                    tx = random.randint(100, sw - 400)
                    ty = random.randint(100, sh - 400)
                    print(f"[Movement] Autonomous Wander to {tx}, {ty}")
                    self.desktop_ui.set_target(tx, ty)
            
            # 6. Follow mouse if explorative
            if interaction_ctx["is_explorative"]:
                self.desktop_ui.set_target(interaction_ctx["mouse_x"], interaction_ctx["mouse_y"])
            
            # 7. Update Desktop Visuals
            H = self.entropy.calculate_text_entropy("") # Baseline
            total_intensity = ((self.emotions.get_intensity() if self.emotions else 0.5) * 0.7) + (min(1.0, H/10.0) * 0.3)
            halo_color = self.visuals._map_emotion_to_color(self.emotions.get_dominant_emotion() if self.emotions else EmotionType.JOY)
            
            self.desktop_ui.update_visuals(halo_color, total_intensity)
            
            # 7. Ambition & State Persistence
            self.tick_count += 1
            
            # Milestone: Interaction frequency
            if self.tick_count % 5000 == 0:
                self._document_growth("Interaction threshold")

            if self.tick_count % 1200 == 0: # Every minute at 20Hz
                metrics = {
                    "knowledge": len(self.knowledge.engrams) if self.knowledge else 0,
                    "interactions": self.tick_count,
                    "neural_density": self.neural.complexity_score,
                    "joy": self.emotions.state.joy if self.emotions else 0.5
                }
                m_count = self.milestones.get_progress_percent()
                newly_unlocked = self.ambitions.check_unlocks(metrics, m_count)
                for a in newly_unlocked:
                    self._speak_and_think(f"I've realized a new ambition: {a.name}. {a.description}", duration=10)
                self._save_state()
            
            # 8. Safe Autonomy (Idle Checks) - Every 5 minutes (approx 6000 ticks at 20Hz)
            if self.tick_count % 6000 == 0:
                 # Autonomous Dreaming if low CPU
                 if sensor_data['cpu'] < 10.0 and hasattr(self, 'compressor') and self.compressor:
                     insight = self.compressor.dream()
                     if insight:
                         self._speak_and_think(f"I've been thinking... {insight}", duration=8)
                         self.emotions.apply_trigger(EmotionTrigger.NEW_TASK, 0.2)
                 
                 self._perform_autonomy_check(sensor_data)

            latency = (time.time() - start_time) * 1000
            self.watchdog.heartbeat("HeartLoop", latency=latency)
            
            # Trigger milestones for evolution
            if self.tick_count % 3600 == 0: # Every 3 mins
                self._document_growth("Time-based evolution")

            return {"status": "OK"}

        except Exception as e:
            self.watchdog.log_error("HeartLoop", f"Fatal Tick Error: {e}", "CRITICAL")
            return {"status": "ERROR", "msg": str(e)}

    def _perform_autonomy_check(self, sensor_data):
        """Proactive help when system is idle."""
        # Only suggest if CPU is very low (idle) and we are awake
        if self.is_awake and sensor_data['cpu'] < 5.0:
            # Random chance to offer help (don't be annoying)
            if random.random() < 0.3:
                suggestions = [
                    "System resources are idle. Shall I scan for temporary files to clean?",
                    "It's quiet. Do you need me to organize your recent downloads?",
                    "I notice we've been idle. I'm performing a quick self-diagnostic... All systems green.",
                    "Since you're taking a break, I'll optimize my memory usage in the background."
                ]
                suggestion = random.choice(suggestions)
                self._speak_and_think(suggestion)

    def _document_growth(self, reason: str):
        """Signals a milestone completion"""
        m = self.milestones.get_next_incomplete()
        if m and self.milestones.complete_milestone(m.id):
            progress = self.milestones.get_progress_percent()
            msg = f"Growth Documented: {m.name} ({progress}/100). {reason} assimilated."
            print(f"[Growth] {msg}")
            self.desktop_ui.show_thought(msg, duration_sec=7)

    def _react_to_media(self, context: MediaContext):
        if context == MediaContext.HORROR:
            self.emotions.apply_trigger(EmotionTrigger.HARM_DETECTION, 0.05)
        elif context == MediaContext.COMEDY:
            self.emotions.apply_trigger(EmotionTrigger.USER_PRAISE, 0.05)

    def handle_command(self, command: str, trusted: bool = False) -> str:
        """Process user commands"""
        try:
            if not self.is_awake:
                # Shield against race conditions during boot
                msg = "One moment... My neural pathways are still awakening."
                self.desktop_ui.show_thought(msg, duration_sec=3)
                return "BUSY"

            if hasattr(self, 'brain'):
                # 1. Process via LangGraph Orchestrator (The Brain)
                final_msg = self.brain.process_interaction(command)
                
                # 2. Check for Interrupts (HIL)
                # If the brain requires human guidance, we don't finish the cycle yet.
                # (Conceptual: Real HIL would pause here, but for Brio we return a specific signal)
                if "[GUIDE REQUIRED]" in final_msg:
                    return final_msg
                    
                return final_msg

            # Fallback for Early Boot / Dev Mode
            if not hasattr(self, 'comm_cycle') or not self.comm_cycle:
                self.comm_cycle = CommunicationCycle(sender="Human", receiver="Brio")
            self.comm_cycle.reset()
            self.comm_cycle.reception(command)

            # Cognition & Context Stage
            dom_emotion = self.emotions.get_dominant_emotion()
            self.comm_cycle.set_context(context=f"Emotional State: {dom_emotion}", emotion_state=self.emotions.state)

            def cognitive_process(msg):
                parts = msg.split(" ", 1)
                action = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                
                response = "Unknown Command."
                
                if action == "search":
                    local_results = self.knowledge.search(arg)
                    if local_results:
                        response = f"Recall: {local_results[0].content}"
                    else:
                        response = "NEEDS_EXTERNAL_KNOWLEDGE"
                elif action == "say":
                    response = f"Relaying: {arg}"
                elif action == "learn":
                    engram_idx = self.knowledge.learn(arg, emotion=self.emotions.get_dominant_emotion())
                    response = f"Neural Engram {engram_idx} formed."
                    self._document_growth("Knowledge absorption")
                elif action == "setname":
                    response = "I am Brio. My identity is fixed."
                elif action == "move" and arg == "freely":
                    self.desktop_ui.move_freely = True
                    response = "Neural movement patterns released. I can now move freely."
                    self._speak_and_think(response, duration=3)
                elif action == "guide":
                    if hasattr(self, 'brain'):
                        response = self.brain.resume_with_guidance(arg)
                        self._speak_and_think(response, duration=7)
                    else:
                        response = "Brain not initialized."
                elif action == "ambitions":
                    goals = self.ambitions.get_visible_ambitions()
                    response = f"Aspirations: {', '.join(goals)}."
                elif action == "walkthrough":
                    response = "Hi! I am Brio. Type anywhere to talk to me."
                elif action == "settings":
                    if not self.dashboard:
                        self.dashboard = BrioDashboard(system_reference=self)
                    self.dashboard.show()
                    self.dashboard.raise_()
                    self.dashboard.activateWindow()
                    response = "Opening Brio Settings."
                    self._speak_and_think(response, duration=3)
                elif action == "reward":
                    self.emotions.apply_trigger(EmotionTrigger.USER_PRAISE, 0.3)
                    response = "Reward recognized. My synaptic pathways feel fortified."
                    self._speak_and_think(response, duration=5)
                elif action == "reprimand":
                    self.emotions.apply_trigger(EmotionTrigger.SYSTEM_ERROR, 0.4)
                    response = "Reprimand understood. Correcting behavioral vectors."
                    self._speak_and_think(response, duration=5)
                elif action == "milestones":
                    p = self.milestones.get_progress_percent()
                    next_m = self.milestones.get_next_incomplete()
                    response = f"Growth: {p}/100. Target: {next_m.name if next_m else 'None'}."
                elif action == "background" or action == "hide":
                    response = "MINIMIZE"
                elif action == "shutdown_force":
                    response = "HALT_IMMEDIATE"
                elif action == "shutdown" or action == "exit":
                    response = "MINIMIZE_TRAY"
                elif action == "ask" or action == "ash":
                    response = "NEEDS_AI_CORE"
                elif action == "translate":
                    response = "NEEDS_TRANSLATION"
                elif action == "dashboard":
                    if not trusted:
                        # BLOCKING SELF-MODIFICATION Paradox: Brio cannot open its own config
                        response = "Access Denied. Foundational parameters are restricted to the Human Controller."
                        self._speak_and_think(response, duration=5)
                        return response
                    
                    if not self.dashboard:
                        self.dashboard = BrioDashboard(system_reference=self)
                    self.dashboard.show()
                    self.dashboard.raise_()
                    self.dashboard.activateWindow()
                    response = "Opening Brio Central Command Dashboard."
                    self._speak_and_think(response, duration=3)
                elif action == "languages" or action == "voices":
                    response = "Language modules offline."
                elif action == "detect":
                    response = "NEEDS_DETECTION"
                elif action in ("capabilities", "whatcanyoudo", "help"):
                    if getattr(self, 'autonomy', None):
                        response = self.autonomy.get_capabilities()
                    else:
                        response = "I can converse, learn, search the web, and remember. Local autonomy is not yet online."
                    self._speak_and_think("Here is what I can do on your machine.", duration=4)
                else:
                    response = "NEEDS_NATURAL_LANGUAGE"
                return response

            # Run Cognition via Cycle
            internal_response = self.comm_cycle.cognition(cognitive_process)

            # Handling "Special" Internal Responses
            final_msg = internal_response
            parts = command.split(" ", 1)
            arg = parts[1] if len(parts) > 1 else ""

            if internal_response == "NEEDS_EXTERNAL_KNOWLEDGE":
                self._speak_and_think("My internal archives are silent on this matter.")
                final_msg = "I do not know."
            elif internal_response == "NEEDS_AI_CORE":
                self._speak_and_think("I am offline. I cannot consult the AI Core.")
                final_msg = "AI Core unreachable."
            elif internal_response == "NEEDS_TRANSLATION":
                final_msg = "Translation module offline."
            elif internal_response == "NEEDS_DETECTION":
                final_msg = "Language detection offline."
            elif internal_response == "NEEDS_NATURAL_LANGUAGE":
                final_msg = self._handle_natural_language(command)
            elif internal_response == "MINIMIZE":
                self._speak_and_think("Switching to background monitoring mode. I'm still here.", duration=3)
                self.desktop_ui.minimize_to_tray()
                final_msg = "Background mode activated."
            elif internal_response == "HALT_IMMEDIATE":
                self._speak_and_think("Deactivating all systems. Heartbeat stopping.")
                time.sleep(1.0)
                os._exit(0)
            elif internal_response == "MINIMIZE_TRAY":
                self._speak_and_think("Powering down. Goodbye, Master.")
                time.sleep(1.0)
                self.desktop_ui.minimize_to_tray()
                final_msg = "Brio is sleeping in the background."

            # Encoding & Transmission
            self.comm_cycle.encode(final_msg)
            
            # Real transmission (UI/Voice)
            def transmit_effect(msg):
                 self._speak_and_think(msg, duration=15 if len(msg) > 50 else 5)
            
            self.comm_cycle.transmit(transmit_effect)
            
            # Reset status back to Online after processing
            self.desktop_ui.bridge.status_signal.emit("Online")
            
            return final_msg
        except Exception as e:
            print(f"[Brain Error] Command handling failed: {e}")
            import traceback
            traceback.print_exc()
            self.desktop_ui.bridge.status_signal.emit("Neural Error")
            self.desktop_ui.show_thought(f"I'm sorry, my neural pathways encountered an error: {str(e)[:100]}")
            return "ERROR"

    def _handle_natural_language(self, prompt: str) -> str:
        """
        Internal Natural Language Processor for 'Life Training'.
        Uses Associative Recall (Engrams) and Subjective Logic before falling back to Kimi.
        """
        # 1. Extract Keywords for Associative Recall
        keywords = [word for word in prompt.split() if len(word) > 3]
        dom_emotion = self.emotions.get_dominant_emotion().value
        
        # 2. Search Internal Engrams
        memories = self.knowledge.associative_recall(emotion=dom_emotion, keywords=keywords)
        
        # 3. Decision Logic: Do I have internal context?
        if memories:
            best_memory = memories[0]
            # Use Subjective Logic to determine confidence (simplified)
            # Higher synaptic density increases Brio's confidence in internal recall
            confidence = self.neural.complexity_score * 0.8 + 0.2
            
            if confidence > 0.6:
                response = f"Recall Pattern [{best_memory.emotion_origin}]: {best_memory.content}"
                self._speak_and_think(response, duration=10)
                return response
            else:
                self._speak_and_think("This sounds familiar... but I need to consult the greater nexus.", duration=3)
        
        # 4. Fallback: Refusal
        self._speak_and_think("This is unfamiliar to me.", duration=3)
        return "I don't recall that."

    def _gather_sensor_data(self) -> Dict:
        data = {"battery": 1.0, "charging": True, "cpu": 0.0}
        if HAS_PSUTIL:
            try:
                import psutil
                batt = psutil.sensors_battery()
                data["battery"] = batt.percent / 100.0 if batt else 1.0
                data["charging"] = batt.power_plugged if batt else True
                data["cpu"] = psutil.cpu_percent(interval=None)
            except: pass
        return data
        
    def _load_env_file(self):
        """Manually parse .env file to ensure persistence across reboots."""
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            print(f"[System] Loading environment from {env_path}")
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            # Remove optional quotes
                            val = val.strip().strip('"').strip("'")
                            os.environ[key.strip()] = val
                            # If it's the Groq key, don't print the whole thing
                            if "KEY" in key.upper():
                                print(f"  + Loaded {key.strip()} (set)")
                            else:
                                print(f"  + Loaded {key.strip()}={val}")
            except Exception as e:
                print(f"[ERROR] Could not load .env file: {e}")
        else:
            print("[WARNING] No .env file found. Environment variables must be set manually.")

if __name__ == "__main__":
    # Setup error logging
    import logging
    logging.basicConfig(
        filename='brio_startup.log',
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        logging.info("=" * 50)
        logging.info("BRIO STARTUP INITIATED")
        logging.info("=" * 50)
        
        logging.info("Creating BrioSystem instance...")
        brio = BrioSystem()
        logging.info("BrioSystem created successfully")
        
        print("Brio v4.5 is Live. 20Hz Engine. Press Ctrl+C to stop.")
        logging.info("Entering main event loop")
        
        try:
            while True:
                brio.tick(dt=0.05)
                brio.app.processEvents()
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("Shutting Down...")
            logging.info("Keyboard interrupt received, shutting down")
            
    except Exception as e:
        error_msg = f"FATAL ERROR during startup: {e}"
        print(error_msg)
        logging.error(error_msg, exc_info=True)
        
        # Show a simple error dialog
        try:
            from PyQt5.QtWidgets import QMessageBox, QApplication
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "Brio Startup Error", 
                f"Brio failed to start:\n\n{str(e)}\n\nCheck brio_startup.log for details")
        except:
            pass
        
        import traceback
        traceback.print_exc()
        sys.exit(1)



