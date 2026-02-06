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
        self.has_stt_active = HAS_STT
        
        # Initialize TTS
        if self.has_tts_active:
            try:
                self.tts_engine = pyttsx3.init()
                # Younger/Curious check: Increase rate for a chipper feel
                self.tts_engine.setProperty('rate', 190) 
                self.tts_engine.setProperty('volume', 0.9)
                
                # Try to find a 'younger' or female voice (often sounds more youthful in TTS)
                voices = self.tts_engine.getProperty('voices')
                for voice in voices:
                    if "zira" in voice.name.lower() or "female" in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
            except Exception as e:
                print(f"[Voice] TTS Init Error: {e}")
                self.has_tts_active = False
        
        # Initialize STT (Mic Check)
        if self.has_stt_active:
            try:
                p = pyaudio.PyAudio()
                # Check if at least one input device exists
                if p.get_device_count() == 0:
                    print("[Voice] No microphone detected. Hearing disabled.")
                    self.has_stt_active = False
                p.terminate()
            except Exception as e:
                print(f"[Voice] PyAudio Error: {e}")
                self.has_stt_active = False

    def speak(self, text: str):
        """Speak text using TTS or fallback to print"""
        print(f"[BRIO SPEAKS]: {text}")
        if self.watchdog:
            self.watchdog.heartbeat("VoiceEngine")
            
        if self.has_tts_active and self.tts_engine:
            try:
                # Wrap in a thread to prevent blocking the main engine during long speech
                threading.Thread(target=self._speak_sync, args=(text,), daemon=True).start()
            except Exception as e:
                print(f"[Voice] TTS Error: {e}")

    def _speak_sync(self, text):
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except: pass

    def start_listening_loop(self):
        """Starts background thread for wake-word detection"""
        if not self.has_stt_active:
            print("[Voice] Voice commands disabled (Missing driver or Mic).")
            return

        self.is_listening = True
        t = threading.Thread(target=self._listen_worker, daemon=True)
        t.start()
        
    def _listen_worker(self):
        """Real listener or Simulation fallback"""
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
            stream.start_stream()
            print("[Voice] Listening active.")
            
            while self.is_listening:
                # Real recognition logic would go here
                time.sleep(0.1)
        except Exception as e:
            print(f"[Voice] Listener Thread Crash: {e}")
            self.has_stt_active = False

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
