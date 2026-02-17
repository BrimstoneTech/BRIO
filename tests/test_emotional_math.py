
import sys
import os
sys.path.append(os.getcwd())

from brio_emotions import EmotionEngine, EmotionTrigger
from brio_communication import CommunicationCycle

def test_emotional_math():
    engine = EmotionEngine()
    cycle = CommunicationCycle(sender="Brio", receiver="Human")
    
    def mock_transmit(msg):
        print(f"Final Transmitted Message: {msg}")

    # Case 1: Neutral / Positive State
    print("\n--- CASE 1: Positive/Confident State ---")
    engine.state.joy = 0.8
    engine.state.confidence = 0.9
    engine.state.frustration = 0.1
    
    v = engine.state.get_valence()
    a = engine.state.get_arousal()
    intensity = engine.state.math_intensity()
    print(f"Valence: {v:.2f}, Arousal: {a:.2f}, Intensity: {intensity:.2f}")
    
    cycle.reception("System check complete.")
    cycle.decode("NL")
    cycle.set_context("Standard Interaction", engine.state)
    cycle.encode("I am functioning at peak efficiency.")
    cycle.transmit(mock_transmit)
    
    print(f"Output Clarity: {cycle.clarity:.2f}")
    print(f"Encoding Strength: {cycle.encoding_strength:.2f}")

    # Case 2: Negative / Frustrated State
    print("\n--- CASE 2: Negative/Frustrated State ---")
    engine.state.joy = 0.1
    engine.state.confidence = 0.2
    engine.state.frustration = 0.9
    engine.state.concern = 0.8
    
    v = engine.state.get_valence()
    a = engine.state.get_arousal()
    intensity = engine.state.math_intensity()
    print(f"Valence: {v:.2f}, Arousal: {a:.2f}, Intensity: {intensity:.2f}")
    
    cycle.reset()
    cycle.reception("Is there an issue?")
    cycle.decode("NL", noise_level=0.5)
    cycle.set_context("System Anomaly", engine.state)
    cycle.encode("There is a significant disruption in neural synchronization.")
    cycle.transmit(mock_transmit)
    
    print(f"Output Clarity: {cycle.clarity:.2f}")
    print(f"Encoding Strength: {cycle.encoding_strength:.2f}")

if __name__ == "__main__":
    test_emotional_math()


