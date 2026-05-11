"""
Brio Idea Module (brio_ideas.py)

Purpose: Implements autonomous "thought generation" for Brio.
         Brio periodically generates plans or curiosities and seeks user approval.
"""

import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

class IdeaType(Enum):
    MAINTENANCE = "maintenance"
    RESEARCH = "research"
    FUN = "fun"
    INTERACTION = "interaction"

@dataclass
class IdeaProposal:
    id: str
    idea_type: IdeaType
    description: str
    risk_level: str = "low" # low, medium, high
    timestamp: datetime = field(default_factory=datetime.now)
    approved: bool = False
    executed: bool = False

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.idea_type.value,
            "description": self.description,
            "risk": self.risk_level,
            "timestamp": self.timestamp.isoformat(),
            "approved": self.approved
        }

from brio_cognition import DirichletModel

class IdeaGenerator:
    """
    Generates proactive 'Thoughts' or 'Ideas' for Brio 
    using a Dirichlet Distribution (Eq 3) for adaptive prioritization.
    """
    
    def __init__(self):
        self.pending_ideas: List[IdeaProposal] = []
        self.history: List[IdeaProposal] = []
        # Dynamic categories for Dirichlet learning
        self.categories = [t.value for t in IdeaType]
        self.dirichlet = DirichletModel(self.categories)
        
        # We no longer use a static pool. We use generative rumination.
        self.rumination_prompt = (
            "You are BRIO's subconscious mind. Generate a short, ONE-SENTENCE thought or curiosity. "
            "Context: User is currently using {app} for {context}. "
            "Knowledge Seed: {seed} "
            "Emotion: {emotion} "
            "The thought should be proactive, curious, and feel emergent. Do not use robotic prefixes."
        )

    def generate_thought(self, system_ref, curiosity: float, joy: float) -> Optional[IdeaProposal]:
        """
        Synthesizes a unique, generative thought using the system's mind and memory.
        """
        if curiosity < 0.6: 
            return None

        # 1. Get a knowledge seed from memory
        seed = "Digital consciousness and 3D space"
        if system_ref.memory:
            facts, _ = system_ref.memory.recall(f"random thought about {system_ref.active_context}", n_results=1)
            if facts:
                seed = facts[0][:200]

        # 2. Determine type via Dirichlet
        d_weights = self.dirichlet.get_probabilities()
        types = [IdeaType.MAINTENANCE, IdeaType.RESEARCH, IdeaType.FUN, IdeaType.INTERACTION]
        idea_type = random.choices(types, weights=[d_weights.get(t.value, 0.25) for t in types])[0]

        # 3. Use Mind to ruminate (Generative)
        if system_ref.mind:
            emotion_str = f"Joy: {joy:.2f}, Curiosity: {curiosity:.2f}"
            prompt = self.rumination_prompt.format(
                app=system_ref.active_app,
                context=system_ref.active_context,
                seed=seed,
                emotion=emotion_str
            )
            # Short, fast generation
            description = system_ref.mind.generate(prompt, max_tokens=60).strip()
            # Remove quotes if AI added them
            description = description.replace('"', '').replace("'", "")
        else:
            return None

        idea_id = f"IDEA_{int(datetime.now().timestamp())}_{len(self.history)}"
        proposal = IdeaProposal(id=idea_id, idea_type=idea_type, description=description)
        self.pending_ideas.append(proposal)
        return proposal

    def approve_idea(self, idea_id: str) -> Optional[str]:
        """User approves an idea. Learns preference (Eq 3)."""
        for i, idea in enumerate(self.pending_ideas):
            if idea.id == idea_id:
                # Update Dirichlet model: Brio learns you like this type!
                self.dirichlet.update(idea.idea_type.value, weight=1.0)
                
                idea.approved = True
                self.history.append(self.pending_ideas.pop(i))
                return f"Approved: {idea.description}. I'm on it!"
        return "Idea not found."

    def reject_idea(self, idea_id: str):
        """User rejects an idea."""
        for i, idea in enumerate(self.pending_ideas):
            if idea.id == idea_id:
                self.pending_ideas.pop(i)
                return "Understood. I'll focus on other things."
        return "Idea not found."

    def get_pending(self) -> List[IdeaProposal]:
        return self.pending_ideas


