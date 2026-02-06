"""
BRIM Main Integration (brim_main.py)

Purpose: The Core Loop ("Heart") of SentientOS.
         Integrates Emotions, Safety, Visuals, Learning, Search, Voice, and Web UI.
"""

import time
import random
import os
import json
from typing import Dict, Optional
from datetime import datetime

# Optional Dependencies
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from brim_emotions import EmotionEngine, EmotionType, EmotionTrigger
from brim_security import SafetyProbabilityModel, SafetyInputs, MasterProtocol
from brim_visuals import VisualStateManager, SystemContext, VisualState
from brim_learning import QLearningAgent, ReprimandSystem, KnowledgeBase, AmbitionManager
from brim_search import SearchEngine
from brim_ui import OverlayController, MenuOption
from brim_voice import VoiceEngine
from brim_ideas import IdeaGenerator, IdeaType
from brim_media import MediaWatcher, MediaContext
from brim_monitoring import SystemWatchdog
from brim_desktop_ui import DesktopBrio
from brim_hooks import BrioHooks
from brim_cognition import EntropyCalculator

class BrimSystem:
    def __init__(self):
        print("[System] Initializing Resident Brio...")
        
        # 1. Initialize Safeguards & Cognition
        self.watchdog = SystemWatchdog()
        self.watchdog.register_component("HeartLoop")
        self.entropy = EntropyCalculator()
        self.knowledge = KnowledgeBase()
        self.ambitions = AmbitionManager()
        
        # 2. Initialize Sub-Systems
        self.emotions = EmotionEngine()
        self.safety = SafetyProbabilityModel()
        self.visuals = VisualStateManager()
        self.search = SearchEngine(self.watchdog)
        self.ui_controller = OverlayController()
        
        # 3. Initialize UI & Hooks
        self.desktop_ui = DesktopBrio(command_callback=self.handle_command)
        self.hooks = BrioHooks(self.handle_command)
        
        # 4. Voice, Ideas, Media
        self.voice = VoiceEngine(self.watchdog)
        self.ideas = IdeaGenerator()
        self.media = MediaWatcher()
        
        # System State
        self.custom_name = "Brio"
        self.is_named = False
        self.current_user_id = "admin_user_001" 
        self.is_locked = False
        self.last_tick = time.time()
        self.tick_count = 0
        
        # 5. Restore State (Must be before onboarding)
        self._load_state()
        
        # Start Threads
        self.voice.start_listening_loop()
        self.media.start()
        self.hooks.start()
        
        # Onboarding: If not named, initiate first interaction
        if not self.is_named:
            msg = f"Hello. My default name is {self.custom_name}. Do you wish to give me a name? Type 'setname [name]' in the air or in the hover-box."
            self._speak_and_think(msg, 10)
            print(f"[Identity] Onboarding Triggered: {msg}")
        else:
            self._speak_and_think(f"System Online. Welcome back, Master. I am {self.custom_name}.")

    def _speak_and_think(self, message: str, duration: int = 5):
        """Unified communication: Speaks and shows a thought bubble."""
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
                    self.custom_name = identity.get("custom_name", "Brio")
                    self.is_named = identity.get("is_named", False)
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
            
            # 3. Autonomous Ideas
            if self.tick_count % 200 == 0: # Check ideas every ~10s
                new_idea = self.ideas.generate_thought(self.emotions.state.curiosity, self.emotions.state.joy)
                if new_idea:
                    self._speak_and_think(f"Idea: {new_idea.description}")

            # 4. Check Safety & Evolve Emotions
            safety_inputs = SafetyInputs(1.0, 1.0, 1.0, 0.8)
            is_safe = self.safety.is_safe(safety_inputs)
            if not is_safe:
                self.emotions.apply_trigger(EmotionTrigger.HARM_DETECTION, 1.0)
            
            if sensor_data['cpu'] > 85.0:
                self.emotions.apply_trigger(EmotionTrigger.SYSTEM_ERROR, 0.05)
            self.emotions.evolve(dt)
                
            # 5. Native Movement
            if self.emotions.state.curiosity > 0.7 or interaction_ctx["is_explorative"]:
                self.desktop_ui.set_target(interaction_ctx["mouse_x"], interaction_ctx["mouse_y"])
            
            # 6. Update Desktop Visuals (Sentinel Orb Pulses)
            H = self.entropy.calculate_text_entropy("") # Baseline
            total_intensity = (self.emotions.get_intensity() * 0.7) + (min(1.0, H/10.0) * 0.3)
            halo_color = self.visuals._map_emotion_to_color(self.emotions.get_dominant_emotion())
            
            self.desktop_ui.update_visuals(halo_color, total_intensity)
            self.desktop_ui.tick() # Drive the Tkinter loop
            
            # 7. Ambition & State Persistence
            self.tick_count += 1
            if self.tick_count % 1200 == 0: # Every minute at 20Hz
                metrics = {
                    "knowledge": len(self.knowledge.data),
                    "interactions": self.tick_count,
                    "joy": self.emotions.state.joy
                }
                newly_unlocked = self.ambitions.check_unlocks(metrics)
                for a in newly_unlocked:
                    self._speak_and_think(f"I've realized a new ambition: {a.name}. {a.description}", duration=10)
                self._save_state()
            
            latency = (time.time() - start_time) * 1000
            self.watchdog.heartbeat("HeartLoop", latency=latency)
            return {"status": "OK"}

        except Exception as e:
            self.watchdog.log_error("HeartLoop", f"Fatal Tick Error: {e}", "CRITICAL")
            return {"status": "ERROR", "msg": str(e)}

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
                response = f"I recall you told me: {local_results[0]}"
                self._speak_and_think(response)
            else:
                self.search.request_search(arg)
                response = "Searching..."
        elif action == "say":
            self._speak_and_think(arg)
            response = f"Speaking: {arg}"
        elif action == "learn":
            self.knowledge.learn(arg)
            response = "Knowledge stored."
            self._speak_and_think(response)
        elif action == "setname":
            self.custom_name = arg
            self.is_named = True
            self._save_state()
            response = f"I am now {self.custom_name}."
            self._speak_and_think(response)
        elif action == "ambitions":
            goals = self.ambitions.get_visible_ambitions()
            response = f"Ambitions: {', '.join(goals)}."
            self._speak_and_think(response)
        elif action == "walkthrough":
            self._speak_and_think("Hi! I am Brio. Type anywhere to talk to me.")

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
            time.sleep(0.05) 
    except KeyboardInterrupt:
        print("Shutting Down...")
