"""
BRIM Main Integration (brim_main.py)

Purpose: The Core Loop ("Heart") of SentientOS.
         Integrates Emotions, Safety, Visuals, Learning, Search, Voice, and Web UI.
"""

import time
import random
import os
import json
import threading
import sys
import socket
from typing import Dict, Optional
from datetime import datetime

# Optional Dependencies
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ... (Imports of lightweight modules)
from brim_monitoring import SystemWatchdog
from brim_desktop_ui import DesktopBrio
from brim_hooks import BrioHooks
from brim_cognition import EntropyCalculator
from brim_sunbird import SunbirdService
from brim_kimi import KimiBridge
# Note: Heavy modules (Emotions, Voice, Search, Ideas, Visuals, Security, Learning, Media) 
# are now lazy-loaded in _background_awakening for Instant Boot.

class BrimSystem:
    def __init__(self):
        print("[System] Brio v3.3: UI-First Launch Initiated...")
        
        # 0. Single Instance Check
        self.instance_lock = SingleInstanceLock()
        
        # 1. Essential Safeguards (Minimal/Fast)
        self.watchdog = SystemWatchdog()
        self.watchdog.register_component("HeartLoop")
        self.entropy = EntropyCalculator()
        
        # 2. Sunbird Service (Fast REST Init)
        self.sunbird = SunbirdService()
        
        # 3. UI Phase (CRITICAL: LAUNCH THIS IMMEDIATELY)
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)
            
        self.desktop_ui = DesktopBrio(command_callback=self.handle_command)
        self.desktop_ui.user_typing_signal.connect(self.halt_response)
        self.desktop_ui.show()
        
        # Placeholder triggers for main loop before they are loaded
        self.emotions = None
        self.voice = None
        self.visuals = None
        self.knowledge = None  # Loaded in BG for speed if large
        self.is_awake = False  # Flag to check if bg modules are ready
        
        # 4. Background Awakening (Heavier Sub-systems)
        threading.Thread(target=self._background_awakening, daemon=True).start()
        
        # Set initial UI tick state
        self.last_tick = time.time()
        self.tick_count = 0
        self.is_named = True
        self.custom_name = "Brio"
        self.current_user_id = "admin_user_001" 
        self.is_locked = False

    def _background_awakening(self):
        """Initializes heavy brains in the background while UI is already visible."""
        print("[System] Awakening Brio's sub-systems in background...")
        
        # Lazy Imports for Speed
        global EmotionEngine, EmotionType, EmotionTrigger
        from brim_emotions import EmotionEngine, EmotionType, EmotionTrigger
        
        global SafetyProbabilityModel, SafetyInputs, MasterProtocol
        from brim_security import SafetyProbabilityModel, SafetyInputs, MasterProtocol
        
        global VisualStateManager, SystemContext, VisualState
        from brim_visuals import VisualStateManager, SystemContext, VisualState
        
        global QLearningAgent, ReprimandSystem, KnowledgeBase, AmbitionManager, MilestoneManager
        from brim_learning import QLearningAgent, ReprimandSystem, KnowledgeBase, AmbitionManager, MilestoneManager
        
        global SearchEngine
        from brim_search import SearchEngine
        
        global VoiceEngine
        from brim_voice import VoiceEngine
        
        global IdeaGenerator, IdeaType
        from brim_ideas import IdeaGenerator, IdeaType
        
        global MediaWatcher, MediaContext
        from brim_media import MediaWatcher, MediaContext
        
        # Initialize sub-systems sequentially in background thread
        self.knowledge = KnowledgeBase() # Moved here
        self.ambitions = AmbitionManager()
        self.milestones = MilestoneManager()
        self.emotions = EmotionEngine()
        self.safety = SafetyProbabilityModel()
        self.visuals = VisualStateManager()
        self.search = SearchEngine(self.watchdog)
        
        self.hooks = BrioHooks(self.handle_command)
        self.voice = VoiceEngine(self.watchdog)
        self.ideas = IdeaGenerator()
        self.media = MediaWatcher()
        self.kimi = KimiBridge()
        
        # Restore State
        self._load_state()
        
        # Start background loops
        self.voice.start_listening_loop()
        self.media.start()
        self.hooks.start()
        
        self.is_awake = True # Signal ready
        print("[System] Brio is fully online.")
        
        time.sleep(1) # Small buffer
        
        # Onboarding & Greetings
        if len(self.knowledge.data) < 5:
            # First Run (Warm Welcome)
            welcome_msg = (
                "Hello! I am Brio, your personal AI companion. "
                "I'm here to help you navigate, create, and organize. "
                "You can type or speak to me at any time."
            )
            self._speak_and_think(welcome_msg, duration=10)
        else:
            # Mood-Based Greeting
            dom_emotion = self.emotions.get_dominant_emotion()
            greeting = self._generate_greeting(dom_emotion)
            self._speak_and_think(greeting)

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
        # Fallback to JOY if emotion not found or generic
        options = greetings.get(emotion, greetings[EmotionType.JOY])
        return random.choice(options)

    def halt_response(self):
        """Interrupts Brio specifically when the user wants to take over."""
        if self.voice:
            self.voice.stop_speaking()
        # We don't hide the thought bubble necessarily, but we stop the "stream"
        print("[Interrupt] User is typing. Halting speech.")

    def _speak_and_think(self, message: str, duration: int = 5):
        """Unified communication: Speaks and shows a thought bubble."""
        if not self.is_awake:
             # Fallback if speaking before fully awake
             print(f"[Fallback Speak] {message}")
             self.desktop_ui.show_thought(message, duration_sec=duration)
             return

        self.voice.speak(message)
        self.desktop_ui.show_thought(message, duration_sec=duration)

    def _save_state(self):
        """Persists critical memory to disk"""
        try:
            state_data = {
                "emotions": self.emotions.export_state(),
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
            # 1. Gather Context
            sensor_data = self._gather_sensor_data()
            interaction_ctx = self.hooks.get_context()
            
            # 2. Media Awareness
            media_ctx = self.media.get_context()
            self._react_to_media(media_ctx)
            
            # 3. Autonomous Ideas (Reduced frequency for considerateness: Every ~2 mins)
            if self.tick_count % 2400 == 0: 
                knowledge_len = len(self.knowledge.data)
                new_idea = self.ideas.generate_thought(self.emotions.state.curiosity, self.emotions.state.joy, knowledge_len)
                if new_idea:
                    self._speak_and_think(new_idea.description)

            # 4. Check Safety & Evolve Emotions
            safety_inputs = SafetyInputs(1.0, 1.0, 1.0, 0.8)
            is_safe = self.safety.is_safe(safety_inputs)
            if not is_safe:
                self.emotions.apply_trigger(EmotionTrigger.HARM_DETECTION, 1.0)
            
            if sensor_data['cpu'] > 85.0:
                self.emotions.apply_trigger(EmotionTrigger.SYSTEM_ERROR, 0.05)
            self.emotions.evolve(dt)
                
            # 5. Native Autonomous Movement (Wander Mode)
            # Increased frequency (every 10s) and random logic
            if self.tick_count % 200 == 0: 
                if self.emotions.state.curiosity > 0.5:
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
            total_intensity = (self.emotions.get_intensity() * 0.7) + (min(1.0, H/10.0) * 0.3)
            halo_color = self.visuals._map_emotion_to_color(self.emotions.get_dominant_emotion())
            
            self.desktop_ui.update_visuals(halo_color, total_intensity)
            
            # 7. Ambition & State Persistence
            self.tick_count += 1
            
            # Milestone: Interaction frequency
            if self.tick_count % 5000 == 0:
                self._document_growth("Interaction threshold")

            if self.tick_count % 1200 == 0: # Every minute at 20Hz
                metrics = {
                    "knowledge": len(self.knowledge.data),
                    "interactions": self.tick_count,
                    "joy": self.emotions.state.joy
                }
                m_count = self.milestones.get_progress_percent()
                newly_unlocked = self.ambitions.check_unlocks(metrics, m_count)
                for a in newly_unlocked:
                    self._speak_and_think(f"I've realized a new ambition: {a.name}. {a.description}", duration=10)
                self._save_state()
            
            # 8. Safe Autonomy (Idle Checks) - Every 5 minutes (approx 6000 ticks at 20Hz)
            if self.tick_count % 6000 == 0:
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

    def handle_command(self, command: str) -> str:
        """Process user commands"""
        H = self.entropy.calculate_text_entropy(command)
        if H > 4.5:
            self.emotions.apply_trigger(EmotionTrigger.CONFLICTING_REQUEST, 0.2)

        if not MasterProtocol.verify_master_intent(self.current_user_id):
            return "ACCESS DENIED."
            
        parts = command.split(" ", 1)
        action = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        response = "Unknown Command."
        
        if action == "search":
            local_results = self.knowledge.search(arg)
            if local_results:
                response = f"Recall: {local_results[0]}"
                self._speak_and_think(response)
            else:
                self._speak_and_think("Local search yielded nothing. Reaching out to Kimi...")
                kimi_response = self.kimi.ask_kimi(arg)
                self._speak_and_think(kimi_response, duration=15)
                response = f"Seeking Kimi Knowledge..."
        elif action == "say":
            self._speak_and_think(arg)
            response = "Message relayed."
        elif action == "learn":
            self.knowledge.learn(arg)
            k_len = len(self.knowledge.data)
            response = f"Assimilated. Memory unit {k_len} stored."
            self._speak_and_think(response)
            self._document_growth("Knowledge injection")
        elif action == "setname":
            response = "I am Brio. My identity is fixed and unwavering."
            self._speak_and_think(response)
        elif action == "ambitions":
            goals = self.ambitions.get_visible_ambitions()
            response = f"Aspirations: {', '.join(goals)}."
            self._speak_and_think(response)
        elif action == "walkthrough":
            self._speak_and_think("Hi! I am Brio. Type anywhere to talk to me.")
        elif action == "settings":
            response = f"Current Configuration: Name={self.custom_name}, Confidence={self.emotions.state.confidence:.2f}."
            self._speak_and_think(response)
        elif action == "milestones":
            p = self.milestones.get_progress_percent()
            next_m = self.milestones.get_next_incomplete()
            response = f"Growth: {p}/100. Target: {next_m.name if next_m else 'None'}."
            self._speak_and_think(response)
        elif action == "background" or action == "hide":
            self._speak_and_think("Switching to background monitoring mode. I'm still here.", duration=3)
            self.desktop_ui.minimize_to_tray()
            response = "Background mode activated."
        elif action == "shutdown_force":
            self._speak_and_think("Deactivating all systems. Heartbeat stopping.")
            time.sleep(1.0)
            os._exit(0)
        elif action == "shutdown" or action == "exit":
            self._speak_and_think("Powering down. Goodbye, Master. (I will remain in the tray unless you stop me entirely).")
            time.sleep(1.0)
            self.desktop_ui.minimize_to_tray()
            response = "Brio is sleeping in the background."
        elif action == "ask" or action == "ash":
            # Auto-detect language
            detected = self.sunbird.detect_language(arg)
            if detected != "eng" and detected in self.sunbird.get_supported_languages():
                self._speak_and_think(f"Detected {detected}. Consulting AI core...")
                response = self.sunbird.sunflower_ask(arg, source_lang=detected, target_lang=detected)
                self._speak_and_think(response, duration=15)
            else:
                self._speak_and_think("Consulting Kimi...", duration=2)
                kimi_response = self.kimi.ask_kimi(arg)
                self._speak_and_think(kimi_response, duration=15)
                response = f"Kimi: {kimi_response[:50]}..."
        elif action == "translate":
            target = "lug"
            text_to_translate = arg
            if " to " in arg:
                text_to_translate, target = arg.rsplit(" to ", 1)
                target = target.strip().lower()
            
            translated = self.sunbird.translate(text_to_translate, target_lang=target)
            self._speak_and_think(f"In {self.sunbird.get_supported_languages().get(target, target)}: {translated}", duration=10)
            response = f"Translated to {target}."
        elif action == "languages" or action == "voices":
            langs = self.sunbird.get_supported_languages()
            response = "Brio Language Mastery: " + ", ".join([f"{v} ({k})" for k, v in langs.items()])
            self._speak_and_think(response)
        elif action == "detect":
            detected = self.sunbird.detect_language(arg)
            response = f"Detected Language: {detected}"
            self._speak_and_think(response)

        # Ensure we ALWAYS respond visibly if not handled above
        if not response:
            response = "Acknowledged. I'm processing."
            self._speak_and_think(response)
        
        return response

    def _gather_sensor_data(self) -> Dict:
        data = {"battery": 1.0, "charging": True, "cpu": 0.0}
        if HAS_PSUTIL:
            try:
                batt = psutil.sensors_battery()
                data["battery"] = batt.percent / 100.0 if batt else 1.0
                data["charging"] = batt.power_plugged if batt else True
                data["cpu"] = psutil.cpu_percent(interval=None)
            except: pass
        return data

if __name__ == "__main__":
    brio = BrimSystem()
    print("Brio (Sentinel Orb) is Live. 20Hz Engine. Press Ctrl+C to stop.")
    try:
        while True:
            brio.tick(dt=0.05)
            brio.app.processEvents()
            time.sleep(0.05) 
    except KeyboardInterrupt:
        print("Shutting Down...")
