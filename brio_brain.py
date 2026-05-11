"""
Brio Brain Orchestrator (brio_brain.py)

Purpose: Central 'Sifting' Engine for Brio v4.5.
         Uses LangGraph to coordinate between identity, memory, and emotion.
"""

import os
from typing import Dict, List, Optional
from langgraph.graph import StateGraph, END
from brio_cognition import BrioState, DecisionEngine, EntropyCalculator
import operator

class BrioBrain:
    def __init__(self, system_ref):
        self.system = system_ref # Reference to BrioSystem for component access
        self.builder = StateGraph(BrioState)
        
        # 1. Define Nodes
        self.builder.add_node("brio_think", self.brio_core)
        self.builder.add_node("human_checkpoint", self.human_checkpoint)
        self.builder.add_node("human_clarification", self.human_clarification)
        self.builder.add_node("memory_update", self.memory_update)
        self.builder.add_node("web_sift", self.web_sift_node)
        self.builder.add_node("local_action", self.local_action_node)   # ← Autonomy
        self.builder.add_node("agent_action", self.agent_action_node)   # ← GUI Agent
        
        # 2. Define Edges
        self.builder.set_entry_point("brio_think")
        self.builder.add_conditional_edges(
            "brio_think",
            self.route_conversation,
            {
                "human_checkpoint": "human_checkpoint",
                "human_clarification": "human_clarification",
                "memory_update": "memory_update",
                "web_sift": "web_sift",
                "local_action": "local_action",   # ← Autonomy route
                "agent_action": "agent_action",   # ← GUI route
            }
        )
        
        self.builder.add_conditional_edges(
            "human_checkpoint",
            self.decide_post_guide,
            {
                "continue": "memory_update",
                "rethink": "brio_think",
                "end": END
            }
        )
        self.builder.add_edge("human_clarification", END)
        self.builder.add_edge("web_sift", "memory_update")
        self.builder.add_edge("local_action", END)   # Local actions don't need memory update
        self.builder.add_edge("agent_action", END)   # Agent actions don't need memory update
        self.builder.add_edge("memory_update", END)
        
        # 3. Neural Cache & Working Memory
        from brio_web_sifter import WebSifter
        self.web_sifter = WebSifter(self.system)
        self.neural_cache = {}
        self.working_memory = []
        self.max_working_mem = 10
        
        # 3. Compile
        self.graph = self.builder.compile()

    def brio_core(self, state: BrioState):
        """BRIO's core personality & neural processing"""
        prompt = state["last_message"]
        
        # 0. Intent Classification (v4.0 Natural Intuition)
        intent = DecisionEngine.classify_intent(prompt)
        
        # 1. Visual Context Awareness (Vision v4.0)
        visual_info = None
        if intent == "vision":
            from brio_vision import VisionEngine
            ve = VisionEngine()
            visual_info = ve.analyze_context(prompt)

        # 2. Neural Cache Check (Speed Optimization)
        if prompt.lower() in self.neural_cache and intent == "chat":
            return {"response": self.neural_cache[prompt.lower()], "confusion": 0.0, "intent": intent}

        # 3. Emotional Calibration & Sifting
        dom_emotion = self.system.emotions.get_dominant_emotion().value
        intensity = self.system.emotions.get_intensity()
        
        # 4. Neural Context Recall (Working Memory + Engrams)
        context = " ".join(self.working_memory)
        keywords = [w for w in prompt.split() if len(w) > 3]
        memories = self.system.knowledge.associative_recall(emotion=dom_emotion, keywords=keywords)
        
        # 5. Calculate Confusion & Severity
        confusion = 1.0 - intensity if not memories and intent != "feedback" else 0.2
        severity = DecisionEngine.detect_radical_shift(state)

        # 6. Generate Response (Priority: Local Mind > Kimi > Error)
        response = ""
        
        # Try Local Mind (Ollama + RAG)
        if getattr(self.system, 'mind', None):
            # Pass visual context if available
            if visual_info:
                prompt = f"[Visual Context: {visual_info}] {prompt}"
            
            # Using think_with_state for adaptive personality
            current_mode = state.get("current_mode", "companion")
            response, sources = self.system.mind.think_with_state(prompt, current_mode)
            
            if sources:
                response += f"\n\n[Sources: {', '.join(set(sources))}]"

        # Fallback to silence if Local Mind failed
        else:
            response = "My mind is silent. I cannot reach my internal archives."
        
        # 7. Update Cache
        if len(self.neural_cache) < 100:
            self.neural_cache[prompt.lower()] = response

        return {
            "response": response, 
            "confusion": confusion, 
            "topic_shift_severity": severity,
            "intent": intent,
            "visual_context": visual_info
        }

    def route_conversation(self, state: BrioState):
        """State-driven routing with v4.5 Intuition + Autonomy"""
        intent = state.get("intent", "chat")
        
        # ── Autonomy routes (highest priority — bypass Ollama) ────────────────
        if intent == "local":
            return "local_action"
        if intent == "agent":
            return "agent_action"
        
        # ── Standard routes ───────────────────────────────────────────────────
        if intent == "feedback":
            return "memory_update"
        if intent == "query":
            return "web_sift"
        if state.get("confusion", 0) > 0.8:
            return "human_clarification"
        elif state.get("topic_shift_severity") == "radical":
            return "human_checkpoint"
        else:
            return "memory_update"

    def decide_post_guide(self, state: BrioState) -> str:
        """Determines next step after human checkpoint"""
        if state.get("human_approved"):
            return "rethink"
        return "end"

    def web_sift_node(self, state: BrioState):
        """Knowledge Expansion node (v4.0)"""
        query = state["last_message"]
        sift_result = self.web_sifter.search_and_ingest(query)
        self.system.desktop_ui.show_thought("Sifting the web for excellence...", duration_sec=3)
        return {"response": f"{state['response']}\n\n[Sifter Intel]: {sift_result}"}

    def human_checkpoint(self, state: BrioState):
        """Interrupt for human guidance (v4.0 Natural shift)"""
        self.system.desktop_ui.show_thought("I'm sensing a shift in our resonance. Should I adapt?", duration_sec=5)
        return {"requires_human": True, "response": state["response"]}

    def human_clarification(self, state: BrioState):
        """Node for natural clarification questions"""
        msg = "I'm having trouble sifting through that. Could you clarify your intent?"
        self.system.desktop_ui.show_thought(msg, duration_sec=5)
        return {"response": msg}

    def memory_update(self, state: BrioState):
        """Final node: Persistent wisdom + Behavioral adaptation"""
        res = state["response"]
        intent = state.get("intent", "chat")
        
        if intent == "feedback":
            praise = any(w in state["last_message"].lower() for w in ["good", "yes", "excellent", "nice"])
            if praise:
                self.system.emotions.apply_trigger("joy", 0.5)
                self.system.neural.evolve(1, 1, 0.8)
            else:
                self.system.emotions.apply_trigger("frustration", 0.5)
        
        if res and "error" not in res.lower():
            # Update Working Memory
            self.working_memory.append(res)
            if len(self.working_memory) > self.max_working_mem:
                self.working_memory.pop(0)

            self.system.knowledge.learn(
                res, 
                emotion=self.system.emotions.get_dominant_emotion().value,
                importance=0.9 if intent == "feedback" else 0.7
            )
        return state

    # ─── Autonomy Nodes ───────────────────────────────────────────────────────

    def local_action_node(self, state: BrioState):
        """
        Routes local machine commands to BrioAutonomy.
        Bypasses Ollama entirely — direct execution with safety gate.
        """
        user_input = state["last_message"]
        response = ""

        if getattr(self.system, 'autonomy', None):
            result = self.system.autonomy.handle(user_input)
            response = result if result is not None else "I wasn't sure how to handle that locally."
        else:
            # Fallback: autonomy not loaded, try the local_access module directly
            if getattr(self.system, 'local', None):
                response = self.system.local.handle_command(user_input) or "Local access returned no result."
            else:
                response = "Local access is not initialized."

        # Show thought in UI
        self.system.desktop_ui.show_thought(response[:200], duration_sec=6)
        return {"response": response, "intent": "local"}

    def agent_action_node(self, state: BrioState):
        """
        Routes GUI automation commands to BrioAutonomy (desktop agent).
        """
        user_input = state["last_message"]
        response = ""

        if getattr(self.system, 'autonomy', None):
            result = self.system.autonomy.handle(user_input)
            response = result if result is not None else "GUI task queued."
        else:
            response = "Desktop agent (autonomy module) is not initialized."

        self.system.desktop_ui.show_thought(response[:200], duration_sec=6)
        return {"response": response, "intent": "agent"}

    def process_interaction(self, user_input: str):
        """Entry point for the Brain (v4.0)"""
        if user_input.lower().startswith("guide ") and self.last_state and self.last_state.get("requires_human"):
            return self.resume_with_guidance(user_input[6:])

        initial_state = {
            "brio_identity": {"name": self.system.custom_name, "version": "v4.5"},
            "conversation_history": [{"role": "user", "content": user_input}],
            "emotional_state": {"joy": 0.5},
            "complexity_score": self.system.neural.complexity_score,
            "confusion": 0.0,
            "intent": "chat",
            "visual_context": None,
            "working_memory": self.working_memory,
            "topic_shift_severity": "normal",
            "current_mode": "companion",
            "requires_human": False,
            "human_approved": False,
            "last_message": user_input,
            "response": ""
        }
        
        final_state = self.graph.invoke(initial_state)
        self.last_state = final_state
        return final_state["response"]

    def resume_with_guidance(self, feedback: str):
        """Resumes the graph with natural feedback"""
        if not self.last_state: return "No pending state."
        self.last_state["human_approved"] = True
        self.last_state["conversation_history"].append({"role": "user", "content": f"GUIDANCE: {feedback}"})
        final_state = self.graph.invoke(self.last_state)
        self.last_state = None
        return final_state['response']


