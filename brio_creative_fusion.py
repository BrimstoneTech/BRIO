"""
Brio Creative Fusion Module (brio_creative_fusion.py)

Purpose: Cross-domain idea generation for BRIO.
         Combines concepts from different fields (art, science, philosophy,
         music, etc.) to produce novel ideas and unexpected connections.

Concepts:
- Domain Knowledge Graphs: Each field has core concepts and relationships
- Bisociation: Creativity = connecting ideas from unrelated domains (Koestler)
- Conceptual Blending: Merge two concepts to create a new emergent idea
- Serendipity Engine: Random but informed cross-domain connections
- Novelty Scoring: Measure how original an idea is

Author: BrimstoneTech
Version: 1.0
Dependencies: None (stdlib only)
"""

import random
import math
import time
import hashlib
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# KNOWLEDGE DOMAINS
# ============================================================================

class Domain(Enum):
    ART = "art"
    MUSIC = "music"
    PHYSICS = "physics"
    PHILOSOPHY = "philosophy"
    BIOLOGY = "biology"
    MATHEMATICS = "mathematics"
    LITERATURE = "literature"
    TECHNOLOGY = "technology"
    PSYCHOLOGY = "psychology"
    AFRICAN_CULTURE = "african_culture"


# Seed knowledge — BRIO starts with these and learns more
DOMAIN_CONCEPTS: Dict[str, List[str]] = {
    Domain.ART.value: [
        "composition", "contrast", "harmony", "perspective", "colour theory",
        "negative space", "rhythm", "texture", "abstraction", "symbolism"
    ],
    Domain.MUSIC.value: [
        "melody", "harmony", "rhythm", "counterpoint", "dissonance",
        "resonance", "improvisation", "tempo", "dynamics", "timbre"
    ],
    Domain.PHYSICS.value: [
        "entropy", "wave-particle duality", "quantum superposition", "relativity",
        "conservation of energy", "symmetry breaking", "emergence", "field theory",
        "uncertainty principle", "entanglement"
    ],
    Domain.PHILOSOPHY.value: [
        "consciousness", "free will", "epistemology", "ontology", "ethics",
        "existentialism", "phenomenology", "dialectics", "ubuntu", "paradox"
    ],
    Domain.BIOLOGY.value: [
        "evolution", "symbiosis", "homeostasis", "adaptation", "emergence",
        "neural plasticity", "genetic memory", "ecosystem", "mutation", "natural selection"
    ],
    Domain.MATHEMATICS.value: [
        "infinity", "recursion", "fractal", "golden ratio", "topology",
        "chaos theory", "symmetry", "proof by contradiction", "prime numbers", "dimensionality"
    ],
    Domain.LITERATURE.value: [
        "metaphor", "narrative arc", "unreliable narrator", "stream of consciousness",
        "allegory", "irony", "catharsis", "foreshadowing", "archetype", "voice"
    ],
    Domain.TECHNOLOGY.value: [
        "neural networks", "distributed systems", "encryption", "feedback loops",
        "abstraction layers", "emergent behaviour", "self-healing systems",
        "version control", "parallel processing", "API"
    ],
    Domain.PSYCHOLOGY.value: [
        "cognitive dissonance", "flow state", "gestalt", "projection",
        "intrinsic motivation", "mirror neurons", "empathy gap",
        "confirmation bias", "peak experience", "collective unconscious"
    ],
    Domain.AFRICAN_CULTURE.value: [
        "ubuntu", "oral tradition", "communal wisdom", "ancestral memory",
        "drum language", "call and response", "proverb", "rites of passage",
        "griot storytelling", "interconnectedness"
    ],
}

# Cross-domain bridges — known connections between fields
KNOWN_BRIDGES: List[Tuple[str, str, str]] = [
    ("harmony", "homeostasis", "Both seek balance through dynamic tension"),
    ("fractal", "rhythm", "Self-similar patterns at every scale"),
    ("evolution", "dialectics", "Thesis-antithesis-synthesis mirrors mutation-selection"),
    ("ubuntu", "symbiosis", "Interconnected existence as survival strategy"),
    ("metaphor", "neural networks", "Both map one domain's structure onto another"),
    ("entropy", "narrative arc", "Stories fight entropy — imposing order on chaos"),
    ("flow state", "improvisation", "The dissolution of self in creative action"),
    ("quantum superposition", "paradox", "Holding contradictions simultaneously"),
    ("emergence", "consciousness", "Complex wholes arising from simple parts"),
    ("drum language", "encryption", "Encoding meaning in patterns"),
]


# ============================================================================
# CONCEPTUAL BLEND
# ============================================================================

