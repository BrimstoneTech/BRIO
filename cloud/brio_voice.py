"""
Brio Voice Module (brio_voice.py)

Purpose: Gives BRIO a voice — text-to-speech for reading replies aloud,
         and speech-to-text for voice conversations.

FREE-TIER Options Implemented:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TTS (Text-to-Speech):
  1. pyttsx3        — Fully offline, uses system voices (eSpeak/SAPI5/nsss)
                       Already in requirements.txt. Zero API cost.
  2. gTTS           — Google Translate TTS. Free, unlimited, needs internet.
                       Produces natural-sounding MP3 files.
  3. Edge-TTS       — Microsoft Edge's free TTS API. 300+ voices, very natural.
                       Best quality of the free options. Async, needs internet.

STT (Speech-to-Text):
  1. Vosk            — Fully offline. Already in requirements.txt.
                       Models from 50MB (fast) to 1.8GB (accurate).
  2. SpeechRecognition — Google free tier (no API key needed).
                       Simple, reliable, needs internet.

Strategy:
  - Desktop edition: pyttsx3 (offline TTS) + Vosk (offline STT)
  - Cloud edition: Edge-TTS (best quality) + SpeechRecognition (simple)
  - Fallback chain: Edge-TTS → gTTS → pyttsx3 (never silent)

Author: BrimstoneTech
Version: 1.0
"""

import os
import sys
import time
import json
import queue
import threading
import tempfile
import logging
from typing import Optional, Callable, Dict, List
from enum import Enum

log = logging.getLogger("brio.voice")


# ============================================================================
# TTS ENGINE ABSTRACTION
# ============================================================================

class TTSEngine(Enum):
    PYTTSX3 = "pyttsx3"         # Offline, system voices
    GTTS = "gtts"               # Google Translate (free, online)
    EDGE_TTS = "edge_tts"       # Microsoft Edge (free, online, best quality)


