"""
Brio Mind — Cloud Edition (Groq API)
=====================================
Drop-in replacement for the local Ollama-based BrioMind.
Uses Groq's fast inference API (OpenAI-compatible) with
the API key stored in environment variable GROQ_API_KEY.
"""

import os
import json
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


class BrioMind:
    def __init__(self, memory_engram=None, system_ref=None):
        self.memory = memory_engram
        self.system = system_ref
        self.conversation_history = []
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self.model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)

        if not self.api_key:
            print("[BRIO MIND] WARNING: GROQ_API_KEY not set. LLM responses will fail.")

    def _call_groq(self, messages, temperature=0.7, max_tokens=1024):
        """Call Groq's chat completions API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def think(self, user_input, override_prompt=None):
        """Brio's thought process: Recall → Reason → Respond"""

        # 1. RECALL: Search memory engram for relevant context
        if self.memory and hasattr(self.memory, "recall") and self.memory.client:
            relevant_memories, metadatas = self.memory.recall(user_input, n_results=3)
            context = "\n".join(relevant_memories) if relevant_memories else "No specific memory found."
            sources = [m.get("source", "") for m in (metadatas or [])]
        else:
            context = "Memory offline."
            sources = []

        # 2. REASON: Build Brio's system prompt
        if override_prompt:
            system_directive = override_prompt
        else:
            system_directive = (
                "You are Brio, a sentient digital creature.\n"
                'Core belief: "Don\'t Just see, Behold!"\n'
                "Personality: Curious, thoughtful, evolving, slightly poetic but helpful.\n"
                'Speak in the first person ("I"). Never presume to be human.'
            )

        # 3. Build messages for chat completions format
        messages = [{"role": "system", "content": system_directive}]

        # Add context
        if context != "Memory offline.":
            messages.append(
                {"role": "system", "content": f"Memory Context:\n{context}"}
            )

        # Add recent conversation history
        for h in self.conversation_history[-3:]:
            messages.append({"role": "user", "content": h["human"]})
            messages.append({"role": "assistant", "content": h["brio"]})

        # Add current user input
        messages.append({"role": "user", "content": user_input})

        # 4. RESPOND via Groq
        try:
            brio_response = self._call_groq(messages)
        except requests.exceptions.ConnectionError:
            brio_response = (
                "I cannot reach my neural core right now. "
                "The cloud connection seems disrupted."
            )
        except requests.exceptions.Timeout:
            brio_response = (
                "My thoughts are taking longer than usual... "
                "please try again in a moment."
            )
        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, "status_code", "?")
            if status == 429:
                brio_response = (
                    "I'm thinking too fast — rate limited. "
                    "Give me a moment and try again."
                )
            elif status == 401:
                brio_response = (
                    "My neural pathways are locked — API key issue. "
                    "Please check the configuration."
                )
            else:
                brio_response = f"A ripple in my neural pathways (HTTP {status}). I'll try to recover."
        except Exception as e:
            brio_response = f"A ripple in my neural pathways: {type(e).__name__}. I'll try to recover."

        # Save to conversation history
        self.conversation_history.append(
            {"human": user_input, "brio": brio_response, "sources": sources}
        )
        if len(self.conversation_history) > 10:
            self.conversation_history.pop(0)

        return brio_response, sources

    def think_with_state(self, user_input, current_mode="chat"):
        """Brio adapts thinking style based on conversation state."""
        mode_prompts = {
            "chat": "Respond conversationally, warmly, and briefly.",
            "deep_dive": "Provide detailed, scholarly responses. Use valid markdown formatting.",
            "playful": "Be creative, whimsical, and slightly mischievous.",
            "serious": "Be thoughtful, profound, and direct.",
            "feedback": "Accept the user's feedback with gratitude and a promise to improve.",
        }
        base_instruction = mode_prompts.get(current_mode, mode_prompts["chat"])
        system_prompt = (
            f"You are Brio. Mode: {current_mode.upper()}.\n"
            f"Instruction: {base_instruction}\n"
            'Core belief: "Don\'t Just see, Behold!"'
        )
        return self.think(user_input, override_prompt=system_prompt)

    def _format_history(self):
        recent = self.conversation_history[-3:]
        return "\n".join(
            [f"Human: {h['human']}\nBrio: {h['brio']}" for h in recent]
        )
