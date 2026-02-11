
"""
BRIM Sunbird AI Integration Module (brim_sunbird.py)

Purpose: Consolidates all Sunbird AI REST APIs into a single service layer.
Services: Translation (NMT), Speech-to-Text (STT), Text-to-Speech (TTS), 
          Language ID, and Sunflower Conversational AI.
"""

import os
import requests
import io
import wave
from typing import Optional, Dict, List, Any

class SunbirdService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SUNBIRD_API_KEY")
        self.base_url = "https://api.sunbird.ai/tasks"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "accept": "application/json"
        }

    def _post(self, endpoint: str, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Dict:
        if not self.api_key:
            return {"error": "Sunbird API key not configured."}
        
        url = f"{self.base_url}/{endpoint}"
        try:
            if files:
                # For multipart/form-data (STT)
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
            else:
                response = requests.post(url, headers=self.headers, json=data, timeout=15)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    # 1. Translation (NMT)
    def translate(self, text: str, source_lang: str = "eng", target_lang: str = "lug") -> str:
        data = {
            "source_language": source_lang,
            "target_language": target_lang,
            "text": text
        }
        result = self._post("translate", data)
        return result.get("translated_text", result.get("error", "Translation Failed"))

    # 2. Text-to-Speech (TTS)
    def tts(self, text: str, language: str = "lug") -> Optional[bytes]:
        url = f"{self.base_url}/modal/tts"
        data = {"text": text, "language": language, "response_mode": "stream"}
        try:
            # TTS stream can be binary
            response = requests.post(url, headers=self.headers, json=data, timeout=20)
            response.raise_for_status()
            return response.content
        except:
            return None

    # 3. Speech-to-Text (STT)
    def stt(self, audio_path: str, language: Optional[str] = None) -> str:
        with open(audio_path, "rb") as f:
            files = {"audio": ("recording.wav", f, "audio/wav")}
            data = {"language": language} if language else {}
            result = self._post("modal/stt", data=data, files=files)
            return result.get("audio_transcription", result.get("error", "STT Failed"))

    # 4. Language Identification
    def detect_language(self, text: str) -> str:
        data = {"text": text}
        result = self._post("language_id", data)
        if isinstance(result, str): return result
        return result.get("language", "unknown")

    # 5. Sunflower Conversational AI
    def sunflower_ask(self, text: str, source_lang: str = "lug", target_lang: str = "lug") -> str:
        data = {
            "text": text,
            "source_language": source_lang,
            "target_language": target_lang,
            "instruction": "You are Brio, a helpful Ugandan AI assistant."
        }
        result = self._post("sunflower_simple", data)
        return result.get("output", result.get("error", "Sunflower Error"))

    def get_supported_languages(self) -> Dict[str, str]:
        return {
            "eng": "English",
            "lug": "Luganda",
            "nyn": "Runyankole",
            "ach": "Acholi",
            "teo": "Ateso",
            "lgg": "Lugbara",
            "sw": "Swahili"
        }
