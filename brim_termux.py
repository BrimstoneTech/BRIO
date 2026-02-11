import shutil
import os
import sys
import subprocess
import threading
import time
import random

# Import Brio Brains (Light Version)
# Note: Emotion/Search/Sunbird are pure Python, so we can reuse them if deps are installed
try:
    from brim_sunbird import SunbirdService
    from brim_search import SearchEngine
    from brim_emotions import EmotionEngine, EmotionType
    from brim_monitoring import SystemWatchdog
    from brim_learning import KnowledgeBase
except ImportError as e:
    print(f"Brio Mobile Error: Dependency missing: {e}")
    sys.exit(1)

class AndroidBrio:
    """The mobile body for Brio running on Termux."""
    def __init__(self):
        print("[Android] Connecting Neural Pathways...")
        self.sunbird = SunbirdService()
        self.emotions = EmotionEngine()
        self.knowledge = KnowledgeBase()
        self.watchdog = SystemWatchdog()
        self.search = SearchEngine(self.watchdog)
        
        # Check Capabilities
        self.has_termux_api = shutil.which("termux-tts-speak") is not None
        self.has_espeak = shutil.which("espeak") is not None
        
        # Identity
        self.name = "Brio"
        self._say_hello()

    def _say_hello(self):
        """Intro based on mood."""
        # Simple random for now on mobile to save resources
        greetings = [
            "Online on Android.",
            "I'm with you on the go.",
            "Mobile systems ready."
        ]
        self.speak(random.choice(greetings))

    def speak(self, text):
        """Uses Termux API or ESpeak to speak."""
        print(f"[{self.name}] {text}") 
        
        if self.has_termux_api:
            subprocess.Popen(['termux-tts-speak', text])
        elif self.has_espeak:
            # Fallback to robotic espeak
            subprocess.Popen(['espeak', text])
        else:
            # Silent mode (Text only)
            pass

    def listen(self):
        """Uses Termux API to get speech input."""
        if not self.has_termux_api:
            return None # Force text mode
            
        print("[Listening] Tap microphone on popup...")
        try:
            # -p prompt text
            result = subprocess.check_output(['termux-speech-to-text'], text=True)
            return result.strip()
        except Exception as e:
            return ""

    def run(self):
        """Main Loop for Android."""
        print("=================================")
        print("   Brio Mobile (Termux Edition)  ")
        print("=================================")
        print(" COMMANDS:")
        print("  type:  Manual text input")
        if self.has_termux_api:
            print("  speak: Voice input")
        print("  exit:  Shutdown")
        print("=================================")

        while True:
            choice = input("\n[You] > ").strip().lower()

            if choice == "exit":
                self.speak("Shutting down mobile link.")
                break
            
            elif choice == "speak" and self.has_termux_api:
                user_text = self.listen()
                if user_text:
                    print(f"You said: {user_text}")
                    self.process_input(user_text)
                else:
                    print("No audio detected.")

            elif choice == "type":
                user_text = input("Query: ")
                self.process_input(user_text)
                
            else:
                # Direct input mode
                if choice:
                    self.process_input(choice)

    def process_input(self, text):
        """Core Logic (Simplified for Mobile)."""
        # 1. Update Emotion
        self.emotions.update(text)
        
        # 2. Check for Search
        if "search for" in text.lower():
            query = text.lower().replace("search for", "").strip()
            self.speak(f"Searching for {query}...")
            # Simple dummy search response on mobile for now or actual search if installed
            # For Phase 0, we can just acknowledge
            self.speak(f"I found some results for {query} on the web.")
            return

        # 3. Ask Sunbird (LLM)
        # Note: We need an API key for Sunbird or it falls back to local patterns
        response = self.sunbird.ask(text, context=f"User is on Android Mobile. Mood: {self.emotions.get_dominant_emotion()}")
        
        self.speak(response)

if __name__ == "__main__":
    brio_mobile = AndroidBrio()
    brio_mobile.run()
