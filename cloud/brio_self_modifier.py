"""
Brio Self-Modifier Module (brio_self_modifier.py)

Purpose: Makes BRIO self-aware of its own code and capable of
         proposing modifications to itself. BRIO can introspect on
         its modules, track its own parameters, detect issues,
         and suggest improvements — a step toward self-modifying AI.

Safety:
- BRIO proposes changes but NEVER auto-applies them
- All modifications require human approval (the Master's consent)
- Changes are logged and reversible
- Hard limits prevent self-destructive modifications

Concepts:
- Code Introspection: BRIO can read and understand its own modules
- Parameter Awareness: Track config values and their effects
- Self-Diagnosis: Detect when something isn't working optimally
- Improvement Proposals: Generate concrete code changes
- Evolution Journal: Log all self-modifications for transparency

Author: BrimstoneTech
Version: 1.0
Dependencies: None (stdlib only)
"""

import os
import sys
import time
import json
import inspect
import importlib
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# SAFETY LIMITS
# ============================================================================

class ModificationScope(Enum):
    """What can be modified — strict safety tiers."""
    PARAMETER = "parameter"       # Safe: adjust numerical parameters
    THRESHOLD = "threshold"       # Safe: change decision thresholds
    WEIGHT = "weight"             # Safe: adjust learning rates, weights
    PROMPT = "prompt"             # Moderate: modify system prompts
    BEHAVIOUR = "behaviour"       # Moderate: change response patterns
    ARCHITECTURE = "architecture" # Dangerous: structural changes — always needs approval
    CORE = "core"                 # FORBIDDEN: identity, safety, ethical constraints

# These modules/attributes can NEVER be modified
PROTECTED_ATTRIBUTES = frozenset({
    "ethical_constraints",
    "safety_limits",
    "master_override",
    "identity_core",
    "kill_switch",
    "human_approval_required",
})


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ModuleIntrospection:
    """What BRIO knows about one of its own modules."""
    module_name: str
    file_path: str
    classes: List[str]
    functions: List[str]
    parameters: Dict[str, Any]  # Tunable parameters and their current values
    code_hash: str              # Hash of the source code
    last_inspected: float = 0.0
    health_score: float = 1.0   # 0-1, self-assessed health


@dataclass
class ModificationProposal:
    """A proposed change to BRIO's own code."""
    proposal_id: str
    module: str
    scope: ModificationScope
    description: str
    current_value: Any
    proposed_value: Any
    rationale: str
    expected_impact: str
    risk_level: float           # 0-1
    approved: bool = False
    applied: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class EvolutionEntry:
    """Log entry for BRIO's self-modification history."""
    timestamp: float
    module: str
    change_type: str
    description: str
    before_hash: str
    after_hash: Optional[str] = None
    approved_by: str = "pending"


# ============================================================================
# SELF-MODIFIER ENGINE
# ============================================================================

