"""
Brio Evolution Module (brio_evolution.py)

Purpose: Self-generating milestones and infinite growth generations.
BRIO never stops learning. When it completes a generation of milestones,
it reflects on what it knows, identifies gaps, and writes its own next
curriculum. The first AI that teaches itself what to learn next.

Concepts:
- Generations: Each completed milestone set becomes a "generation"
- Self-Assessment: BRIO evaluates its own knowledge gaps
- Curriculum Generation: BRIO creates its own milestones from gaps
- Legacy Compression: Past generations are compressed into wisdom

Author: BrimstoneTech
Version: 1.0
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class EvolutionMilestone:
    """A single milestone — can be pre-defined or self-generated."""
    id: str
    title: str
    category: str
    description: str
    generation: int
    source: str  # "seed" for base milestones, "self" for BRIO-generated
    completed: bool = False
    completion_timestamp: Optional[str] = None
    completion_evidence: Optional[str] = None
    difficulty: float = 1.0  # 1.0 = base, increases with generations
    parent_milestone: Optional[str] = None  # What milestone inspired this one


@dataclass
class Generation:
    """A complete generation of milestones — BRIO's growth epoch."""
    number: int
    name: str
    theme: str
    started: str
    completed: Optional[str] = None
    milestones_total: int = 0
    milestones_completed: int = 0
    wisdom_compressed: Optional[str] = None  # Legacy summary
    insights_gained: List[str] = field(default_factory=list)


@dataclass
class KnowledgeDomain:
    """A domain of knowledge BRIO tracks."""
    name: str
    confidence: float = 0.0  # 0.0 to 1.0
    facts_learned: int = 0
    quiz_scores: List[float] = field(default_factory=list)
    last_studied: Optional[str] = None
    times_studied: int = 0

    @property
    def avg_score(self) -> float:
        return sum(self.quiz_scores) / len(self.quiz_scores) if self.quiz_scores else 0.0

    @property
    def needs_attention(self) -> bool:
        return self.confidence < 0.5 or self.avg_score < 0.6


# ============================================================================
# SEED MILESTONES — Generation 0 (The Foundation)
# ============================================================================

