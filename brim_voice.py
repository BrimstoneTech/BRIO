"""
BRIM Voice Module (brim_voice.py)

Purpose: Handles Speech-to-Text (Hearing) and Text-to-Speech (Speaking).
         Designed to fail gracefully if 'vosk' or 'pyttsx3' are not installed.
"""

import threading
import queue
import time
import sys

# Try imports
try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

try:
    import vosk
    import pyaudio
    HAS_STT = True
except ImportError:
    HAS_STT = False

class VoiceEngine:
    def __init__(self, watchdog=None):
        self.input_queue = queue.Queue()
        self.is_listening = False
        self.tts_engine = None
        self.has_tts_active = HAS_TTS
        self.watchdog = watchdog
        
        # Initialize TTS
        if self.has_tts_active:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 160)
            except Exception as e:
                print(f"[Voice] TTS Init Error: {e}")
                self.has_tts_active = False
                if self.watchdog:
                    self.watchdog.log_error("VoiceEngine", f"TTS Init Failure: {e}")
        
        # Initialize STT
        self.stt_model = None

    def speak(self, text: str):
        """Speak text using TTS or fallback to print"""
        print(f"[BRIO SPEAKS]: {text}")
        if self.watchdog:
            self.watchdog.heartbeat("VoiceEngine")
            
        if self.has_tts_active and self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                print(f"[Voice] TTS Error: {e}")
                if self.watchdog:
                    self.watchdog.log_error("VoiceEngine", f"TTS Playback Error: {e}")

    def start_listening_loop(self):
        """Starts background thread for wake-word detection"""
        if not HAS_STT:
            print("[Voice] 'vosk' or 'pyaudio' not found. Voice commands disabled.")
            return

        self.is_listening = True
        t = threading.Thread(target=self._listen_worker, daemon=True)
        t.start()
        
    def _listen_worker(self):
        """Simulated listener or Real loop"""
        print("[Voice] Listening... (Simulation)")
        while self.is_listening:
            time.sleep(1)
            # In real implementation: read stream, rec.AcceptWaveform(data)
            pass

    def get_dependencies_status(self) -> str:
        status = []
        status.append(f"TTS (pyttsx3): {'INSTALLED' if HAS_TTS else 'MISSING'}")
        status.append(f"STT (vosk/pyaudio): {'INSTALLED' if HAS_STT else 'MISSING'}")
        
        if not (HAS_TTS and HAS_STT):
            status.append("\nTo enable Full Voice, run:")
            status.append("pip install pyttsx3 vosk pyaudio")
            
        return "\n".join(status)

# Test
if __name__ == "__main__":
    v = VoiceEngine()
    print(v.get_dependencies_status())
    v.speak("Hello Master. I am ready.")
