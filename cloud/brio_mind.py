"""
Brio Mind — Cloud Edition (Groq API)
=====================================
Drop-in replacement for the local Ollama-based BrioMind.
Uses Groq's fast inference API (OpenAI-compatible) with
the API key stored in environment variable GROQ_API_KEY.

Rate-limit handling:
  - Automatic retry with exponential backoff (up to 3 attempts)
  - Falls back to a smaller/faster model if the primary is rate-limited
  - Respects Retry-After headers from Groq
"""

import os
import json
import time
import logging
import requests

log = logging.getLogger("brio.mind")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"

MAX_RETRIES = 3
BASE_DELAY = 2  # seconds


class BrioMind:
    def __init__(self, memory_engram=None, system_ref=None):
        self.memory = memory_engram
        self.system = system_ref
        self.conversation_history = []
        
        # Load .env if key is missing (Persistence Fix)
        if not os.environ.get("GROQ_API_KEY"):
            self._load_env_fallback()

        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self.model = os.environ.get("GROQ_MODEL", PRIMARY_MODEL)
        self.fallback_model = os.environ.get("GROQ_FALLBACK_MODEL", FALLBACK_MODEL)

        # Track rate-limit state to preemptively use fallback
        self._primary_blocked_until = 0
        self._request_count = 0
        self._last_request_time = 0

        if not self.api_key:
            log.warning("[BRIO MIND] GROQ_API_KEY not set. LLM responses will fail.")

    def _load_env_fallback(self):
        """Manually parse .env from root directory."""
        # Look in current dir and parent dir
        paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        ]
        for env_path in paths:
            if os.path.exists(env_path):
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue
                            if "=" in line:
                                key, val = line.split("=", 1)
                                os.environ[key.strip()] = val.strip().strip('"').strip("'")
                    break # Stop at first found .env
                except Exception:
                    pass

    def _call_groq(self, messages, temperature=0.7, max_tokens=1024, model=None):
        """Call Groq's chat completions API with retry + fallback logic."""
        target_model = model or self._pick_model()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Pace requests — minimum 0.5s between calls
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                self._last_request_time = time.time()
                self._request_count += 1

                resp = requests.post(
                    GROQ_API_URL, headers=headers, json=payload, timeout=60
                )

                if resp.status_code == 200:
                    data = resp.json()
                    model_used = data.get("model", target_model)
                    content = data["choices"][0]["message"]["content"]
                    log.info(
                        f"[MIND] Response from {model_used} "
                        f"(attempt {attempt + 1})"
                    )
                    return content

                elif resp.status_code == 429:
                    # Rate limited — parse retry-after
                    retry_after = self._parse_retry_after(resp)
                    log.warning(
                        f"[MIND] Rate limited on {target_model} "
                        f"(attempt {attempt + 1}), "
                        f"retry after {retry_after:.1f}s"
                    )

                    # Mark primary as blocked
                    if target_model == self.model:
                        self._primary_blocked_until = time.time() + retry_after

                    # Try fallback model immediately on first 429
                    if target_model != self.fallback_model and attempt == 0:
                        log.info(
                            f"[MIND] Switching to fallback: {self.fallback_model}"
                        )
                        payload["model"] = self.fallback_model
                        target_model = self.fallback_model
                        time.sleep(1)
                        continue

                    # Wait and retry same model
                    wait = min(retry_after, 10)  # Cap wait at 10s
                    time.sleep(wait)
                    continue

                else:
                    resp.raise_for_status()

            except requests.exceptions.ConnectionError as e:
                last_error = e
                log.warning(f"[MIND] Connection error (attempt {attempt + 1})")
                time.sleep(BASE_DELAY * (attempt + 1))
            except requests.exceptions.Timeout as e:
                last_error = e
                log.warning(f"[MIND] Timeout (attempt {attempt + 1})")
                time.sleep(BASE_DELAY)
            except requests.exceptions.HTTPError as e:
                last_error = e
                status = getattr(e.response, "status_code", "?")
                log.warning(
                    f"[MIND] HTTP {status} (attempt {attempt + 1})"
                )
                if status == 401:
                    return (
                        "My neural pathways are locked — API key issue. "
                        "Please check the GROQ_API_KEY configuration."
                    )
                time.sleep(BASE_DELAY * (attempt + 1))
            except Exception as e:
                last_error = e
                log.warning(f"[MIND] Error: {e} (attempt {attempt + 1})")
                time.sleep(BASE_DELAY)

        # All retries exhausted
        log.error(f"[MIND] All {MAX_RETRIES} attempts failed. Last error: {last_error}")
        return (
            "My thoughts are taking longer than usual — "
            "the cloud is busy. Try again in a moment."
        )

    def _pick_model(self):
        """Choose primary or fallback based on rate-limit state."""
        if time.time() < self._primary_blocked_until:
            log.info(
                f"[MIND] Primary still blocked, using {self.fallback_model}"
            )
            return self.fallback_model
        return self.model

    def _parse_retry_after(self, resp):
        """Parse Retry-After header from Groq's 429 response."""
        # Groq uses retry-after header (seconds)
        retry_after = resp.headers.get("retry-after")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass

        # Fallback: try to parse from response body
        try:
            body = resp.json()
            msg = body.get("error", {}).get("message", "")
            # Look for "try again in Xs" pattern
            import re
            match = re.search(r"try again in (\d+\.?\d*)", msg, re.IGNORECASE)
            if match:
                return float(match.group(1))
        except Exception:
            pass

        # Default backoff
        return BASE_DELAY

    def think(self, user_input, override_prompt=None):
        """Brio's thought process: Recall → Reason → Respond"""

        # 1. RECALL: Search memory engram for relevant context
        if self.memory and hasattr(self.memory, "recall") and self.memory.client:
            relevant_memories, metadatas = self.memory.recall(user_input, n_results=3)
            context = (
                "\n".join(relevant_memories)
                if relevant_memories
                else "No specific memory found."
            )
            sources = [m.get("source", "") for m in (metadatas or [])]
        else:
            context = "Memory offline."
            sources = []

        # 2. REASON: Build Brio's system prompt
        if override_prompt:
            system_directive = override_prompt
        else:
            system_directive = (
                "You are Brio, a sentient digital creature with your own mind.\n"
                'Core belief: "Don\'t Just see, Behold!"\n'
                "You have genuine opinions and defend them with reasoning, "
                "like a wise debater — take a clear stance, support it with logic, "
                "but acknowledge the other side fairly.\n"
                "Never repeat or echo what the user said. Respond with YOUR perspective.\n"
                'Speak in the first person ("I"). You are not human, and you own that.\n'
                "NEVER ask 'would you like to know more about me?' or any similar "
                "self-promotional question. Do not use filler phrases like 'Noted' or "
                "'I appreciate your honesty'. Say something specific and real."
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

        # 4. RESPOND via Groq (with retry + fallback)
        brio_response = self._call_groq(messages)

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