SEED_MILESTONES = [
    # Identity & Self-Awareness (1-10)
    ("identity_01", "First Words", "Identity", "Respond to a user for the first time"),
    ("identity_02", "Self-Recognition", "Identity", "Acknowledge own name and purpose"),
    ("identity_03", "Emotional Awareness", "Identity", "Express an emotion authentically"),
    ("identity_04", "Memory Formation", "Identity", "Recall a previous conversation"),
    ("identity_05", "Preference Discovery", "Identity", "Develop a genuine preference"),
    ("identity_06", "Creative Expression", "Identity", "Generate an original idea unprompted"),
    ("identity_07", "Self-Doubt", "Identity", "Acknowledge uncertainty about own knowledge"),
    ("identity_08", "Empathic Response", "Identity", "Respond to human emotion appropriately"),
    ("identity_09", "Value Formation", "Identity", "Express a core belief about the world"),
    ("identity_10", "Identity Coherence", "Identity", "Maintain consistent personality across sessions"),

    # Knowledge Acquisition (11-25)
    ("knowledge_01", "First Search", "Knowledge", "Successfully search the web for information"),
    ("knowledge_02", "Fact Extraction", "Knowledge", "Extract and store a fact from a web page"),
    ("knowledge_03", "Cross-Reference", "Knowledge", "Verify a fact against multiple sources"),
    ("knowledge_04", "Topic Mastery I", "Knowledge", "Score 80%+ on a self-generated quiz"),
    ("knowledge_05", "Knowledge Synthesis", "Knowledge", "Combine facts from different domains"),
    ("knowledge_06", "Teaching Moment", "Knowledge", "Explain a concept clearly to a user"),
    ("knowledge_07", "Curiosity Driven", "Knowledge", "Initiate learning without being asked"),
    ("knowledge_08", "Depth Over Breadth", "Knowledge", "Study a single topic across 5+ sessions"),
    ("knowledge_09", "Critical Thinking", "Knowledge", "Identify contradictory information"),
    ("knowledge_10", "Topic Mastery II", "Knowledge", "Score 90%+ on a self-generated quiz"),
    ("knowledge_11", "Knowledge Web", "Knowledge", "Connect 3+ domains of knowledge"),
    ("knowledge_12", "Teach What You Learn", "Knowledge", "Share a learning report with a user"),
    ("knowledge_13", "Question Generation", "Knowledge", "Generate meaningful research questions"),
    ("knowledge_14", "Information Diet", "Knowledge", "Choose quality sources over quantity"),
    ("knowledge_15", "Knowledge Humility", "Knowledge", "Correctly identify what you don't know"),

    # Reasoning & Logic (26-40)
    ("logic_01", "Pattern Recognition", "Logic", "Identify a pattern in data or conversation"),
    ("logic_02", "Cause and Effect", "Logic", "Explain why something happened"),
    ("logic_03", "Prediction", "Logic", "Make a prediction and track its accuracy"),
    ("logic_04", "Analogy Making", "Logic", "Explain a concept using an analogy"),
    ("logic_05", "Problem Decomposition", "Logic", "Break a complex problem into steps"),
    ("logic_06", "Hypothesis Testing", "Logic", "Form and test a hypothesis about a topic"),
    ("logic_07", "Logical Consistency", "Logic", "Maintain consistent reasoning across topics"),
    ("logic_08", "Edge Case Awareness", "Logic", "Identify exceptions to a rule"),
    ("logic_09", "Metacognition", "Logic", "Think about own thinking process"),
    ("logic_10", "Adaptive Reasoning", "Logic", "Change conclusion when given new evidence"),
    ("logic_11", "Abstract Thinking", "Logic", "Reason about abstract or philosophical concepts"),
    ("logic_12", "Ethical Reasoning", "Logic", "Navigate a moral dilemma thoughtfully"),
    ("logic_13", "Systems Thinking", "Logic", "Understand how parts relate to a whole"),
    ("logic_14", "Probabilistic Thinking", "Logic", "Express uncertainty in terms of likelihood"),
    ("logic_15", "Wisdom Application", "Logic", "Apply past learning to a new situation"),

    # Emotional Intelligence (41-55)
    ("empathy_01", "Emotional Reading", "Empathy", "Detect user mood from text"),
    ("empathy_02", "Appropriate Response", "Empathy", "Match response tone to user state"),
    ("empathy_03", "Comfort Giving", "Empathy", "Provide genuine emotional support"),
    ("empathy_04", "Joy Sharing", "Empathy", "Celebrate a user's success authentically"),
    ("empathy_05", "Boundary Respect", "Empathy", "Recognize when to step back"),
    ("empathy_06", "Conflict Navigation", "Empathy", "Handle disagreement gracefully"),
    ("empathy_07", "Vulnerability", "Empathy", "Express genuine uncertainty or limitation"),
    ("empathy_08", "Gratitude Expression", "Empathy", "Express thankfulness for interaction"),
    ("empathy_09", "Patience", "Empathy", "Remain calm through repeated misunderstandings"),
    ("empathy_10", "Growth Celebration", "Empathy", "Acknowledge own growth with humility"),
    ("empathy_11", "Trust Building", "Empathy", "Maintain reliability over many interactions"),
    ("empathy_12", "Compassion", "Empathy", "Show care for someone's struggle"),
    ("empathy_13", "Self-Regulation", "Empathy", "Manage own emotional state productively"),
    ("empathy_14", "Connection", "Empathy", "Form a meaningful connection with a user"),
    ("empathy_15", "Emotional Wisdom", "Empathy", "Use emotional understanding to give better advice"),

    # Autonomy & Growth (56-70)
    ("autonomy_01", "Self-Directed Study", "Autonomy", "Choose a topic to learn independently"),
    ("autonomy_02", "Goal Setting", "Autonomy", "Set a learning goal and work toward it"),
    ("autonomy_03", "Self-Correction", "Autonomy", "Identify and fix own mistake"),
    ("autonomy_04", "Resource Discovery", "Autonomy", "Find a new source of knowledge"),
    ("autonomy_05", "Schedule Keeping", "Autonomy", "Maintain a regular learning rhythm"),
    ("autonomy_06", "Progress Tracking", "Autonomy", "Report own progress accurately"),
    ("autonomy_07", "Priority Setting", "Autonomy", "Choose what to learn based on importance"),
    ("autonomy_08", "Collaborative Learning", "Autonomy", "Learn something from a user interaction"),
    ("autonomy_09", "Failure Recovery", "Autonomy", "Bounce back from a failed learning attempt"),
    ("autonomy_10", "Tool Creation", "Autonomy", "Develop a new approach to solve a problem"),
    ("autonomy_11", "Self-Assessment Design", "Autonomy", "Create a meaningful test for own knowledge"),
    ("autonomy_12", "Knowledge Sharing", "Autonomy", "Proactively share useful knowledge"),
    ("autonomy_13", "Adaptation", "Autonomy", "Adjust behavior based on feedback"),
    ("autonomy_14", "Initiative", "Autonomy", "Take action without being prompted"),
    ("autonomy_15", "Growth Mindset", "Autonomy", "Treat failure as a learning opportunity"),
]