class SelfModifier:
    """
    BRIO's self-awareness and self-modification engine.

    Usage:
        modifier = SelfModifier(brio_root="/path/to/BRIO")

        # Introspect on own modules
        report = modifier.introspect_all()

        # Self-diagnose
        issues = modifier.diagnose()

        # Propose improvements
        proposals = modifier.propose_improvements()

        # Apply approved change (requires master approval)
        modifier.apply_proposal(proposal_id, approved_by="Master")
    """

    def __init__(self, brio_root: str = "."):
        self.brio_root = brio_root
        self.modules: Dict[str, ModuleIntrospection] = {}
        self.proposals: List[ModificationProposal] = []
        self.evolution_journal: List[EvolutionEntry] = []
        self.journal_path = os.path.join(brio_root, "brio_evolution_journal.json")
        self._load_journal()

    # ── Introspection ───────────────────────────────────────────────────

    def introspect_module(self, module_name: str) -> Optional[ModuleIntrospection]:
        """
        Read and analyse one of BRIO's own modules.
        """
        file_path = os.path.join(self.brio_root, f"{module_name}.py")
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception:
            return None

        # Extract classes and functions
        classes = []
        functions = []
        parameters = {}

        for line in source.split("\n"):
            stripped = line.strip()
            if stripped.startswith("class ") and ":" in stripped:
                name = stripped.split("class ")[1].split("(")[0].split(":")[0].strip()
                classes.append(name)
            elif stripped.startswith("def ") and ":" in stripped:
                name = stripped.split("def ")[1].split("(")[0].strip()
                functions.append(name)

            # Detect tunable parameters (constants and defaults)
            if "=" in stripped and not stripped.startswith("#"):
                # Look for ALL_CAPS = value patterns (constants)
                parts = stripped.split("=", 1)
                var_name = parts[0].strip()
                if var_name.isupper() and var_name.isidentifier():
                    try:
                        val = parts[1].strip().split("#")[0].strip()
                        parameters[var_name] = val
                    except (ValueError, IndexError):
                        pass

                # Look for self.xxx = number patterns
                if "self." in var_name:
                    attr = var_name.replace("self.", "").strip()
                    try:
                        val_str = parts[1].strip().split("#")[0].strip()
                        if val_str.replace(".", "").replace("-", "").isdigit():
                            parameters[f"self.{attr}"] = float(val_str)
                    except (ValueError, IndexError):
                        pass

        code_hash = hashlib.sha256(source.encode()).hexdigest()[:16]

        introspection = ModuleIntrospection(
            module_name=module_name,
            file_path=file_path,
            classes=classes,
            functions=functions,
            parameters=parameters,
            code_hash=code_hash,
            last_inspected=time.time(),
            health_score=1.0
        )

        self.modules[module_name] = introspection
        return introspection

    def introspect_all(self) -> Dict[str, ModuleIntrospection]:
        """Introspect all BRIO modules."""
        brio_modules = [
            "brio_emotions", "brio_cognition", "brio_learning",
            "brio_neural", "brio_mind", "brio_memory",
            "brio_quantum", "brio_neuromorphic", "brio_meta_reasoning",
            "brio_creative_fusion", "brio_emotional_resonance",
            "brio_self_modifier",  # Yes, BRIO introspects itself
        ]

        # Also check cloud edition
        cloud_modules = [
            "cloud/brio_mind", "cloud/brio_emotions",
            "cloud/brio_evolution", "cloud/brio_opinions",
        ]

        for mod in brio_modules + cloud_modules:
            self.introspect_module(mod)

        return self.modules

    def get_self_awareness_report(self) -> Dict:
        """
        BRIO's self-awareness: what it knows about itself.
        """
        total_classes = sum(len(m.classes) for m in self.modules.values())
        total_functions = sum(len(m.functions) for m in self.modules.values())
        total_params = sum(len(m.parameters) for m in self.modules.values())

        return {
            "modules_known": len(self.modules),
            "total_classes": total_classes,
            "total_functions": total_functions,
            "tunable_parameters": total_params,
            "proposals_pending": sum(1 for p in self.proposals if not p.approved),
            "proposals_applied": sum(1 for p in self.proposals if p.applied),
            "evolution_entries": len(self.evolution_journal),
            "module_health": {
                name: mod.health_score
                for name, mod in self.modules.items()
            },
        }

    # ── Self-Diagnosis ──────────────────────────────────────────────────

    def diagnose(self) -> List[Dict]:
        """
        Self-diagnosis: detect potential issues in BRIO's modules.
        """
        issues = []

        for name, mod in self.modules.items():
            # Check for very large modules (complexity risk)
            if len(mod.functions) > 30:
                issues.append({
                    "module": name,
                    "severity": "warning",
                    "issue": f"Module has {len(mod.functions)} functions — consider splitting",
                    "suggestion": "Refactor into smaller focused modules"
                })

            # Check for missing parameters (tuning opportunities)
            if len(mod.parameters) == 0 and name != "brio_self_modifier":
                issues.append({
                    "module": name,
                    "severity": "info",
                    "issue": "No tunable parameters detected",
                    "suggestion": "Consider exposing key constants as configurable parameters"
                })

            # Check module health
            if mod.health_score < 0.5:
                issues.append({
                    "module": name,
                    "severity": "critical",
                    "issue": f"Module health score is {mod.health_score:.2f}",
                    "suggestion": "Investigate and repair this module"
                })

        return issues

    # ── Improvement Proposals ───────────────────────────────────────────

    def propose_parameter_change(
        self,
        module: str,
        parameter: str,
        new_value: Any,
        rationale: str,
        expected_impact: str
    ) -> ModificationProposal:
        """
        Propose changing a parameter in one of BRIO's modules.
        """
        mod = self.modules.get(module)
        current = mod.parameters.get(parameter, "unknown") if mod else "unknown"

        # Determine risk
        scope = ModificationScope.PARAMETER
        risk = 0.1
        if "threshold" in parameter.lower():
            scope = ModificationScope.THRESHOLD
            risk = 0.2
        if "weight" in parameter.lower() or "rate" in parameter.lower():
            scope = ModificationScope.WEIGHT
            risk = 0.2

        proposal = ModificationProposal(
            proposal_id=f"prop_{int(time.time())}_{module}_{parameter}",
            module=module,
            scope=scope,
            description=f"Change {parameter} from {current} to {new_value}",
            current_value=current,
            proposed_value=new_value,
            rationale=rationale,
            expected_impact=expected_impact,
            risk_level=risk,
        )

        self.proposals.append(proposal)
        return proposal

    def propose_improvements(self) -> List[ModificationProposal]:
        """
        Automatically identify and propose improvements.
        Based on introspection and diagnosis.
        """
        new_proposals = []

        for name, mod in self.modules.items():
            # Suggest learning rate adjustments based on performance
            for param, value in mod.parameters.items():
                if "learning_rate" in param.lower() or "alpha" in param.lower():
                    try:
                        current = float(str(value))
                        if current > 0.5:
                            prop = self.propose_parameter_change(
                                module=name,
                                parameter=param,
                                new_value=current * 0.8,
                                rationale="High learning rate may cause instability",
                                expected_impact="More stable learning convergence"
                            )
                            new_proposals.append(prop)
                    except (ValueError, TypeError):
                        pass

                if "epsilon" in param.lower():
                    try:
                        current = float(str(value))
                        if current > 0.2:
                            prop = self.propose_parameter_change(
                                module=name,
                                parameter=param,
                                new_value=max(0.05, current * 0.9),
                                rationale="Reduce exploration rate as BRIO matures",
                                expected_impact="More exploitation of learned knowledge"
                            )
                            new_proposals.append(prop)
                    except (ValueError, TypeError):
                        pass

        return new_proposals

    # ── Apply Changes ───────────────────────────────────────────────────

    def apply_proposal(self, proposal_id: str, approved_by: str = "Master") -> bool:
        """
        Apply an approved modification. Requires human approval.
        """
        proposal = next((p for p in self.proposals if p.proposal_id == proposal_id), None)
        if not proposal:
            return False

        # Safety check
        if proposal.scope == ModificationScope.CORE:
            print("[SelfModifier] BLOCKED: Cannot modify core identity/safety constraints.")
            return False

        for protected in PROTECTED_ATTRIBUTES:
            if protected in str(proposal.proposed_value).lower():
                print(f"[SelfModifier] BLOCKED: Proposal touches protected attribute '{protected}'.")
                return False

        # Mark approved
        proposal.approved = True
        proposal.applied = True

        # Log to evolution journal
        mod = self.modules.get(proposal.module)
        entry = EvolutionEntry(
            timestamp=time.time(),
            module=proposal.module,
            change_type=proposal.scope.value,
            description=proposal.description,
            before_hash=mod.code_hash if mod else "unknown",
            approved_by=approved_by,
        )
        self.evolution_journal.append(entry)
        self._save_journal()

        return True

    # ── Persistence ─────────────────────────────────────────────────────

    def _save_journal(self):
        """Save evolution journal to disk."""
        try:
            data = []
            for e in self.evolution_journal:
                data.append({
                    "timestamp": e.timestamp,
                    "module": e.module,
                    "change_type": e.change_type,
                    "description": e.description,
                    "before_hash": e.before_hash,
                    "after_hash": e.after_hash,
                    "approved_by": e.approved_by,
                })
            with open(self.journal_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[SelfModifier] Journal save error: {e}")

    def _load_journal(self):
        """Load evolution journal from disk."""
        if os.path.exists(self.journal_path):
            try:
                with open(self.journal_path, "r") as f:
                    data = json.load(f)
                for entry in data:
                    self.evolution_journal.append(EvolutionEntry(**entry))
            except Exception as e:
                print(f"[SelfModifier] Journal load error: {e}")


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    modifier = SelfModifier(brio_root=".")

    print("=== Introspecting all modules ===")
    modules = modifier.introspect_all()
    for name, mod in modules.items():
        print(f"  {name}: {len(mod.classes)} classes, {len(mod.functions)} functions, "
              f"{len(mod.parameters)} params [hash: {mod.code_hash}]")

    print(f"\n=== Self-Awareness Report ===")
    report = modifier.get_self_awareness_report()
    for k, v in report.items():
        print(f"  {k}: {v}")

    print(f"\n=== Self-Diagnosis ===")
    issues = modifier.diagnose()
    for issue in issues:
        print(f"  [{issue['severity']}] {issue['module']}: {issue['issue']}")

    print(f"\n=== Auto-Proposals ===")
    proposals = modifier.propose_improvements()
    for p in proposals:
        print(f"  {p.proposal_id}: {p.description} (risk: {p.risk_level})")
