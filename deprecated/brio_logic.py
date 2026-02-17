"""
Brio Logic Module (brio_logic.py)

Purpose: Implements Subjective Logic for Trust and Decision Modeling.
         See Equation 5 in Brio Design Optimization.

Concepts:
- Opinion w = (b, d, u)
  b: Belief (Trust)
  d: Disbelief (Distrust)
  u: Uncertainty
  a: Base rate (default 0.5)

Invariant: b + d + u = 1.0
"""

from dataclasses import dataclass
import math

@dataclass
class SubjectiveOpinion:
    b: float  # Belief
    d: float  # Disbelief
    u: float  # Uncertainty
    a: float = 0.5  # Base rate (prior probability)

    def __post_init__(self):
        """Ensure invariants are met upon creation (normalize if needed)"""
        total = self.b + self.d + self.u
        if abs(total - 1.0) > 0.001:
            # Normalize
            if total == 0:
                self.b, self.d, self.u = 0, 0, 1 # Total uncertainty fallback
            else:
                self.b /= total
                self.d /= total
                self.u /= total
                
    def expected_probability(self) -> float:
        """
        Calculate expected probability E(x)
        E = b + a * u
        """
        return self.b + (self.a * self.u)

    def fuse(self, other: 'SubjectiveOpinion') -> 'SubjectiveOpinion':
        """
        Combine this opinion with another using the Consensus Operator (Cumulative Fusion).
        Used when two independent agents/sensors observe the same event.
        
        Formula for Cumulative Fusion:
        k = uA + uB - uA*uB
        b = (bA*uB + bB*uA) / k
        d = (dA*uB + dB*uA) / k
        u = (uA*uB) / k
        """
        if self.u == 0 and other.u == 0:
            # Dogmatic conflict - simplified handling (average)
            return SubjectiveOpinion(
                (self.b + other.b) / 2,
                (self.d + other.d) / 2,
                0.0
            )

        k = self.u + other.u - (self.u * other.u)
        
        if k == 0:
            # Should be covered by dogmatic check, but safety fallback
            return SubjectiveOpinion(0, 0, 1)

        new_b = (self.b * other.u + other.b * self.u) / k
        new_d = (self.d * other.u + other.d * self.u) / k
        new_u = (self.u * other.u) / k
        
        return SubjectiveOpinion(new_b, new_d, new_u, self.a)