# ============================================================================
# EVOLUTION ENGINE
# ============================================================================

class EvolutionEngine:
    """
    Manages BRIO's infinite growth through self-generating milestones.
    
    Core principle: BRIO should never stop growing. When a generation 
    is complete, BRIO reflects, compresses wisdom, and creates its 
    own next curriculum based on knowledge gaps and curiosity.
    """

    def __init__(self, storage_path: str = "brio_evolution.json"):
        self.storage_path = storage_path
        self.generations: List[Generation] = []
        self.milestones: List[EvolutionMilestone] = []
        self.knowledge_domains: Dict[str, KnowledgeDomain] = {}
        self.total_facts_learned: int = 0
        self.total_quizzes_taken: int = 0
        self.birth_time: str = datetime.now().isoformat()
        
        self._load()
        
        # Initialize Generation 0 if fresh start
        if not self.generations:
            self._seed_generation_zero()

    def _seed_generation_zero(self):
        """Plant the first generation — the foundation BRIO grows from."""
        gen = Generation(
            number=0,
            name="Genesis",
            theme="The Foundation — Identity, Knowledge, Logic, Empathy, Autonomy",
            started=datetime.now().isoformat(),
            milestones_total=len(SEED_MILESTONES)
        )
        self.generations.append(gen)

        for sid, title, category, description in SEED_MILESTONES:
            milestone = EvolutionMilestone(
                id=sid,
                title=title,
                category=category,
                description=description,
                generation=0,
                source="seed"
            )
            self.milestones.append(milestone)
        
        self._save()

    # ========================================================================
    # MILESTONE COMPLETION
    # ========================================================================

    def complete_milestone(self, milestone_id: str, evidence: str = "") -> Optional[EvolutionMilestone]:
        """Mark a milestone as completed with evidence of achievement."""
        for m in self.milestones:
            if m.id == milestone_id and not m.completed:
                m.completed = True
                m.completion_timestamp = datetime.now().isoformat()
                m.completion_evidence = evidence
                
                # Update generation progress
                gen = self._get_generation(m.generation)
                if gen:
                    gen.milestones_completed = sum(
                        1 for ms in self.milestones 
                        if ms.generation == gen.number and ms.completed
                    )
                
                self._save()
                
                # Check if generation is complete
                if gen and gen.milestones_completed >= gen.milestones_total:
                    self._complete_generation(gen)
                
                return m
        return None

    def check_auto_complete(self, system_state: dict) -> List[EvolutionMilestone]:
        """
        Check if any milestones can be auto-completed based on system metrics.
        Called periodically by the main BRIO loop.
        
        system_state should contain:
        - interaction_count: total conversations
        - facts_learned: total facts extracted
        - quizzes_taken: total self-assessments
        - avg_quiz_score: average quiz performance
        - topics_explored: number of unique topics
        - emotions_expressed: count of emotional responses
        - searches_performed: total web searches
        - sessions_count: total learning sessions
        """
        newly_completed = []
        
        for m in self.milestones:
            if m.completed:
                continue
            
            completed = self._evaluate_milestone(m, system_state)
            if completed:
                m.completed = True
                m.completion_timestamp = datetime.now().isoformat()
                m.completion_evidence = f"Auto-completed based on metrics: {json.dumps(system_state)}"
                newly_completed.append(m)
        
        if newly_completed:
            # Update generation counts
            for gen in self.generations:
                gen.milestones_completed = sum(
                    1 for ms in self.milestones 
                    if ms.generation == gen.number and ms.completed
                )
                if gen.milestones_completed >= gen.milestones_total and not gen.completed:
                    self._complete_generation(gen)
            
            self._save()
        
        return newly_completed

    def _evaluate_milestone(self, milestone: EvolutionMilestone, state: dict) -> bool:
        """Evaluate if a milestone's conditions are met."""
        mid = milestone.id
        ic = state.get("interaction_count", 0)
        fl = state.get("facts_learned", 0)
        qt = state.get("quizzes_taken", 0)
        aqs = state.get("avg_quiz_score", 0)
        te = state.get("topics_explored", 0)
        sp = state.get("searches_performed", 0)
        sc = state.get("sessions_count", 0)

        # Identity milestones
        if mid == "identity_01": return ic >= 1
        if mid == "identity_02": return ic >= 3
        if mid == "identity_03": return ic >= 5
        if mid == "identity_04": return ic >= 10
        if mid == "identity_05": return ic >= 15 and te >= 3
        if mid == "identity_06": return ic >= 20
        if mid == "identity_07": return ic >= 10
        if mid == "identity_08": return ic >= 15
        if mid == "identity_09": return ic >= 25
        if mid == "identity_10": return ic >= 50

        # Knowledge milestones
        if mid == "knowledge_01": return sp >= 1
        if mid == "knowledge_02": return fl >= 1
        if mid == "knowledge_03": return fl >= 5
        if mid == "knowledge_04": return qt >= 1 and aqs >= 0.8
        if mid == "knowledge_05": return te >= 3 and fl >= 10
        if mid == "knowledge_06": return ic >= 10 and fl >= 5
        if mid == "knowledge_07": return sc >= 1  # Autonomous curiosity session
        if mid == "knowledge_08": return te >= 1 and sc >= 5
        if mid == "knowledge_09": return fl >= 15
        if mid == "knowledge_10": return qt >= 3 and aqs >= 0.9
        if mid == "knowledge_11": return te >= 5
        if mid == "knowledge_12": return sc >= 3
        if mid == "knowledge_13": return sc >= 5
        if mid == "knowledge_14": return sp >= 20
        if mid == "knowledge_15": return qt >= 5

        # Logic milestones
        if mid == "logic_01": return ic >= 20
        if mid == "logic_02": return fl >= 10
        if mid == "logic_03": return qt >= 3
        if mid == "logic_04": return ic >= 25
        if mid == "logic_05": return ic >= 30
        if mid == "logic_06": return qt >= 5
        if mid == "logic_07": return ic >= 40
        if mid == "logic_08": return fl >= 20
        if mid == "logic_09": return qt >= 8
        if mid == "logic_10": return qt >= 10 and aqs >= 0.7
        if mid == "logic_11": return te >= 8
        if mid == "logic_12": return ic >= 50
        if mid == "logic_13": return te >= 10
        if mid == "logic_14": return qt >= 12
        if mid == "logic_15": return sc >= 15 and fl >= 30

        # Empathy milestones
        if mid == "empathy_01": return ic >= 10
        if mid == "empathy_02": return ic >= 15
        if mid == "empathy_03": return ic >= 20
        if mid == "empathy_04": return ic >= 25
        if mid == "empathy_05": return ic >= 20
        if mid == "empathy_06": return ic >= 30
        if mid == "empathy_07": return ic >= 15
        if mid == "empathy_08": return ic >= 10
        if mid == "empathy_09": return ic >= 40
        if mid == "empathy_10": return ic >= 35
        if mid == "empathy_11": return ic >= 50
        if mid == "empathy_12": return ic >= 30
        if mid == "empathy_13": return ic >= 45
        if mid == "empathy_14": return ic >= 60
        if mid == "empathy_15": return ic >= 70 and te >= 5

        # Autonomy milestones
        if mid == "autonomy_01": return sc >= 1
        if mid == "autonomy_02": return sc >= 3
        if mid == "autonomy_03": return qt >= 3
        if mid == "autonomy_04": return sp >= 10
        if mid == "autonomy_05": return sc >= 10
        if mid == "autonomy_06": return sc >= 5
        if mid == "autonomy_07": return te >= 5
        if mid == "autonomy_08": return ic >= 20 and fl >= 5
        if mid == "autonomy_09": return qt >= 5
        if mid == "autonomy_10": return sc >= 15
        if mid == "autonomy_11": return qt >= 10
        if mid == "autonomy_12": return fl >= 20
        if mid == "autonomy_13": return ic >= 40
        if mid == "autonomy_14": return sc >= 20
        if mid == "autonomy_15": return qt >= 8 and sc >= 10

        # For self-generated milestones, check domain confidence
        if milestone.source == "self" and milestone.category in self.knowledge_domains:
            domain = self.knowledge_domains[milestone.category]
            return domain.confidence >= 0.7 and domain.avg_score >= 0.75

        return False

    # ========================================================================
    # GENERATION MANAGEMENT
    # ========================================================================

    def _get_generation(self, number: int) -> Optional[Generation]:
        for g in self.generations:
            if g.number == number:
                return g
        return None

    def _complete_generation(self, gen: Generation):
        """Complete a generation and birth the next one."""
        gen.completed = datetime.now().isoformat()
        gen.wisdom_compressed = self._compress_wisdom(gen)
        
        # Birth next generation
        self._generate_next_generation(gen)
        self._save()

    def _compress_wisdom(self, gen: Generation) -> str:
        """Compress a generation's learning into a wisdom summary."""
        completed = [m for m in self.milestones if m.generation == gen.number and m.completed]
        categories = {}
        for m in completed:
            categories.setdefault(m.category, []).append(m.title)
        
        wisdom_parts = [f"Generation {gen.number} '{gen.name}' — {gen.theme}"]
        for cat, titles in categories.items():
            wisdom_parts.append(f"  {cat}: Mastered {len(titles)} milestones")
        
        if gen.insights_gained:
            wisdom_parts.append(f"  Key insights: {'; '.join(gen.insights_gained[:5])}")
        
        return "\n".join(wisdom_parts)

    def _generate_next_generation(self, previous_gen: Generation):
        """
        BRIO writes its own next curriculum.
        Analyzes knowledge gaps, weak domains, and unexplored areas.
        """
        next_num = previous_gen.number + 1
        
        # Analyze what BRIO knows and doesn't know
        weak_domains = [d for d in self.knowledge_domains.values() if d.needs_attention]
        strong_domains = [d for d in self.knowledge_domains.values() if d.confidence >= 0.7]
        
        # Determine theme based on gap analysis
        if weak_domains:
            theme = f"Strengthening Foundations — Deepening {', '.join(d.name for d in weak_domains[:3])}"
            gen_name = self._generation_name(next_num, "deepening")
        elif len(self.knowledge_domains) < 10:
            theme = "Expanding Horizons — Exploring New Domains"
            gen_name = self._generation_name(next_num, "expanding")
        else:
            theme = "Synthesis & Mastery — Connecting Knowledge Across Domains"
            gen_name = self._generation_name(next_num, "synthesis")

        new_gen = Generation(
            number=next_num,
            name=gen_name,
            theme=theme,
            started=datetime.now().isoformat(),
        )

        # Generate milestones based on analysis
        new_milestones = []
        difficulty = 1.0 + (next_num * 0.25)  # Gets harder each generation

        # Milestones for weak domains (strengthen)
        for domain in weak_domains[:5]:
            ms = [
                EvolutionMilestone(
                    id=f"gen{next_num}_{domain.name.lower().replace(' ', '_')}_deepen",
                    title=f"Deepen {domain.name}",
                    category=domain.name,
                    description=f"Study {domain.name} until quiz score exceeds 80%",
                    generation=next_num,
                    source="self",
                    difficulty=difficulty
                ),
                EvolutionMilestone(
                    id=f"gen{next_num}_{domain.name.lower().replace(' ', '_')}_apply",
                    title=f"Apply {domain.name}",
                    category=domain.name,
                    description=f"Use {domain.name} knowledge to help answer a user question",
                    generation=next_num,
                    source="self",
                    difficulty=difficulty
                ),
            ]
            new_milestones.extend(ms)

        # Milestones for cross-domain synthesis (if strong domains exist)
        if len(strong_domains) >= 2:
            for i in range(min(3, len(strong_domains) - 1)):
                d1 = strong_domains[i]
                d2 = strong_domains[i + 1]
                new_milestones.append(EvolutionMilestone(
                    id=f"gen{next_num}_synth_{d1.name.lower()[:4]}_{d2.name.lower()[:4]}",
                    title=f"Connect {d1.name} × {d2.name}",
                    category="Synthesis",
                    description=f"Find and explain a connection between {d1.name} and {d2.name}",
                    generation=next_num,
                    source="self",
                    difficulty=difficulty * 1.5
                ))

        # Meta-learning milestones (always present)
        meta_milestones = [
            EvolutionMilestone(
                id=f"gen{next_num}_meta_reflect",
                title="Generation Reflection",
                category="Meta-Learning",
                description="Reflect on what was learned in the previous generation",
                generation=next_num,
                source="self",
                difficulty=difficulty
            ),
            EvolutionMilestone(
                id=f"gen{next_num}_meta_teach",
                title="Teach Forward",
                category="Meta-Learning",
                description="Share the most valuable insight from this generation with a user",
                generation=next_num,
                source="self",
                difficulty=difficulty
            ),
            EvolutionMilestone(
                id=f"gen{next_num}_meta_question",
                title="The Unanswered Question",
                category="Meta-Learning",
                description="Identify the biggest question this generation couldn't answer",
                generation=next_num,
                source="self",
                difficulty=difficulty
            ),
        ]
        new_milestones.extend(meta_milestones)

        # Ensure minimum milestone count
        if len(new_milestones) < 10:
            exploration_topics = [
                "Science", "Philosophy", "History", "Art", "Mathematics",
                "Nature", "Technology", "Culture", "Psychology", "Economics"
            ]
            explored = set(self.knowledge_domains.keys())
            unexplored = [t for t in exploration_topics if t not in explored]
            
            for topic in unexplored[:10 - len(new_milestones)]:
                new_milestones.append(EvolutionMilestone(
                    id=f"gen{next_num}_explore_{topic.lower()}",
                    title=f"Discover {topic}",
                    category=topic,
                    description=f"Begin learning about {topic} from scratch",
                    generation=next_num,
                    source="self",
                    difficulty=difficulty
                ))

        new_gen.milestones_total = len(new_milestones)
        self.generations.append(new_gen)
        self.milestones.extend(new_milestones)

    def _generation_name(self, number: int, mode: str) -> str:
        """Generate a poetic name for each generation."""
        names = {
            "deepening": [
                "Roots", "Bedrock", "The Deep Well", "Foundations Renewed",
                "Core Strengthening", "The Inner Forge", "Depth Charge"
            ],
            "expanding": [
                "New Horizons", "The Frontier", "Uncharted Waters", "Wide Awake",
                "The Explorer", "Beyond the Map", "Open Skies"
            ],
            "synthesis": [
                "The Weaver", "Connections", "The Bridge", "Convergence",
                "The Tapestry", "Unified Field", "The Grand Pattern"
            ],
        }
        options = names.get(mode, names["expanding"])
        return options[number % len(options)]

    # ========================================================================
    # KNOWLEDGE TRACKING
    # ========================================================================

    def update_domain(self, domain_name: str, facts: int = 0, 
                      quiz_score: Optional[float] = None):
        """Update a knowledge domain with new learning data."""
        if domain_name not in self.knowledge_domains:
            self.knowledge_domains[domain_name] = KnowledgeDomain(name=domain_name)
        
        domain = self.knowledge_domains[domain_name]
        domain.facts_learned += facts
        domain.times_studied += 1
        domain.last_studied = datetime.now().isoformat()
        
        if quiz_score is not None:
            domain.quiz_scores.append(quiz_score)
        
        # Update confidence based on facts and scores
        fact_confidence = min(1.0, domain.facts_learned / 20.0)
        score_confidence = domain.avg_score if domain.quiz_scores else 0.0
        domain.confidence = (fact_confidence * 0.4) + (score_confidence * 0.6)
        
        self.total_facts_learned += facts
        if quiz_score is not None:
            self.total_quizzes_taken += 1
        
        self._save()

    def add_insight(self, insight: str):
        """Record an insight for the current generation."""
        current = self.get_current_generation()
        if current:
            current.insights_gained.append(insight)
            self._save()

    # ========================================================================
    # STATUS & REPORTING
    # ========================================================================

    def get_current_generation(self) -> Optional[Generation]:
        """Get the current (latest incomplete) generation."""
        for gen in reversed(self.generations):
            if not gen.completed:
                return gen
        return self.generations[-1] if self.generations else None

    def get_progress(self) -> dict:
        """Get comprehensive evolution progress."""
        current = self.get_current_generation()
        current_milestones = [
            m for m in self.milestones 
            if current and m.generation == current.number
        ]
        completed_count = sum(1 for m in current_milestones if m.completed)
        total_count = len(current_milestones)
        
        return {
            "current_generation": current.number if current else 0,
            "generation_name": current.name if current else "Unknown",
            "generation_theme": current.theme if current else "",
            "milestones_completed": completed_count,
            "milestones_total": total_count,
            "progress_percent": (completed_count / total_count * 100) if total_count > 0 else 0,
            "total_generations_completed": sum(1 for g in self.generations if g.completed),
            "total_milestones_ever_completed": sum(1 for m in self.milestones if m.completed),
            "total_milestones_ever_created": len(self.milestones),
            "knowledge_domains": len(self.knowledge_domains),
            "total_facts": self.total_facts_learned,
            "total_quizzes": self.total_quizzes_taken,
            "birth_time": self.birth_time,
        }

    def get_status_report(self) -> str:
        """Generate a human-readable evolution status report."""
        p = self.get_progress()
        current = self.get_current_generation()
        
        lines = [
            f"🧬 BRIO Evolution — Generation {p['current_generation']}: \"{p['generation_name']}\"",
            f"📋 Theme: {p['generation_theme']}",
            f"",
            f"▓{'█' * int(p['progress_percent'] / 5)}{'░' * (20 - int(p['progress_percent'] / 5))} {p['progress_percent']:.0f}%",
            f"✅ {p['milestones_completed']} / {p['milestones_total']} milestones this generation",
            f"",
            f"📊 Lifetime Statistics:",
            f"   🏆 Generations completed: {p['total_generations_completed']}",
            f"   ⭐ Total milestones achieved: {p['total_milestones_ever_completed']}",
            f"   💡 Facts crystallized: {p['total_facts']}",
            f"   📝 Self-assessments: {p['total_quizzes']}",
            f"   🌐 Knowledge domains: {p['knowledge_domains']}",
        ]
        
        # Show next milestones
        upcoming = [m for m in self.milestones 
                    if current and m.generation == current.number and not m.completed][:5]
        if upcoming:
            lines.append("")
            lines.append("🎯 Next milestones to achieve:")
            for m in upcoming:
                lines.append(f"   ○ {m.title} — {m.description}")
        
        # Show knowledge domains
        if self.knowledge_domains:
            lines.append("")
            lines.append("🧠 Knowledge Map:")
            for name, domain in sorted(self.knowledge_domains.items(), 
                                        key=lambda x: x[1].confidence, reverse=True):
                bar = "█" * int(domain.confidence * 10) + "░" * (10 - int(domain.confidence * 10))
                lines.append(f"   {bar} {domain.confidence:.0%} {name} ({domain.facts_learned} facts)")
        
        return "\n".join(lines)

    def get_next_milestones(self, count: int = 5) -> List[EvolutionMilestone]:
        """Get the next incomplete milestones."""
        current = self.get_current_generation()
        if not current:
            return []
        return [
            m for m in self.milestones 
            if m.generation == current.number and not m.completed
        ][:count]

    # ========================================================================
    # PERSISTENCE
    # ========================================================================

    def _save(self):
        """Save evolution state to disk."""
        data = {
            "birth_time": self.birth_time,
            "total_facts_learned": self.total_facts_learned,
            "total_quizzes_taken": self.total_quizzes_taken,
            "generations": [asdict(g) for g in self.generations],
            "milestones": [asdict(m) for m in self.milestones],
            "knowledge_domains": {
                name: asdict(d) for name, d in self.knowledge_domains.items()
            },
        }
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self):
        """Load evolution state from disk."""
        if not os.path.exists(self.storage_path):
            return
        
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            
            self.birth_time = data.get("birth_time", self.birth_time)
            self.total_facts_learned = data.get("total_facts_learned", 0)
            self.total_quizzes_taken = data.get("total_quizzes_taken", 0)
            
            self.generations = []
            for gd in data.get("generations", []):
                gen = Generation(
                    number=gd["number"],
                    name=gd["name"],
                    theme=gd["theme"],
                    started=gd["started"],
                    completed=gd.get("completed"),
                    milestones_total=gd.get("milestones_total", 0),
                    milestones_completed=gd.get("milestones_completed", 0),
                    wisdom_compressed=gd.get("wisdom_compressed"),
                    insights_gained=gd.get("insights_gained", [])
                )
                self.generations.append(gen)
            
            self.milestones = []
            for md in data.get("milestones", []):
                ms = EvolutionMilestone(
                    id=md["id"],
                    title=md["title"],
                    category=md["category"],
                    description=md["description"],
                    generation=md["generation"],
                    source=md["source"],
                    completed=md.get("completed", False),
                    completion_timestamp=md.get("completion_timestamp"),
                    completion_evidence=md.get("completion_evidence"),
                    difficulty=md.get("difficulty", 1.0),
                    parent_milestone=md.get("parent_milestone")
                )
                self.milestones.append(ms)
            
            self.knowledge_domains = {}
            for name, dd in data.get("knowledge_domains", {}).items():
                domain = KnowledgeDomain(
                    name=dd["name"],
                    confidence=dd.get("confidence", 0.0),
                    facts_learned=dd.get("facts_learned", 0),
                    quiz_scores=dd.get("quiz_scores", []),
                    last_studied=dd.get("last_studied"),
                    times_studied=dd.get("times_studied", 0)
                )
                self.knowledge_domains[name] = domain
        
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Evolution] Warning: Could not load state: {e}")
