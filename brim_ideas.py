"""
BRIM Idea Module (brim_ideas.py)

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

from brim_cognition import DirichletModel

class IdeaGenerator:
    """
    Generates proactive 'Thoughts' or 'Ideas' for Brio 
    using a Dirichlet Distribution (Eq 3) for adaptive prioritization.
    """
    
    def __init__(self):
        self.pending_ideas: List[IdeaProposal] = []
        self.history: List[IdeaProposal] = []
        self.dirichlet = DirichletModel([t.value for t in IdeaType][:3])
        
        # Pool of potential Brio thoughts
        self.idea_pool = {
            IdeaType.MAINTENANCE: [
                "I see your desktop is cluttered. Shall I organize the files into folders?",
                "Your system is running slightly hot. Should I analyze which background processes are heavy?",
                "I've noticed some duplicate documents. May I help you archive the older versions?"
            ],
            IdeaType.RESEARCH: [
                "I wonder how the 'Minimax' algorithm we talked about scales with more complex games?",
                "I've been thinking about the 'SentientOS' design. Should I look for more efficient differential equation solvers?",
                "I wonder what the current top trending technologies are in the AI space today?"
            ],
            IdeaType.FUN: [
                "I'd like to try a new visual pulse pattern for my Halo. May I show you some options?",
                "Would you like to see a visualization of my current emotional vector space over the last hour?",
                "I found a curious mathematical property of prime numbers. May I share it?"
            ]
        }

    def generate_thought(self, curiosity: float, joy: float, knowledge_count: int) -> Optional[IdeaProposal]:
        """
        Periodically returns a new idea weighted by curiosity and Dirichlet priors.
        Requires 'assimilated data' (knowledge_count) to function.
        """
        # Data Assimilation Check: Brio needs to 'know' enough before having ideas
        if knowledge_count < 3:
            return None

        if curiosity < 0.65: # Slightly higher threshold for 'considerate' behavior
            return None
        
        # Combine Dirichlet learning with emotional context (Eq 2 + Eq 3 hybrid)
        d_weights = self.dirichlet.get_probabilities()
        
        # Emotional bias
        final_weights = []
        types = [IdeaType.MAINTENANCE, IdeaType.RESEARCH, IdeaType.FUN]
        
        for t in types:
            w = d_weights[t.value]
            # Higher weighting for research if knowledge is growing
            if t == IdeaType.RESEARCH and knowledge_count > 10: w *= 1.5
            if t == IdeaType.FUN and joy > 0.8: w *= 2.0
            if t == IdeaType.MAINTENANCE and joy < 0.3: w *= 2.0
            final_weights.append(w)
            
        idea_type = random.choices(types, weights=final_weights)[0]
        description = random.choice(self.idea_pool[idea_type])
        
        # Add dynamic 'growth' prefix to sound more evolving
        if knowledge_count > 15:
            description = "I've been analyzing our recent data... " + description
        elif knowledge_count > 5:
            description = "Based on what I've learned... " + description

        idea_id = f"IDEA_{int(datetime.now().timestamp())}_{len(self.history)}"
        
        for p in self.pending_ideas:
            if p.description == description: return None
                
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