class BrioTTS:
    """
    BRIO's voice output — reads text aloud.

    Priority: Edge-TTS > gTTS > pyttsx3 (fallback chain)

    Usage:
        tts = BrioTTS()
        tts.speak("Hello, I am BRIO. Don't just see — behold!")

        # Or save to file
        tts.speak_to_file("Hello world", "output.mp3")
    """

    def __init__(self, preferred_engine: TTSEngine = TTSEngine.EDGE_TTS,
                 voice: Optional[str] = None, rate: int = 170):
        self.preferred_engine = preferred_engine
        self.voice = voice
        self.rate = rate
        self._engine = None
        self._available_engines: List[TTSEngine] = []
        self._detect_available()

    def _detect_available(self):
        """Detect which TTS engines are installed."""
        # pyttsx3
        try:
            import pyttsx3
            self._available_engines.append(TTSEngine.PYTTSX3)
            log.info("pyttsx3 available (offline TTS)")
        except ImportError:
            log.debug("pyttsx3 not installed")

        # gTTS
        try:
            import gtts
            self._available_engines.append(TTSEngine.GTTS)
            log.info("gTTS available (Google Translate TTS)")
        except ImportError:
            log.debug("gTTS not installed — run: pip install gTTS")

        # Edge-TTS
        try:
            import edge_tts
            self._available_engines.append(TTSEngine.EDGE_TTS)
            log.info("Edge-TTS available (Microsoft Edge TTS — best quality)")
        except ImportError:
            log.debug("edge-tts not installed — run: pip install edge-tts")

        if not self._available_engines:
            log.warning("NO TTS engines available! Install at least pyttsx3.")

    def _get_engine(self) -> TTSEngine:
        """Get the best available engine."""
        if self.preferred_engine in self._available_engines:
            return self.preferred_engine
        # Fallback chain
        for engine in [TTSEngine.EDGE_TTS, TTSEngine.GTTS, TTSEngine.PYTTSX3]:
            if engine in self._available_engines:
                return engine
        raise RuntimeError("No TTS engine available")

    # ── Speak (play audio directly) ─────────────────────────────────────

    def speak(self, text: str):
        """Speak text aloud through the default audio output."""
        engine = self._get_engine()

        if engine == TTSEngine.PYTTSX3:
            self._speak_pyttsx3(text)
        elif engine == TTSEngine.GTTS:
            self._speak_gtts(text)
        elif engine == TTSEngine.EDGE_TTS:
            self._speak_edge_tts(text)

    def _speak_pyttsx3(self, text: str):
        """Offline TTS using system voices."""
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', self.rate)

        # Set voice if specified
        if self.voice:
            voices = engine.getProperty('voices')
            for v in voices:
                if self.voice.lower() in v.name.lower():
                    engine.setProperty('voice', v.id)
                    break

        engine.say(text)
        engine.runAndWait()

    def _speak_gtts(self, text: str):
        """Google Translate TTS — free, natural, needs internet."""
        from gtts import gTTS

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(f.name)
            self._play_audio(f.name)
            os.unlink(f.name)

    def _speak_edge_tts(self, text: str):
        """Microsoft Edge TTS — best free quality."""
        import asyncio
        import edge_tts

        voice = self.voice or "en-GB-RyanNeural"  # Deep, clear British voice for BRIO

        async def _generate():
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                communicate = edge_tts.Communicate(text, voice, rate=f"+{self.rate - 150}%")
                await communicate.save(f.name)
                return f.name

        # Run async in sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context (e.g. Flask)
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    path = pool.submit(lambda: asyncio.run(_generate())).result()
            else:
                path = loop.run_until_complete(_generate())
        except RuntimeError:
            path = asyncio.run(_generate())

        self._play_audio(path)
        os.unlink(path)

    # ── Speak to File ───────────────────────────────────────────────────

    def speak_to_file(self, text: str, output_path: str) -> str:
        """Generate speech audio file without playing it. Returns file path."""
        engine = self._get_engine()

        if engine == TTSEngine.PYTTSX3:
            import pyttsx3
            eng = pyttsx3.init()
            eng.setProperty('rate', self.rate)
            eng.save_to_file(text, output_path)
            eng.runAndWait()

        elif engine == TTSEngine.GTTS:
            from gtts import gTTS
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(output_path)

        elif engine == TTSEngine.EDGE_TTS:
            import asyncio
            import edge_tts
            voice = self.voice or "en-GB-RyanNeural"

            async def _save():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_path)

            asyncio.run(_save())

        return output_path

    # ── Audio Playback ──────────────────────────────────────────────────

    @staticmethod
    def _play_audio(path: str):
        """Play an audio file. Tries multiple methods."""
        # Try pygame (cross-platform)
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            return
        except (ImportError, Exception):
            pass

        # Try pydub + simpleaudio
        try:
            from pydub import AudioSegment
            from pydub.playback import play
            audio = AudioSegment.from_file(path)
            play(audio)
            return
        except (ImportError, Exception):
            pass

        # Try system command
        if sys.platform == "darwin":
            os.system(f"afplay '{path}'")
        elif sys.platform == "linux":
            os.system(f"mpv --no-video '{path}' 2>/dev/null || aplay '{path}' 2>/dev/null || paplay '{path}' 2>/dev/null")
        elif sys.platform == "win32":
            os.system(f'start /wait "" "{path}"')

    # ── Available Voices ────────────────────────────────────────────────

    def list_voices(self) -> List[Dict]:
        """List available voices for the current engine."""
        engine = self._get_engine()
        voices = []

        if engine == TTSEngine.PYTTSX3:
            import pyttsx3
            eng = pyttsx3.init()
            for v in eng.getProperty('voices'):
                voices.append({"id": v.id, "name": v.name, "lang": getattr(v, 'languages', ['unknown'])})

        elif engine == TTSEngine.EDGE_TTS:
            import asyncio
            import edge_tts

            async def _list():
                return await edge_tts.list_voices()

            raw = asyncio.run(_list())
            # Curate the best ones for BRIO
            recommended = [
                "en-GB-RyanNeural",      # Deep British male — BRIO's default
                "en-GB-SoniaNeural",     # British female
                "en-US-GuyNeural",       # American male
                "en-US-JennyNeural",     # American female
                "en-ZA-LeahNeural",      # South African female
                "en-KE-AsiliaNeural",    # Kenyan female
                "en-NG-AbeoNeural",      # Nigerian male
                "en-NG-EzinneNeural",    # Nigerian female
            ]
            for v in raw:
                voices.append({
                    "id": v["ShortName"],
                    "name": v["FriendlyName"],
                    "lang": v["Locale"],
                    "gender": v["Gender"],
                    "recommended": v["ShortName"] in recommended
                })

        return voices

    # ── Recommended voices for BRIO ─────────────────────────────────────

    @staticmethod
    def get_recommended_voices() -> Dict[str, str]:
        """BRIO's curated voice picks for Edge-TTS."""
        return {
            "default": "en-GB-RyanNeural",           # Deep, thoughtful, British
            "warm": "en-US-GuyNeural",                # Warm American male
            "african_male": "en-NG-AbeoNeural",       # Nigerian English male
            "african_female": "en-KE-AsiliaNeural",   # Kenyan English female
            "south_african": "en-ZA-LeahNeural",      # South African female
            "poetic": "en-GB-SoniaNeural",            # British female — good for poetry
        }