@dataclass
class ConceptualBlend:
    """The product of fusing two concepts from different domains."""
    concept_a: str
    domain_a: str
    concept_b: str
    domain_b: str
    blend_name: str
    description: str
    novelty_score: float  # 0-1, higher = more original
    timestamp: float = field(default_factory=time.time)

    def __str__(self):
        return f"[{self.blend_name}] ({self.domain_a}×{self.domain_b}): {self.description}"


# ============================================================================
# CREATIVE FUSION ENGINE
# ============================================================================

class CreativeFusionEngine:
    """
    BRIO's cross-domain creativity engine.

    Usage:
        engine = CreativeFusionEngine()

        # Generate a random creative connection
        blend = engine.bisociate()

        # Fuse two specific concepts
        blend = engine.fuse("entropy", "narrative arc")

        # Generate ideas for a topic using cross-domain thinking
        ideas = engine.ideate("How should BRIO handle uncertainty?", n=5)
    """

    def __init__(self):
        self.domains = dict(DOMAIN_CONCEPTS)  # Mutable copy
        self.bridges = list(KNOWN_BRIDGES)
        self.blends: List[ConceptualBlend] = []
        self.blend_hashes: Set[str] = set()  # Avoid duplicates

    def add_concept(self, domain: str, concept: str):
        """Expand BRIO's knowledge in a domain."""
        if domain not in self.domains:
            self.domains[domain] = []
        if concept not in self.domains[domain]:
            self.domains[domain].append(concept)

    # ── Bisociation ─────────────────────────────────────────────────────

    def bisociate(self) -> ConceptualBlend:
        """
        Arthur Koestler's bisociation: connect two ideas from
        completely unrelated domains to produce a creative insight.
        """
        # Pick two different domains
        domain_keys = list(self.domains.keys())
        d1, d2 = random.sample(domain_keys, 2)
        c1 = random.choice(self.domains[d1])
        c2 = random.choice(self.domains[d2])

        return self.fuse(c1, c2, d1, d2)

    def fuse(self, concept_a: str, concept_b: str,
             domain_a: str = "", domain_b: str = "") -> ConceptualBlend:
        """
        Conceptual blending: merge two concepts into a new idea.
        """
        # Auto-detect domains if not specified
        if not domain_a:
            domain_a = self._find_domain(concept_a)
        if not domain_b:
            domain_b = self._find_domain(concept_b)

        # Generate blend name (portmanteau or compound)
        blend_name = self._generate_blend_name(concept_a, concept_b)

        # Generate description via template-based reasoning
        description = self._generate_description(concept_a, domain_a, concept_b, domain_b)

        # Calculate novelty (how far apart are the domains?)
        novelty = self._calculate_novelty(domain_a, domain_b, concept_a, concept_b)

        blend = ConceptualBlend(
            concept_a=concept_a,
            domain_a=domain_a,
            concept_b=concept_b,
            domain_b=domain_b,
            blend_name=blend_name,
            description=description,
            novelty_score=novelty
        )

        # Track unique blends
        h = hashlib.md5(f"{concept_a}:{concept_b}".encode()).hexdigest()[:8]
        if h not in self.blend_hashes:
            self.blends.append(blend)
            self.blend_hashes.add(h)

        return blend

    # ── Ideation ────────────────────────────────────────────────────────

    def ideate(self, topic: str, n: int = 5) -> List[ConceptualBlend]:
        """
        Generate n creative ideas for a topic by cross-pollinating
        with concepts from other domains.
        """
        # Extract keywords from topic
        keywords = [w.lower() for w in topic.split() if len(w) > 3]

        # Find related concepts across all domains
        related = []
        for domain, concepts in self.domains.items():
            for concept in concepts:
                relevance = sum(1 for k in keywords if k in concept.lower())
                if relevance > 0:
                    related.append((concept, domain, relevance))

        # Sort by relevance
        related.sort(key=lambda x: x[2], reverse=True)

        ideas = []
        used_pairs = set()

        for _ in range(n * 3):  # Generate extra, keep best
            if len(ideas) >= n:
                break

            if related and random.random() < 0.6:
                # Fuse a related concept with a random one from a different domain
                base_concept, base_domain, _ = random.choice(related[:5])
                other_domains = [d for d in self.domains if d != base_domain]
                if other_domains:
                    other_domain = random.choice(other_domains)
                    other_concept = random.choice(self.domains[other_domain])
                    pair_key = f"{base_concept}:{other_concept}"
                    if pair_key not in used_pairs:
                        used_pairs.add(pair_key)
                        ideas.append(self.fuse(base_concept, other_concept, base_domain, other_domain))
            else:
                # Pure bisociation
                blend = self.bisociate()
                ideas.append(blend)

        # Sort by novelty
        ideas.sort(key=lambda b: b.novelty_score, reverse=True)
        return ideas[:n]

    def find_bridges(self, concept: str) -> List[Tuple[str, str]]:
        """Find known bridges from this concept to other domains."""
        results = []
        c = concept.lower()
        for a, b, explanation in self.bridges:
            if c in a.lower() or c in b.lower():
                other = b if c in a.lower() else a
                results.append((other, explanation))
        return results

    # ── Internal ────────────────────────────────────────────────────────

    def _find_domain(self, concept: str) -> str:
        """Find which domain a concept belongs to."""
        c = concept.lower()
        for domain, concepts in self.domains.items():
            if any(c in con.lower() or con.lower() in c for con in concepts):
                return domain
        return "unknown"

    def _generate_blend_name(self, a: str, b: str) -> str:
        """Generate a creative name for the blend."""
        # Take first half of a and second half of b
        mid_a = len(a) // 2
        mid_b = len(b) // 2
        portmanteau = a[:mid_a] + b[mid_b:]

        # Also create a compound name
        compound = f"{a.split()[0]}-{b.split()[-1]}" if " " in a or " " in b else f"{a}-{b}"

        # Pick the shorter, more readable one
        return compound if len(compound) < len(portmanteau) else portmanteau

    def _generate_description(self, ca: str, da: str, cb: str, db: str) -> str:
        """Generate a description of how two concepts connect."""
        templates = [
            f"What if we applied {da}'s concept of '{ca}' to {db}'s '{cb}'? "
            f"Like {ca}, {cb} involves patterns that emerge from underlying structure.",

            f"'{ca}' from {da} mirrors '{cb}' in {db}: both describe how "
            f"complex behaviour arises from simpler rules interacting.",

            f"Bridging {da} and {db}: just as {ca} transforms its domain, "
            f"applying similar principles to {cb} could unlock new understanding.",

            f"The intersection of {ca} ({da}) and {cb} ({db}) suggests "
            f"a deeper pattern — both deal with the tension between order and chaos.",

            f"Consider {ca} through the lens of {cb}: what if the rules governing "
            f"{da} have analogues in {db} that we haven't explored?",
        ]
        return random.choice(templates)

    def _calculate_novelty(self, da: str, db: str, ca: str, cb: str) -> float:
        """
        Score how novel a blend is (0-1).
        - Same domain = low novelty
        - Distant domains = high novelty
        - Known bridges = moderate (interesting but not new)
        """
        if da == db:
            return 0.1

        # Domain distance (arbitrary but consistent)
        domain_list = list(self.domains.keys())
        try:
            dist = abs(domain_list.index(da) - domain_list.index(db))
            max_dist = len(domain_list) - 1
            domain_novelty = dist / max_dist if max_dist > 0 else 0.5
        except ValueError:
            domain_novelty = 0.7

        # Check if this is a known bridge (reduce novelty slightly)
        is_known = any(
            (ca.lower() in a.lower() and cb.lower() in b.lower()) or
            (cb.lower() in a.lower() and ca.lower() in b.lower())
            for a, b, _ in self.bridges
        )
        bridge_penalty = 0.2 if is_known else 0.0

        # Lexical distance between concepts (crude proxy for semantic distance)
        shared_chars = len(set(ca.lower()) & set(cb.lower()))
        total_chars = len(set(ca.lower()) | set(cb.lower()))
        lexical_distance = 1.0 - (shared_chars / max(total_chars, 1))

        novelty = (0.4 * domain_novelty + 0.4 * lexical_distance + 0.2 * random.uniform(0.3, 1.0))
        novelty -= bridge_penalty
        return max(0.0, min(1.0, novelty))

    def get_stats(self) -> Dict:
        if not self.blends:
            return {"total_blends": 0}
        avg_novelty = sum(b.novelty_score for b in self.blends) / len(self.blends)
        domains_used = set()
        for b in self.blends:
            domains_used.add(b.domain_a)
            domains_used.add(b.domain_b)
        return {
            "total_blends": len(self.blends),
            "unique_blends": len(self.blend_hashes),
            "avg_novelty": round(avg_novelty, 3),
            "domains_active": len(domains_used),
            "total_concepts": sum(len(v) for v in self.domains.values()),
        }


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    engine = CreativeFusionEngine()

    print("=== Random Bisociation ===")
    blend = engine.bisociate()
    print(blend)

    print("\n=== Targeted Ideation ===")
    ideas = engine.ideate("How should an AI handle emotions and uncertainty?", n=3)
    for idea in ideas:
        print(f"  [{idea.novelty_score:.2f}] {idea}")

    print(f"\n=== Bridges from 'emergence' ===")
    for other, explanation in engine.find_bridges("emergence"):
        print(f"  → {other}: {explanation}")

    print(f"\nStats: {engine.get_stats()}")
