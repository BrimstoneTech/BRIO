"""
Brio Neuromorphic Architecture Module (brio_neuromorphic.py)

Purpose: Emulates biological neural network behaviour for BRIO.
         Spiking neurons, Hebbian learning ("neurons that fire together
         wire together"), and pattern completion from partial input.

Concepts:
- Spiking Neurons: Neurons accumulate potential and fire when threshold
  is reached, then enter a refractory (rest) period — like real brains
- Hebbian Learning: Connections strengthen when neurons co-activate
- Pattern Completion: Given partial input, the network reconstructs
  the full pattern from learned associations
- Sparse Distributed Representations: Concepts are encoded across
  many neurons, giving robustness and generalisation

This replaces the simple NeuralNetwork class in brio_neural.py with
a biologically-inspired architecture that actually learns patterns.

Author: BrimstoneTech
Version: 1.0
Dependencies: None (stdlib only)
"""

import math
import random
import time
import json
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


# ============================================================================
# SPIKING NEURON MODEL (Leaky Integrate-and-Fire)
# ============================================================================

@dataclass
class SpikingNeuron:
    """
    Leaky Integrate-and-Fire (LIF) neuron.

    Membrane potential accumulates from inputs, leaks over time,
    and fires a spike when it crosses threshold. After firing,
    enters a refractory period where it cannot fire again.

    dV/dt = -(V - V_rest) / tau + I_input
    if V >= V_threshold: SPIKE, then V = V_reset for t_refract steps
    """
    neuron_id: str
    membrane_potential: float = 0.0
    threshold: float = 1.0
    reset_potential: float = 0.0
    rest_potential: float = 0.0
    leak_rate: float = 0.05          # tau inverse — how fast potential decays
    refractory_period: int = 2       # steps after firing where neuron is silent
    _refractory_counter: int = 0
    _spike_count: int = 0
    _last_spike_time: float = 0.0

    @property
    def is_refractory(self) -> bool:
        return self._refractory_counter > 0

    def receive_input(self, current: float):
        """Accumulate input current (from synapses)."""
        if not self.is_refractory:
            self.membrane_potential += current

    def step(self) -> bool:
        """
        Advance one time step. Returns True if neuron fires.
        """
        if self.is_refractory:
            self._refractory_counter -= 1
            return False

        # Leak toward rest
        self.membrane_potential -= self.leak_rate * (self.membrane_potential - self.rest_potential)

        # Check threshold
        if self.membrane_potential >= self.threshold:
            # FIRE
            self.membrane_potential = self.reset_potential
            self._refractory_counter = self.refractory_period
            self._spike_count += 1
            self._last_spike_time = time.time()
            return True

        return False


# ============================================================================
# SYNAPSE WITH HEBBIAN LEARNING
# ============================================================================

@dataclass
class Synapse:
    """
    Connection between two neurons with Hebbian plasticity.

    Hebbian rule: If pre fires and post fires within a time window,
    strengthen the connection. If pre fires but post doesn't, weaken.

    dw/dt = eta * (pre_spike * post_spike - decay * w)
    """
    pre_id: str
    post_id: str
    weight: float = 0.1
    learning_rate: float = 0.01      # eta
    decay_rate: float = 0.001        # Synaptic weight decay
    max_weight: float = 1.0
    min_weight: float = 0.0

    def hebbian_update(self, pre_fired: bool, post_fired: bool):
        """
        Apply Hebbian learning rule.
        - Both fire: strengthen (Long-Term Potentiation)
        - Pre fires, post doesn't: weaken slightly (Long-Term Depression)
        """
        if pre_fired and post_fired:
            # LTP: neurons that fire together wire together
            self.weight += self.learning_rate * (1.0 - self.weight)
        elif pre_fired and not post_fired:
            # LTD: mild weakening
            self.weight -= self.learning_rate * 0.3 * self.weight

        # Natural decay
        self.weight -= self.decay_rate * self.weight

        # Clamp
        self.weight = max(self.min_weight, min(self.max_weight, self.weight))


# ============================================================================
# NEUROMORPHIC NETWORK
# ============================================================================

