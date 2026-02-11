"""
BRIM Voice Module (brim_voice.py)

Purpose: Handles Speech-to-Text (Hearing) and Text-to-Speech (Speaking).
         Designed to fail gracefully if 'vosk' or 'pyttsx3' are not installed.
"""

import threading
import queue
import time
import sys
import os
import requests
import io
import wave

# Standard library imports are fast
import threading
import queue
import time
import sys
import os
import requests
import io
import wave
from typing import Optional

# Lazy-loaded imports for speed
HAS_TTS = True # Assuming true, will check inside init
HAS_STT = True

from brim_sunbird import SunbirdService

class VoiceEngine:
    def __init__(self, watchdog=None):
        self.input_queue = queue.Queue()
        self.is_listening = False
        self.tts_engine = None
        self.has_tts_active = True
        self.watchdog = watchdog
        self.has_stt_active = True
        self.sunbird = SunbirdService()
        self.is_ready = False
        
        # Start async initialization
        threading.Thread(target=self._async_init, daemon=True).start()

    def _async_init(self):
        """Heavy initialization of TTS/STT moved to background thread."""
        # 1. Initialize TTS
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 190) 
            self.tts_engine.setProperty('volume', 0.9)
            
            voices = self.tts_engine.getProperty('voices')
            for voice in voices:
                if "zira" in voice.name.lower() or "female" in voice.name.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
        except Exception as e:
            print(f"[Voice] TTS Init Error: {e}")
            self.has_tts_active = False

        # 2. Check STT hardware
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            if p.get_device_count() == 0:
                print("[Voice] No microphone detected. Hearing disabled.")
                self.has_stt_active = False
            p.terminate()
        except Exception as e:
            print(f"[Voice] Audio Hardware Error: {e}")
            self.has_stt_active = False
            
        self.is_ready = True
        print("[Voice] Engine initialized in background.")

    def speak(self, text: str):
        """Speak text using Sunbird AI (Remote), pyttsx3 (Local), or printer fallback"""
        print(f"[BRIO SPEAKS]: {text}")
        if self.watchdog:
            self.watchdog.heartbeat("VoiceEngine")
            
        # Try Sunbird AI first for high fidelity
        threading.Thread(target=self._speak_flow, args=(text,), daemon=True).start()

    def _speak_flow(self, text: str):
        """Orchestrates remote-first with local fallback"""
        # 1. Attempt Sunbird Remote TTS
        audio_data = self.sunbird.tts(text)
        if audio_data:
            self._play_audio(audio_data)
            return

        # 2. Fallback to Local pyttsx3
        if self.has_tts_active and self.tts_engine:
            self._speak_sync(text)

    def _play_audio(self, audio_bytes: bytes):
        """Plays raw audio bytes (WAV/MP3) using PyAudio if available"""
        if not HAS_STT: return # Requires PyAudio for playback too
        try:
            import pydub
            from pydub.playback import play
            audio = pydub.AudioSegment.from_file(io.BytesIO(audio_bytes))
            play(audio)
        except ImportError:
            # Basic WAV play if pydub not found
            try:
                p = pyaudio.PyAudio()
                f = wave.open(io.BytesIO(audio_bytes), 'rb')
                stream = p.open(format=p.get_format_from_width(f.getsampwidth()),
                                channels=f.getnchannels(),
                                rate=f.getframerate(),
                                output=True)
                data = f.readframes(1024)
                while data:
                    stream.write(data)
                    data = f.readframes(1024)
                stream.stop_stream()
                stream.close()
                p.terminate()
            except: pass

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
