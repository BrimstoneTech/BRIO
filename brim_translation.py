
"""
BRIM Sunbird AI Translation Module (brim_translation.py)

Purpose: Interfaces with Sunbird AI REST APIs for Neural Machine Translation.
Supported Languages: Luganda (lug), Acholi (ach), Ateso (teo), Lugbara (lgg), Runyankore (nyn), Swahili (sw).
"""

import os
import requests
from typing import Optional, Dict

class SunbirdTranslator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SUNBIRD_API_KEY")
        self.base_url = "https://api.sunbird.ai/tasks/nmt"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def translate(self, text: str, source_lang: str = "eng", target_lang: str = "lug") -> str:
        """Translates text between supported languages."""
        if not self.api_key:
            return f"[Error] Sunbird API key not configured. Cannot translate '{text}'."

        payload = {
            "source_language": source_lang,
            "target_language": target_lang,
            "text": text
        }
        
        try:
            response = requests.post(self.base_url, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("translated_text", f"[Error] Translation failed for: {text}")
        except Exception as e:
            return f"[Error] Connection to Sunbird AI failed: {e}"

    def get_supported_languages(self) -> Dict[str, str]:
        return {
            "eng": "English",
            "lug": "Luganda",
            "ach": "Acholi",
            "teo": "Ateso",
            "lgg": "Lugbara",
            "nyn": "Runyankore",
            "sw": "Swahili"
        }

if __name__ == "__main__":
    # Quick Test
    translator = SunbirdTranslator(api_key="test_key")
    print(translator.get_supported_languages())
    print(translator.translate("Hello, how are you?", source_lang="eng", target_lang="lug"))
