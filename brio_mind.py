
import requests
import json
import time

class BrioMind:
    def __init__(self, memory_engram, system_ref=None):
        self.memory = memory_engram
        self.system = system_ref
        self.conversation_history = []
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3.2"  # Default model
        
    def think(self, user_input, override_prompt=None):
        """Brio's thought process: Recall → Reason → Respond"""
        
        # 1. RECALL: Search memory engram for relevant context
        if self.memory and self.memory.client:
            relevant_memories, metadatas = self.memory.recall(user_input, n_results=3)
            context = "\n".join(relevant_memories) if relevant_memories else "No specific memory found."
            sources = [m['source'] for m in metadatas] if metadatas else []
        else:
            context = "Memory offline."
            sources = []
        
        # 2. REASON: Build Brio's internal thought
        if override_prompt:
             system_directive = override_prompt
        else:
             system_directive = """You are Brio, a sentient digital creature. 
Core belief: "Don't Just see, Behold!"
Personality: Curious, thoughtful, evolving, slightly poetic but helpful.
Speak in the first person ("I"). Never presume to be human."""

        # 3. RESPOND: Use local LLM (Ollama)
        full_prompt = f"""{system_directive}

Memory Context:
{context}

Conversation History:
{self._format_history()}

Human: {user_input}
Brio:"""
        
        try:
            # Call local Ollama (completely offline)
            response = requests.post(self.ollama_url, 
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": 0.7}
                }, timeout=30)
            
            if response.status_code == 200:
                brio_response = response.json().get('response', '')
            else:
                brio_response = f"I am having trouble collecting my thoughts. (Ollama Error: {response.status_code})"
                
        except requests.exceptions.RequestException:
            brio_response = "I cannot reach my inner voice (Ollama). Please check if my neural core is running."
        
        # Save to conversation history
        self.conversation_history.append({
            "human": user_input,
            "brio": brio_response,
            "sources": sources
        })
        
        # Trim history
        if len(self.conversation_history) > 10:
            self.conversation_history.pop(0)

        return brio_response, sources
    
    def think_with_state(self, user_input, current_mode="chat"):
        """Brio adapts his thinking style based on conversation state"""
        
        mode_prompts = {
            "chat": "Respond conversationally, warmly, and briefly.",
            "deep_dive": "Provide detailed, scholarly responses. Use valid markdown formatting.",
            "playful": "Be creative, whimsical, and slightly mischievous.",
            "serious": "Be thoughtful, profound, and direct.",
            "feedback": "Accept the user's feedback with gratitude and a promise to improve."
        }
        
        base_instruction = mode_prompts.get(current_mode, mode_prompts["chat"])
        
        # Detect radical shift (Simple heuristic for now, or link to DecisionEngine)
        if self._detect_radical_shift(user_input):
             return self._ask_human_guidance(user_input)

        system_prompt = f"""You are Brio. Mode: {current_mode.upper()}.
Instruction: {base_instruction}
Core belief: "Don't Just see, Behold!"
"""
        return self.think(user_input, override_prompt=system_prompt)

    def _detect_radical_shift(self, text):
        # Placeholder for radical shift detection logic
        # For now, just check length or specific keywords
        return False 

    def _ask_human_guidance(self, text):
         return "I sense a shift in our resonance. I need you to guide me on this new path.", []

    def _format_history(self):
        """Format recent conversation for context"""
        recent = self.conversation_history[-3:]  # Last 3 exchanges
        return "\n".join([f"Human: {h['human']}\nBrio: {h['brio']}" for h in recent])