# ============================================================================
# STT ENGINE (Speech-to-Text)
# ============================================================================

class STTEngine(Enum):
    VOSK = "vosk"                           # Offline
    SPEECH_RECOGNITION = "speech_recognition"  # Google free tier (online)


class BrioSTT:
    """
    BRIO's ear — listens to voice input and converts to text.

    Usage:
        stt = BrioSTT()
        text = stt.listen()  # Blocks until speech is detected
        print(f"User said: {text}")

        # Or continuous listening with callback
        stt.listen_continuous(callback=lambda text: print(f"Heard: {text}"))
    """

    def __init__(self, preferred_engine: STTEngine = STTEngine.VOSK,
                 vosk_model_path: Optional[str] = None):
        self.preferred_engine = preferred_engine
        self.vosk_model_path = vosk_model_path or "vosk-model-small-en-us-0.15"
        self._available_engines: List[STTEngine] = []
        self._listening = False
        self._detect_available()

    def _detect_available(self):
        """Detect which STT engines are installed."""
        try:
            import vosk
            self._available_engines.append(STTEngine.VOSK)
            log.info("Vosk available (offline STT)")
        except ImportError:
            log.debug("Vosk not installed — run: pip install vosk")

        try:
            import speech_recognition
            self._available_engines.append(STTEngine.SPEECH_RECOGNITION)
            log.info("SpeechRecognition available (Google free STT)")
        except ImportError:
            log.debug("SpeechRecognition not installed — run: pip install SpeechRecognition")

    def _get_engine(self) -> STTEngine:
        if self.preferred_engine in self._available_engines:
            return self.preferred_engine
        for engine in [STTEngine.VOSK, STTEngine.SPEECH_RECOGNITION]:
            if engine in self._available_engines:
                return engine
        raise RuntimeError("No STT engine available")

    # ── Single Listen ───────────────────────────────────────────────────

    def listen(self, timeout: int = 10) -> Optional[str]:
        """
        Listen for a single utterance and return the text.
        Blocks until speech is detected or timeout.
        """
        engine = self._get_engine()

        if engine == STTEngine.SPEECH_RECOGNITION:
            return self._listen_sr(timeout)
        elif engine == STTEngine.VOSK:
            return self._listen_vosk(timeout)

        return None

    def _listen_sr(self, timeout: int) -> Optional[str]:
        """Listen using SpeechRecognition (Google free API)."""
        import speech_recognition as sr
        recogniser = sr.Recognizer()

        try:
            with sr.Microphone() as source:
                log.info("Listening... (SpeechRecognition)")
                recogniser.adjust_for_ambient_noise(source, duration=0.5)
                audio = recogniser.listen(source, timeout=timeout, phrase_time_limit=30)

            text = recogniser.recognize_google(audio)
            return text
        except Exception as e:
            log.warning(f"STT error: {e}")
            return None

    def _listen_vosk(self, timeout: int) -> Optional[str]:
        """Listen using Vosk (fully offline)."""
        import vosk

        if not os.path.exists(self.vosk_model_path):
            log.error(f"Vosk model not found at {self.vosk_model_path}. "
                      f"Download from https://alphacephei.com/vosk/models")
            return None

        model = vosk.Model(self.vosk_model_path)

        try:
            import pyaudio
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16, channels=1,
                rate=16000, input=True, frames_per_buffer=4096
            )
            stream.start_stream()

            rec = vosk.KaldiRecognizer(model, 16000)
            start = time.time()
            result_text = None

            while time.time() - start < timeout:
                data = stream.read(4096, exception_on_overflow=False)
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        result_text = text
                        break

            # Check partial result
            if not result_text:
                final = json.loads(rec.FinalResult())
                result_text = final.get("text", "").strip() or None

            stream.stop_stream()
            stream.close()
            p.terminate()

            return result_text

        except ImportError:
            log.error("pyaudio required for Vosk. Install: pip install pyaudio")
            return None
        except Exception as e:
            log.warning(f"Vosk listen error: {e}")
            return None

    # ── Continuous Listening ────────────────────────────────────────────

    def listen_continuous(self, callback: Callable[[str], None],
                         silence_timeout: float = 2.0):
        """
        Continuously listen and call `callback(text)` for each utterance.
        Runs in a background thread. Call stop_listening() to halt.
        """
        self._listening = True

        def _loop():
            while self._listening:
                text = self.listen(timeout=int(silence_timeout + 5))
                if text and self._listening:
                    callback(text)

        thread = threading.Thread(target=_loop, daemon=True)
        thread.start()
        log.info("Continuous listening started")

    def stop_listening(self):
        """Stop continuous listening."""
        self._listening = False
        log.info("Continuous listening stopped")