class NeuromorphicNetwork:
    """
    A spiking neural network with Hebbian learning for BRIO.

    Architecture:
    - Input layer: encodes text/concepts as spike patterns
    - Hidden layer: associative memory (learns patterns)
    - Output layer: reconstructed/completed patterns

    Supports:
    - Learning new concept associations
    - Pattern completion from partial input
    - Adaptive thresholds based on activity
    """
    def __init__(self, input_size: int = 64, hidden_size: int = 128, output_size: int = 64):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size

        # Create neuron layers
        self.input_neurons = {
            f"in_{i}": SpikingNeuron(neuron_id=f"in_{i}", threshold=0.8)
            for i in range(input_size)
        }
        self.hidden_neurons = {
            f"hid_{i}": SpikingNeuron(neuron_id=f"hid_{i}", threshold=1.0, leak_rate=0.03)
            for i in range(hidden_size)
        }
        self.output_neurons = {
            f"out_{i}": SpikingNeuron(neuron_id=f"out_{i}", threshold=0.9)
            for i in range(output_size)
        }

        # Create synapses (sparse random connectivity)
        self.synapses: List[Synapse] = []
        self._init_connectivity(sparsity=0.3)

        # Concept-to-pattern mapping
        self.concept_patterns: Dict[str, List[int]] = {}

        # Statistics
        self.total_spikes = 0
        self.learning_cycles = 0
        self.patterns_learned = 0

    def _init_connectivity(self, sparsity: float = 0.3):
        """Initialize sparse random connections between layers."""
        # Input -> Hidden (sparse)
        for in_id in self.input_neurons:
            for hid_id in self.hidden_neurons:
                if random.random() < sparsity:
                    self.synapses.append(Synapse(
                        pre_id=in_id, post_id=hid_id,
                        weight=random.uniform(0.05, 0.2)
                    ))

        # Hidden -> Output (sparse)
        for hid_id in self.hidden_neurons:
            for out_id in self.output_neurons:
                if random.random() < sparsity:
                    self.synapses.append(Synapse(
                        pre_id=hid_id, post_id=out_id,
                        weight=random.uniform(0.05, 0.2)
                    ))

        # Hidden recurrent (sparse — for associative memory)
        hid_ids = list(self.hidden_neurons.keys())
        for i in range(len(hid_ids)):
            for j in range(i + 1, len(hid_ids)):
                if random.random() < sparsity * 0.3:  # Sparser recurrence
                    self.synapses.append(Synapse(
                        pre_id=hid_ids[i], post_id=hid_ids[j],
                        weight=random.uniform(0.01, 0.1)
                    ))

    def _text_to_pattern(self, text: str) -> List[int]:
        """
        Encode text as a sparse binary pattern (Sparse Distributed Representation).
        Each unique concept activates a consistent set of input neurons.
        """
        # Deterministic hash-based activation
        active = set()
        words = text.lower().split()
        for word in words:
            h = hash(word)
            # Each word activates ~10% of input neurons
            for k in range(max(1, self.input_size // 10)):
                idx = (h + k * 7919) % self.input_size  # Prime stride
                active.add(idx)
        return sorted(active)

    def learn_concept(self, concept: str, repetitions: int = 5):
        """
        Learn a concept by presenting its spike pattern repeatedly.
        Hebbian learning strengthens the pathways for this pattern.
        """
        pattern = self._text_to_pattern(concept)
        self.concept_patterns[concept] = pattern

        for _ in range(repetitions):
            # Present pattern to input layer
            fired_neurons = set()

            # Inject spikes into input neurons
            for idx in pattern:
                nid = f"in_{idx}"
                if nid in self.input_neurons:
                    self.input_neurons[nid].membrane_potential = 1.5  # Above threshold
                    fired_neurons.add(nid)

            # Propagate through network (multiple steps)
            for step in range(3):
                step_fired = set()

                # Step all neurons
                for nid, neuron in {**self.input_neurons, **self.hidden_neurons, **self.output_neurons}.items():
                    if neuron.step():
                        step_fired.add(nid)
                        self.total_spikes += 1

                # Propagate spikes through synapses
                for syn in self.synapses:
                    pre_fired = syn.pre_id in step_fired
                    if pre_fired:
                        post_neuron = (
                            self.hidden_neurons.get(syn.post_id) or
                            self.output_neurons.get(syn.post_id) or
                            self.input_neurons.get(syn.post_id)  # Recurrent
                        )
                        if post_neuron:
                            post_neuron.receive_input(syn.weight)

                # Hebbian update for all synapses
                for syn in self.synapses:
                    syn.hebbian_update(
                        pre_fired=syn.pre_id in step_fired,
                        post_fired=syn.post_id in step_fired
                    )

                fired_neurons.update(step_fired)

            self.learning_cycles += 1

        self.patterns_learned += 1

    def recall(self, partial_input: str, steps: int = 5) -> Dict[str, float]:
        """
        Given partial/noisy input, let the network settle and
        return which learned concepts are most activated (pattern completion).

        Returns: {concept_name: activation_score}
        """
        # Encode partial input
        partial_pattern = self._text_to_pattern(partial_input)

        # Inject partial pattern
        for idx in partial_pattern:
            nid = f"in_{idx}"
            if nid in self.input_neurons:
                self.input_neurons[nid].membrane_potential = 1.2

        # Let network settle
        output_spikes: Dict[str, int] = {f"out_{i}": 0 for i in range(self.output_size)}

        for _ in range(steps):
            step_fired = set()
            for nid, neuron in {**self.input_neurons, **self.hidden_neurons, **self.output_neurons}.items():
                if neuron.step():
                    step_fired.add(nid)

            # Propagate
            for syn in self.synapses:
                if syn.pre_id in step_fired:
                    post = (
                        self.hidden_neurons.get(syn.post_id) or
                        self.output_neurons.get(syn.post_id) or
                        self.input_neurons.get(syn.post_id)
                    )
                    if post:
                        post.receive_input(syn.weight)

            # Count output spikes
            for nid in step_fired:
                if nid in output_spikes:
                    output_spikes[nid] += 1

        # Match output pattern against known concepts
        output_active = set(nid for nid, count in output_spikes.items() if count > 0)
        output_indices = set(int(nid.split("_")[1]) for nid in output_active)

        concept_scores = {}
        for concept, pattern in self.concept_patterns.items():
            pattern_set = set(pattern)
            if pattern_set:
                # Jaccard-like overlap between output activity and concept's input pattern
                overlap = len(output_indices & pattern_set)
                score = overlap / max(len(pattern_set), 1)
                concept_scores[concept] = round(score, 3)

        return dict(sorted(concept_scores.items(), key=lambda x: x[1], reverse=True))

    def adapt_thresholds(self):
        """
        Homeostatic plasticity: neurons that fire too much raise their
        threshold; neurons that never fire lower it. Keeps network balanced.
        """
        for neuron in self.hidden_neurons.values():
            if neuron._spike_count > 50:
                neuron.threshold *= 1.05  # Raise threshold (less excitable)
                neuron._spike_count = 0
            elif neuron._spike_count == 0:
                neuron.threshold *= 0.95  # Lower threshold (more excitable)
                neuron.threshold = max(0.5, neuron.threshold)

    def get_summary(self) -> Dict:
        """Return network statistics."""
        active_synapses = sum(1 for s in self.synapses if s.weight > 0.05)
        avg_weight = sum(s.weight for s in self.synapses) / max(len(self.synapses), 1)
        return {
            "total_neurons": self.input_size + self.hidden_size + self.output_size,
            "total_synapses": len(self.synapses),
            "active_synapses": active_synapses,
            "avg_synapse_weight": round(avg_weight, 4),
            "total_spikes": self.total_spikes,
            "patterns_learned": self.patterns_learned,
            "learning_cycles": self.learning_cycles,
            "synaptic_density": round(active_synapses / max(len(self.synapses), 1), 4),
            "status": "Growing" if self.patterns_learned < 50 else "Maturing"
        }


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    net = NeuromorphicNetwork(input_size=32, hidden_size=64, output_size=32)

    # Learn some concepts
    concepts = [
        "philosophy of consciousness and free will",
        "python programming and automation",
        "emotional intelligence and empathy",
        "quantum physics and wave functions",
        "African oral tradition and storytelling",
    ]
    for c in concepts:
        net.learn_concept(c, repetitions=10)
        print(f"Learned: {c}")

    # Pattern completion from partial input
    print("\nRecall from 'philosophy free will':")
    scores = net.recall("philosophy free will")
    for concept, score in scores.items():
        print(f"  {concept}: {score}")

    print(f"\nNetwork summary: {net.get_summary()}")
