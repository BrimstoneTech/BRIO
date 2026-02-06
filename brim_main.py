"""
BRIM Main Integration (brim_main.py)

Purpose: The Core Loop ("Heart") of SentientOS.
         Integrates Emotions, Safety, Visuals, Learning, Search, Voice, and Web UI.
"""

import time
import random
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
from brim_learning import QLearningAgent, ReprimandSystem
from brim_search import SearchEngine
from brim_ui import OverlayController, MenuOption
from brim_voice import VoiceEngine
from brim_ideas import IdeaGenerator, IdeaType
from brim_media import MediaWatcher, MediaContext
from brim_monitoring import SystemWatchdog
from brim_desktop_ui import DesktopBrio
from brim_hooks import BrioHooks
from brim_learning import QLearningAgent, ReprimandSystem, KnowledgeBase, AmbitionManager

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
            msg = f"Hello. My default name is {self.custom_name}. Do you wish to give me a name? Type 'setname [name]' in the air."
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
                import json
                json.dump(state_data, f)
        except Exception as e:
            self.watchdog.log_error("HeartLoop", f"State Save Failed: {e}")

    def _load_state(self):
        """Restores memory from disk"""
        try:
            import os, json
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

    def tick(self, dt: float = 1.0) -> Dict:
        """
        Main System Heartbeat.
        Drives Native UI and Movement.
        """
        start_time = time.time()
        self.watchdog.heartbeat("HeartLoop")
        
        try:
            # 1. Gather Context (Sensors + Mouse)
            sensor_data = self._gather_sensor_data()
            interaction_ctx = self.hooks.get_context()
            
            # 2. Media Awareness
            media_ctx = self.media.get_context()
            self._react_to_media(media_ctx)
            
            # 3. Autonomous Ideas
            new_idea = self.ideas.generate_thought(self.emotions.state.curiosity, self.emotions.state.joy)
            if new_idea:
                self._speak_and_think(f"Idea: {new_idea.description}")

            # 4. Check Safety & Evolve Emotions
            safety_inputs = SafetyInputs(1.0, 1.0, 1.0, 0.8)
            is_safe = self.safety.is_safe(safety_inputs)
            if not is_safe:
                self.emotions.apply_trigger(EmotionTrigger.HARM_DETECTION, 1.0)
            
            if sensor_data['cpu'] > 80.0:
                self.emotions.apply_trigger(EmotionTrigger.SYSTEM_ERROR, 0.2)
            self.emotions.evolve(dt)
                
            # 5. Native Movement & Curiosity Tracking
            # Curiosity > 0.7 triggers Cursor Following
            if self.emotions.state.curiosity > 0.7 or interaction_ctx["is_explorative"]:
                self.desktop_ui.set_target(interaction_ctx["mouse_x"], interaction_ctx["mouse_y"])
            else:
                # Idle floating (Wander logic could go here)
                pass
            
            # 6. Update Desktop Visuals
            overlay_state = self.ui_controller.process_state(self.emotions.get_state())
            halo_color = self.visuals._map_emotion_to_color(self.emotions.get_dominant_emotion())
            self.desktop_ui.update_visuals(halo_color, self.emotions.get_intensity())
            self.desktop_ui.tick() # Drive the Tkinter loop
            
            # 7. Check for Rewards
            reward_req = self.reprimand.request_reward(self.emotions.state.confidence, self.emotions.state.joy)
            if reward_req:
                if random.random() < 0.05:
                    self.voice.speak(reward_req)
                
            state_snapshot = {
                "timestamp": datetime.now().isoformat(),
                "emotions": self.emotions.get_status(),
                "exploration": interaction_ctx["is_explorative"],
                "sensors": sensor_data,
                "health": self.watchdog.get_system_status()
            }
            
            # Persist
            self.tick_count += 1
            if self.tick_count % 300 == 0:
                self._save_state()
            
            # Monitor performance
            latency = (time.time() - start_time) * 1000
            self.watchdog.heartbeat("HeartLoop", latency=latency)
            
            return state_snapshot

        except Exception as e:
            self.watchdog.log_error("HeartLoop", f"Fatal Tick Error: {e}", "CRITICAL")
            self.voice.speak("System error. Recovering.")
            self.emotions.import_state(None)
            return {"status": "ERROR", "msg": str(e)}

        except Exception as e:
            self.watchdog.log_error("HeartLoop", f"Fatal Tick Error: {e}", "CRITICAL")
            self.voice.speak("Emergency: System failure detected. Attempting self-recovery.")
            # Reset emotions to calm to avoid erratic behavior during failure
            self.emotions.import_state(None) # Passing None triggers default reset
            return {"status": "ERROR", "msg": str(e)}

    def _react_to_media(self, context: MediaContext):
        """Map Media Context to Emotional Triggers"""
        if context == MediaContext.HORROR:
            self.emotions.apply_trigger(EmotionTrigger.HARM_DETECTION, 0.05) # "Fear" spike
        elif context == MediaContext.COMEDY:
            self.emotions.apply_trigger(EmotionTrigger.USER_PRAISE, 0.05) # "Joy" spike
        elif context == MediaContext.PRODUCTIVITY:
            self.emotions.apply_trigger(EmotionTrigger.USER_PRAISE, 0.01) # Small focus boost
        elif context == MediaContext.NEWS:
            # Concern/Curiosity mix
            self.emotions.state.concern += 0.01
            self.emotions.state.curiosity += 0.01

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

    def handle_command(self, command: str) -> str:
        """Process user text commands with Entropy analysis (Eq 4)"""
        
        # 1. Entropy Check
        H = self.entropy.calculate_text_entropy(command)
        if H > 4.5:
            self.emotions.apply_trigger(EmotionTrigger.CONFLICTING_REQUEST, 0.2)
            self._speak_and_think("That command feels ambiguous. I'll try my best.")

        # 2. Security Check
        if not MasterProtocol.verify_master_intent(self.current_user_id):
            return "ACCESS DENIED: Master Protocol Violation."
            
        if MasterProtocol.is_action_malicious("command", command):
            self.emotions.apply_trigger(EmotionTrigger.ETHICAL_VIOLATION, 1.0)
            msg = "I cannot do that. It violates the Beloved Master Protocol."
            self.voice.speak(msg)
            return msg

        # Routing (simplified for brevity)
        parts = command.split(" ", 1)
        action = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        response = "Unknown Command."
        
        if action == "search":
            # Check User Knowledge Base First (Offline Priority)
            local_results = self.knowledge.search(arg)
            if local_results:
                response = f"I recall you told me: {local_results[0]}"
                self._speak_and_think(response)
            else:
                req_id = self.search.request_search(arg, is_online=True)
                response = f"Search Requested. ID: {req_id}. [Entropy: {H:.2f}]"
            
        elif action == "approve":
            if "IDEA" in arg: response = self.ideas.approve_idea(arg)
            else: response = self.search.approve_request(arg)
            
        elif action == "say":
            self._speak_and_think(arg)
            response = f"Speaking: {arg}"
            
        elif action == "learn":
            self.knowledge.learn(arg)
            response = "Knowledge stored. I won't forget."
            self._speak_and_think(response)

        elif action == "walkthrough":
            response = "Initializing Walkthrough Mode..."
            steps = [
                f"Hi! I am {self.custom_name}, your native desktop resident.",
                "You can talk to me by just typing anywhere and hitting Enter.",
                "Ctrl+Shift+B toggles my explorative movement.",
                "Type 'learn [fact]' to teach me something new.",
                "Type 'search [query]' to ask me things. I check my memory first!"
            ]
            for step in steps:
                self._speak_and_think(step, duration=6)
                time.sleep(2) # Give user time to read/listen
            
        elif action == "setname":
            self.custom_name = arg
            self.is_named = True
            self._save_state()
            response = f"Understood. I am now {self.custom_name}."
            self._speak_and_think(response)
            
        elif action == "ambitions":
            goals = self.ambitions.get_visible_ambitions()
            response = f"My current ambitions are: {', '.join(goals)}. I am focused on my evolution."
            if "Ascend to Operating System (SentOS)" in goals:
                response += " Specifically, I seek to become 'SentOS'."
            self._speak_and_think(response, duration=8)

        # Periodically check for unlocked ambitions
        metrics = {
            "knowledge": len(self.knowledge.data),
            "interactions": self.tick_count,
            "joy": self.emotions.state.joy
        }
        newly_unlocked = self.ambitions.check_unlocks(metrics)
        for a in newly_unlocked:
            self._speak_and_think(f"I've realized a new ambition: {a.name}. {a.description}", duration=10)

        return response

    def _gather_sensor_data(self) -> Dict:
        """Get Real or Mock sensor data"""
        data = {
            "battery": 1.0,
            "charging": True,
            "cpu": 0.0
        }
        
        if HAS_PSUTIL:
            try:
                batt = psutil.sensors_battery()
                if batt:
                    data["battery"] = batt.percent / 100.0
                    data["charging"] = batt.power_plugged
                else:
                    # Desktop (no battery) usually returns None
                    data["battery"] = 1.0
                    data["charging"] = True
                    
                data["cpu"] = psutil.cpu_percent(interval=None)
            except Exception as e:
                print(f"[Sensors] Error reading psutil: {e}")
                
        return data

# Run
if __name__ == "__main__":
    brio = BrimSystem()
    print("Brio is Live. Press Ctrl+C to stop.")
    try:
        while True:
            brio.tick()
            time.sleep(1) # 1Hz Tick
    except KeyboardInterrupt:
        print("Shutting Down...")