# ============================================================================
# VOICE CONVERSATION MANAGER
# ============================================================================

class BrioVoiceConversation:
    """
    Full voice conversation loop: listen → think → speak.

    Usage:
        from brio_voice import BrioVoiceConversation

        def brio_think(user_text: str) -> str:
            # Your BRIO mind logic here
            return f"I heard you say: {user_text}"

        convo = BrioVoiceConversation(think_fn=brio_think)
        convo.start()  # Blocks, listening and responding
    """

    def __init__(self, think_fn: Callable[[str], str],
                 tts_engine: TTSEngine = TTSEngine.EDGE_TTS,
                 stt_engine: STTEngine = STTEngine.VOSK,
                 voice: Optional[str] = None):
        self.think_fn = think_fn
        self.tts = BrioTTS(preferred_engine=tts_engine, voice=voice)
        self.stt = BrioSTT(preferred_engine=stt_engine)
        self.running = False
        self.conversation_log: List[Dict] = []

    def start(self):
        """Start the voice conversation loop (blocking)."""
        self.running = True
        print("[BRIO Voice] Conversation started. Speak to BRIO...")

        # Opening line
        self.tts.speak("I am BRIO. Don't just see; behold. I'm listening.")

        while self.running:
            # Listen
            user_text = self.stt.listen(timeout=15)
            if not user_text:
                continue

            print(f"[You]: {user_text}")

            # Check for exit commands
            if any(cmd in user_text.lower() for cmd in ["goodbye", "stop", "exit", "quit", "shut down"]):
                self.tts.speak("Until we meet again. Farewell.")
                self.running = False
                break

            # Think
            response = self.think_fn(user_text)
            print(f"[BRIO]: {response}")

            # Speak
            self.tts.speak(response)

            # Log
            self.conversation_log.append({
                "user": user_text,
                "brio": response,
                "timestamp": time.time()
            })

    def stop(self):
        self.running = False


# ============================================================================
# FLASK/WEB VOICE INTEGRATION (for Cloud Edition)
# ============================================================================

