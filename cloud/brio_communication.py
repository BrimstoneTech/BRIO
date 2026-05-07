"""
Brio Communication Module (brio_communication.py)

Purpose: Structured communication cycle for Brio interaction logic.
Implementation of the CommunicationCycle model adapted for Brio.
"""

import time
from typing import Optional, Any

class CommunicationCycle:
    def __init__(self, sender: str, receiver: str):
        self.sender = sender
        self.receiver = receiver
        self.message = None
        self.encoded_message = None
        self.channel = None
        self.decoded_message = None
        self.feedback = None
        self.context = None
        self.emotion_state = None  # Reference to brio_emotions.EmotionalState
        self.noise = 0.0  # Represents ambiguity/entropy
        self.clarity = 1.0
        self.encoding_strength = 1.0
        self.stages = []

    def log_stage(self, stage: str, details: str):
        self.stages.append({"stage": stage, "time": time.time(), "details": details})
        print(f"[Cycle] {stage}: {details}")

    def reception(self, content: str):
        """Step 1: Receive the raw input."""
        self.message = content
        self.decoded_message = content  # Passthrough until decode() is called
        self.log_stage("Reception", f"Raw input: {content}")

    def decode(self, encoding_method: str, noise_level: float = 0.0):
        """Step 2: Decode intent and identify noise."""
        self.noise = noise_level
        self.decoded_message = content = self.message # Simple bypass for now
        self.log_stage("Decoding", f"Decoded message: {self.decoded_message} (Noise: {self.noise:.2f})")

    def cognition(self, process_callback):
        """Step 3: Internal reasoning (Cognition)."""
        self.log_stage("Cognition", "Processing internal logic...")
        result = process_callback(self.decoded_message)
        self.log_stage("Cognition", f"Cognitive Output: {result}")
        return result

    def set_context(self, context: str, emotion_state: Any):
        """Step 4: Align with emotional context and capture state for math influence."""
        self.context = context
        self.emotion_state = emotion_state
        
        # Calculate mathematical influences
        if hasattr(emotion_state, 'calculate_influence'):
            self.clarity = emotion_state.calculate_influence(1.0, max_influence=0.4)
            self.encoding_strength = emotion_state.calculate_influence(1.0, max_influence=0.3)
            
        details = f"Context: {context} | Clarity: {self.clarity:.2f} | Strength: {self.encoding_strength:.2f}"
        self.log_stage("Context", details)

    def encode(self, output_content: str, format_method: str = "Natural Language"):
        """Step 5: Encode output, influenced by emotional state."""
        self.encoded_message = output_content
        # Add visual indicator of clarity/strength for transparency
        self.encoded_message_formatted = f"[{format_method}] (C:{self.clarity:.2f}/S:{self.encoding_strength:.2f}) {output_content}"
        self.log_stage("Encoding", f"Encoded as: {format_method} (Strength: {self.encoding_strength:.2f})")

    def transmit(self, transmit_callback):
        """Step 6: Transmit to receiver, accounting for noise and disruption."""
        disruption = 0.0
        if self.noise > 0 and self.emotion_state:
            # Multiplicative disruption from noise * emotional intensity
            intensity_ratio = self.emotion_state.math_intensity() / 14.14
            disruption = self.noise * intensity_ratio
            
        self.log_stage("Transmission", f"Transmitting via {self.channel} (Disruption: {disruption:.2f})")
        transmit_callback(self.encoded_message)

    def process_feedback(self, feedback: str):
        """Step 7: Record feedback loop."""
        self.feedback = feedback
        self.log_stage("Feedback", f"Receiver feedback: {feedback}")

    def reset(self):
        """Prepare for next cycle."""
        self.message = None
        self.encoded_message = None
        self.decoded_message = None
        self.feedback = None
        self.context = None
        self.noise = 0.0
        self.stages = []