class BrioWebVoice:
    """
    Voice support for BRIO's web/cloud interface.

    Instead of direct mic access (which requires browser permissions),
    this provides:
    1. TTS endpoint: text → audio file URL
    2. STT via browser's Web Speech API (client-side, free)

    The cloud edition uses the browser's built-in speech recognition
    and sends text to the server. BRIO's response is converted to
    audio server-side and sent back.

    Integration with Flask:
        voice = BrioWebVoice()

        @app.route('/api/tts', methods=['POST'])
        def tts_endpoint():
            text = request.json['text']
            audio_path = voice.generate_audio(text)
            return send_file(audio_path, mimetype='audio/mpeg')
    """

    def __init__(self, voice: str = "en-GB-RyanNeural",
                 output_dir: str = "static/audio"):
        self.tts = BrioTTS(preferred_engine=TTSEngine.EDGE_TTS, voice=voice)
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_audio(self, text: str) -> str:
        """Generate audio file from text. Returns file path."""
        # Create unique filename
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        filename = f"brio_voice_{text_hash}_{int(time.time())}.mp3"
        output_path = os.path.join(self.output_dir, filename)

        self.tts.speak_to_file(text, output_path)
        return output_path

    @staticmethod
    def get_web_speech_js() -> str:
        """
        Returns JavaScript code for browser-side speech recognition.
        Add this to your HTML template. Uses the free Web Speech API.
        """
        return """
// BRIO Web Speech Integration
// Uses browser's built-in Speech Recognition (free, no API key)
class BrioSpeechInput {
    constructor(onResult) {
        this.recognition = null;
        this.onResult = onResult;
        this.isListening = false;

        // Check browser support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.error('Speech Recognition not supported in this browser');
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onresult = (event) => {
            const last = event.results.length - 1;
            const text = event.results[last][0].transcript;
            const isFinal = event.results[last].isFinal;

            if (isFinal && this.onResult) {
                this.onResult(text);
            }
        };

        this.recognition.onerror = (event) => {
            console.error('Speech error:', event.error);
            this.isListening = false;
        };

        this.recognition.onend = () => {
            this.isListening = false;
        };
    }

    start() {
        if (this.recognition && !this.isListening) {
            this.recognition.start();
            this.isListening = true;
        }
    }

    stop() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
            this.isListening = false;
        }
    }
}

// BRIO Audio Playback (TTS responses)
class BrioSpeechOutput {
    async speak(text) {
        try {
            const response = await fetch('/api/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            await audio.play();
        } catch (err) {
            console.error('TTS error:', err);
            // Fallback: browser built-in TTS
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.9;
            window.speechSynthesis.speak(utterance);
        }
    }
}
"""


# ============================================================================
# INSTALL HELPER
# ============================================================================

def check_voice_dependencies() -> Dict[str, bool]:
    """Check which voice dependencies are installed."""
    deps = {}
    for pkg in ["pyttsx3", "gtts", "edge_tts", "vosk", "speech_recognition",
                "pyaudio", "pygame", "pydub"]:
        try:
            __import__(pkg)
            deps[pkg] = True
        except ImportError:
            deps[pkg] = False

    return deps


def install_recommendations() -> str:
    """Return pip install commands for recommended setup."""
    return """
# === BRIO Voice Setup ===

# RECOMMENDED (Cloud Edition — best quality, free):
pip install edge-tts          # Microsoft Edge TTS — 300+ voices, natural
pip install SpeechRecognition # Google free STT (for desktop)

# RECOMMENDED (Desktop Edition — fully offline):
pip install pyttsx3           # Already in requirements.txt
pip install vosk              # Already in requirements.txt
pip install pyaudio           # Needed for microphone access
# Also download a Vosk model:
# wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip

# OPTIONAL (better audio playback):
pip install pygame            # Cross-platform audio playback
pip install pydub             # Audio format conversion

# OPTIONAL (Google Translate TTS — fallback):
pip install gTTS
"""


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    print("=== BRIO Voice System ===")
    print(f"\nDependency check: {check_voice_dependencies()}")
    print(f"\nRecommended voices: {BrioTTS.get_recommended_voices()}")
    print(install_recommendations())

    # Quick TTS test if edge-tts is available
    try:
        tts = BrioTTS()
        print("\nGenerating test audio...")
        tts.speak_to_file(
            "Hello. I am BRIO. Don't just see; behold. My voice module is operational.",
            "brio_voice_test.mp3"
        )
        print("Saved: brio_voice_test.mp3")
    except Exception as e:
        print(f"TTS test skipped: {e}")
