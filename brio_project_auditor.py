"""
BRIO Project Auditor (brio_project_auditor.py)
================================================
Gives BRIO the ability to:
  1. DECONSTRUCT a complex task into sub-steps
  2. ESTIMATE time for each step
  3. PRESENT a roadmap with ETA before execution
  4. TRACK progress during execution
  5. REPORT completion status

Usage:
    auditor = ProjectAuditor(system_ref=brio_system)
    audit = auditor.audit("Build a low-poly house in Blender")
    # Returns a structured ProjectAudit with steps, ETA, and approval gate

Integration:
    - In brio_autonomy.py, detect "audit", "assess", "plan", "roadmap", "eta"
    - Route to auditor.audit(user_input)
    - BRIO presents the plan and waits for "proceed" / "cancel"
"""

import json
import time
import logging
import os
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Tuple
from enum import Enum

log = logging.getLogger("brio.auditor")


# ─────────────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────────────

class StepStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskComplexity(Enum):
    TRIVIAL = "trivial"         # < 2 min  (e.g., open an app)
    SIMPLE = "simple"           # 2-5 min  (e.g., create a cube, save a file)
    MODERATE = "moderate"       # 5-15 min (e.g., build a simple scene)
    COMPLEX = "complex"         # 15-45 min (e.g., character model, full layout)
    ADVANCED = "advanced"       # 45+ min  (e.g., animated scene, full project)


@dataclass
class ProjectStep:
    """A single step in the project roadmap."""
    id: int
    name: str
    description: str
    estimated_minutes: float
    tool: str = "blender"       # blender, gimp, krita, shell, python, browser
    method: str = "script"      # script (bpy), gui (mouse), manual (user does it)
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    notes: str = ""

    def to_dict(self):
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class ProjectAudit:
    """The full project roadmap produced by the auditor."""
    project_name: str
    description: str
    complexity: TaskComplexity
    steps: List[ProjectStep] = field(default_factory=list)
    total_eta_minutes: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    approved: bool = False
    current_step: int = 0

    @property
    def eta_human(self) -> str:
        """Human-readable ETA."""
        if self.total_eta_minutes < 1:
            return "< 1 minute"
        elif self.total_eta_minutes < 60:
            return f"~{int(self.total_eta_minutes)} minutes"
        else:
            hours = int(self.total_eta_minutes // 60)
            mins = int(self.total_eta_minutes % 60)
            return f"~{hours}h {mins}m"

    @property
    def progress_percent(self) -> float:
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        return round((completed / len(self.steps)) * 100, 1)

    def to_dict(self):
        return {
            "project_name": self.project_name,
            "description": self.description,
            "complexity": self.complexity.value,
            "steps": [s.to_dict() for s in self.steps],
            "total_eta_minutes": self.total_eta_minutes,
            "eta_human": self.eta_human,
            "created_at": self.created_at,
            "approved": self.approved,
            "current_step": self.current_step,
            "progress_percent": self.progress_percent,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Base: Task Templates
# These are "recipes" BRIO uses to estimate and plan tasks.
# As you feed him more knowledge, these expand.
# ─────────────────────────────────────────────────────────────────────────────

TASK_TEMPLATES: Dict[str, Dict] = {
    # ── Blender 3D ────────────────────────────────────────────────────────
    "cube": {
        "complexity": TaskComplexity.TRIVIAL,
        "steps": [
            ("Open Blender", "Launch Blender application", 0.5, "blender", "script"),
            ("Create Cube", "bpy.ops.mesh.primitive_cube_add()", 0.2, "blender", "script"),
            ("Position Camera", "Set camera to face the cube", 0.3, "blender", "script"),
        ]
    },
    "sphere": {
        "complexity": TaskComplexity.TRIVIAL,
        "steps": [
            ("Open Blender", "Launch Blender application", 0.5, "blender", "script"),
            ("Create Sphere", "bpy.ops.mesh.primitive_uv_sphere_add()", 0.2, "blender", "script"),
            ("Smooth Shading", "Apply smooth shading to the sphere", 0.3, "blender", "script"),
        ]
    },
    "low_poly_tree": {
        "complexity": TaskComplexity.MODERATE,
        "steps": [
            ("Open Blender", "Launch Blender and clear default scene", 0.5, "blender", "script"),
            ("Create Trunk", "Add cylinder mesh for trunk, scale to tree proportions", 1.0, "blender", "script"),
            ("Shape Trunk", "Apply slight taper using proportional editing", 1.5, "blender", "script"),
            ("Create Canopy", "Add icosphere with low subdivisions for foliage", 1.0, "blender", "script"),
            ("Position Canopy", "Move canopy sphere atop the trunk", 0.5, "blender", "script"),
            ("Assign Materials", "Green material for canopy, brown for trunk", 2.0, "blender", "script"),
            ("Ground Plane", "Add a flat plane underneath as ground", 0.5, "blender", "script"),
            ("Camera & Lighting", "Position camera and add sun lamp", 1.5, "blender", "script"),
            ("Render Preview", "Render a preview image (F12)", 2.0, "blender", "script"),
        ]
    },
    "low_poly_house": {
        "complexity": TaskComplexity.COMPLEX,
        "steps": [
            ("Open Blender", "Launch Blender and clear default scene", 0.5, "blender", "script"),
            ("Foundation", "Create a scaled cube as the base/floor", 1.0, "blender", "script"),
            ("Walls", "Extrude the foundation upward to form walls", 2.0, "blender", "script"),
            ("Roof Structure", "Add a prism/wedge shape on top for the roof", 3.0, "blender", "script"),
            ("Door Opening", "Use Boolean modifier to cut a door shape", 2.0, "blender", "script"),
            ("Window Openings", "Use Boolean modifier to cut 2-4 window shapes", 3.0, "blender", "script"),
            ("Door Mesh", "Create a thin cube for the door panel", 1.0, "blender", "script"),
            ("Window Frames", "Create thin cubes for window frames", 2.0, "blender", "script"),
            ("Materials", "Assign wall, roof, door, and window materials", 3.0, "blender", "script"),
            ("Ground & Path", "Add ground plane and a simple path to the door", 1.5, "blender", "script"),
            ("Lighting", "Add sun lamp and ambient occlusion", 1.5, "blender", "script"),
            ("Camera Setup", "Position camera for a 3/4 view", 1.0, "blender", "script"),
            ("Final Render", "Render the scene at 1920x1080", 3.0, "blender", "script"),
        ]
    },
    "landscape": {
        "complexity": TaskComplexity.COMPLEX,
        "steps": [
            ("Open Blender", "Launch and clear scene", 0.5, "blender", "script"),
            ("Terrain Mesh", "Create subdivided plane (100x100 grid)", 1.0, "blender", "script"),
            ("Terrain Sculpting", "Apply displacement with cloud/noise texture", 3.0, "blender", "script"),
            ("Water Plane", "Add a transparent blue plane for water level", 1.5, "blender", "script"),
            ("Vegetation", "Scatter low-poly trees using particle system", 5.0, "blender", "script"),
            ("Sky & Atmosphere", "Set up world shader for sky gradient", 2.0, "blender", "script"),
            ("Sun Lighting", "Add sun lamp at golden-hour angle", 1.0, "blender", "script"),
            ("Camera Flyover", "Set camera path for aerial view", 2.0, "blender", "script"),
            ("Render Settings", "Configure render engine (EEVEE for speed)", 1.0, "blender", "script"),
            ("Final Render", "Render scene", 3.0, "blender", "script"),
        ]
    },
    "character_model": {
        "complexity": TaskComplexity.ADVANCED,
        "steps": [
            ("Open Blender", "Launch and set up modeling workspace", 0.5, "blender", "script"),
            ("Reference Setup", "Load reference images to background planes", 2.0, "blender", "gui"),
            ("Torso Base", "Create and shape cube into torso form", 5.0, "blender", "script"),
            ("Head", "Extrude and shape head from torso", 5.0, "blender", "script"),
            ("Arms", "Extrude arms from torso sides", 4.0, "blender", "script"),
            ("Hands (simplified)", "Create low-poly mitten-style hands", 3.0, "blender", "script"),
            ("Legs", "Extrude legs from torso bottom", 4.0, "blender", "script"),
            ("Feet", "Extrude simple feet shapes", 2.0, "blender", "script"),
            ("Symmetry Check", "Apply mirror modifier and verify", 1.5, "blender", "script"),
            ("UV Unwrap", "Unwrap mesh for texturing", 3.0, "blender", "script"),
            ("Base Materials", "Assign skin, clothing, and hair materials", 4.0, "blender", "script"),
            ("Armature", "Add skeleton bones for posing", 5.0, "blender", "script"),
            ("Weight Painting", "Paint vertex weights for deformation", 5.0, "blender", "gui"),
            ("Test Pose", "Move bones to verify rig works", 2.0, "blender", "gui"),
            ("Final Render", "Render character in A-pose or action pose", 3.0, "blender", "script"),
        ]
    },
    # ── Graphics (GIMP/Krita) ─────────────────────────────────────────────
    "logo_design": {
        "complexity": TaskComplexity.MODERATE,
        "steps": [
            ("Open Canvas", "Create new 1024x1024 canvas", 0.5, "gimp", "script"),
            ("Background", "Fill with brand color gradient", 1.0, "gimp", "script"),
            ("Shape Layer", "Create geometric shape for logo mark", 2.0, "gimp", "script"),
            ("Typography", "Add company name with chosen font", 2.0, "gimp", "gui"),
            ("Color Balance", "Adjust colors for harmony", 1.5, "gimp", "script"),
            ("Export", "Export as PNG and SVG", 0.5, "gimp", "script"),
        ]
    },
    # ── General / System ──────────────────────────────────────────────────
    "file_organization": {
        "complexity": TaskComplexity.SIMPLE,
        "steps": [
            ("Scan Directory", "List all files and classify by type", 1.0, "shell", "script"),
            ("Create Folders", "Create organized folder structure", 0.5, "shell", "script"),
            ("Move Files", "Sort files into appropriate folders", 2.0, "shell", "script"),
            ("Report", "Generate summary of what was organized", 0.5, "shell", "script"),
        ]
    },
}

# Keywords that map natural language to template keys
TEMPLATE_KEYWORDS: Dict[str, List[str]] = {
    "cube": ["cube", "box", "block"],
    "sphere": ["sphere", "ball", "globe", "orb"],
    "low_poly_tree": ["tree", "plant", "vegetation", "forest"],
    "low_poly_house": ["house", "building", "cabin", "home", "cottage", "structure"],
    "landscape": ["landscape", "terrain", "environment", "world", "scene", "mountain"],
    "character_model": ["character", "person", "human", "figure", "avatar", "body", "model"],
    "logo_design": ["logo", "brand", "icon", "badge", "emblem"],
    "file_organization": ["organize", "sort files", "clean up", "tidy"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Project Auditor
# ─────────────────────────────────────────────────────────────────────────────

class ProjectAuditor:
    """
    BRIO's strategic planning module.
    
    Before executing a complex task, BRIO will:
    1. Identify what type of project this is
    2. Look up a template or generate a generic plan
    3. Estimate time for each step
    4. Present the roadmap to the user
    5. Wait for approval before executing
    """

    AUDIT_LOG = "brio_projects.json"

    def __init__(self, system_ref=None):
        self.system = system_ref
        self.active_project: Optional[ProjectAudit] = None
        self.project_history: List[ProjectAudit] = []
        self._load_history()
        log.info("[Auditor] Project Auditor initialized.")

    # ─── Main Entry Point ─────────────────────────────────────────────────

    def audit(self, task_description: str) -> str:
        """
        Main entry: Analyze a task, build a roadmap, return formatted plan.
        """
        task_lower = task_description.lower()

        # 1. Find the best matching template
        template_key = self._match_template(task_lower)

        if template_key and template_key in TASK_TEMPLATES:
            template = TASK_TEMPLATES[template_key]
            audit = self._build_from_template(task_description, template_key, template)
        else:
            # No template — generate a generic audit
            audit = self._build_generic_audit(task_description)

        # 2. Store as active project
        self.active_project = audit
        self._save_history()

        # 3. Format and return
        return self._format_roadmap(audit)

    def approve(self) -> str:
        """User approved the plan — mark it ready for execution."""
        if not self.active_project:
            return "❓ No project is pending approval. Ask me to *assess* a task first."

        self.active_project.approved = True
        self._save_history()
        return (
            f"✅ **Project Approved:** {self.active_project.project_name}\n"
            f"Starting execution. ETA: {self.active_project.eta_human}\n\n"
            f"I'll update you as each step completes. Say **'status'** anytime to check progress."
        )

    def reject(self) -> str:
        """User rejected the plan."""
        if not self.active_project:
            return "❓ No project is pending."

        name = self.active_project.project_name
        self.active_project = None
        return f"✋ **Project Cancelled:** {name}\nTell me what you'd like to change and I'll re-plan."

    def get_status(self) -> str:
        """Return progress on the active project."""
        if not self.active_project:
            return "📋 No active project. Say *'assess: build a house in Blender'* to start planning."

        audit = self.active_project
        lines = [
            f"📊 **Project Status: {audit.project_name}**",
            f"Progress: {audit.progress_percent}% complete",
            f"Complexity: {audit.complexity.value.upper()}",
            "",
        ]

        for step in audit.steps:
            if step.status == StepStatus.COMPLETED:
                icon = "✅"
            elif step.status == StepStatus.IN_PROGRESS:
                icon = "🔄"
            elif step.status == StepStatus.FAILED:
                icon = "❌"
            elif step.status == StepStatus.SKIPPED:
                icon = "⏭️"
            else:
                icon = "⬜"

            lines.append(f"  {icon} Step {step.id}: {step.name} ({step.estimated_minutes}m)")

        completed_time = sum(
            s.estimated_minutes for s in audit.steps
            if s.status == StepStatus.COMPLETED
        )
        remaining_time = audit.total_eta_minutes - completed_time

        lines.append(f"\n⏱️ Time remaining: ~{int(remaining_time)} minutes")
        return "\n".join(lines)

    def complete_step(self, step_id: int, notes: str = "") -> str:
        """Mark a step as completed."""
        if not self.active_project:
            return "No active project."

        for step in self.active_project.steps:
            if step.id == step_id:
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.now().isoformat()
                step.notes = notes
                self.active_project.current_step = step_id + 1
                self._save_history()

                # Check if entire project is done
                all_done = all(
                    s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
                    for s in self.active_project.steps
                )
                if all_done:
                    return (
                        f"✅ Step {step_id} complete: {step.name}\n\n"
                        f"🎉 **PROJECT COMPLETE: {self.active_project.project_name}!**\n"
                        f"All {len(self.active_project.steps)} steps finished."
                    )

                return f"✅ Step {step_id} complete: {step.name}"

        return f"❌ Step {step_id} not found."

    # ─── Template Matching ────────────────────────────────────────────────

    def _match_template(self, text: str) -> Optional[str]:
        """Find the best matching task template from keywords."""
        best_match = None
        best_score = 0

        for key, keywords in TEMPLATE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_match = key

        return best_match if best_score > 0 else None

    def _build_from_template(self, description: str, key: str,
                             template: Dict) -> ProjectAudit:
        """Build a ProjectAudit from a known template."""
        steps = []
        for i, (name, desc, mins, tool, method) in enumerate(template["steps"], 1):
            steps.append(ProjectStep(
                id=i,
                name=name,
                description=desc,
                estimated_minutes=mins,
                tool=tool,
                method=method,
            ))

        total_eta = sum(s.estimated_minutes for s in steps)

        return ProjectAudit(
            project_name=f"{key.replace('_', ' ').title()} Project",
            description=description,
            complexity=template["complexity"],
            steps=steps,
            total_eta_minutes=total_eta,
        )

    def _build_generic_audit(self, description: str) -> ProjectAudit:
        """
        For tasks without a template, generate a generic plan.
        Uses word count and keyword density to estimate complexity.
        """
        words = description.lower().split()
        word_count = len(words)

        # Heuristic complexity estimation
        complex_words = {"animation", "rigged", "textured", "uv", "render",
                         "particle", "physics", "simulation", "sculpt",
                         "character", "landscape", "architectural", "realistic"}
        complexity_score = sum(1 for w in words if w in complex_words)

        if complexity_score >= 3 or word_count > 20:
            complexity = TaskComplexity.ADVANCED
        elif complexity_score >= 2 or word_count > 12:
            complexity = TaskComplexity.COMPLEX
        elif complexity_score >= 1 or word_count > 6:
            complexity = TaskComplexity.MODERATE
        else:
            complexity = TaskComplexity.SIMPLE

        # Generate generic steps
        time_multiplier = {
            TaskComplexity.TRIVIAL: 0.5,
            TaskComplexity.SIMPLE: 1.0,
            TaskComplexity.MODERATE: 2.0,
            TaskComplexity.COMPLEX: 3.0,
            TaskComplexity.ADVANCED: 5.0,
        }
        mult = time_multiplier[complexity]

        steps = [
            ProjectStep(1, "Setup", "Open application and prepare workspace", 0.5 * mult, "blender", "script"),
            ProjectStep(2, "Base Geometry", "Create primary shapes and forms", 2.0 * mult, "blender", "script"),
            ProjectStep(3, "Detail Pass", "Add secondary details and features", 3.0 * mult, "blender", "script"),
            ProjectStep(4, "Materials", "Assign colors and materials", 2.0 * mult, "blender", "script"),
            ProjectStep(5, "Lighting", "Set up scene lighting", 1.0 * mult, "blender", "script"),
            ProjectStep(6, "Camera", "Position camera for final composition", 0.5 * mult, "blender", "script"),
            ProjectStep(7, "Render", "Render final output", 2.0 * mult, "blender", "script"),
        ]

        total_eta = sum(s.estimated_minutes for s in steps)

        return ProjectAudit(
            project_name=f"Custom Project: {description[:50]}",
            description=description,
            complexity=complexity,
            steps=steps,
            total_eta_minutes=total_eta,
        )

    # ─── Formatting ───────────────────────────────────────────────────────

    def _format_roadmap(self, audit: ProjectAudit) -> str:
        """Format the audit as a beautiful, readable roadmap."""
        complexity_icons = {
            TaskComplexity.TRIVIAL: "🟢",
            TaskComplexity.SIMPLE: "🟡",
            TaskComplexity.MODERATE: "🟠",
            TaskComplexity.COMPLEX: "🔴",
            TaskComplexity.ADVANCED: "⚫",
        }
        icon = complexity_icons.get(audit.complexity, "⬜")

        lines = [
            f"📋 **PROJECT AUDIT: {audit.project_name}**",
            f"",
            f"  {icon} Complexity: **{audit.complexity.value.upper()}**",
            f"  ⏱️ Estimated Time: **{audit.eta_human}**",
            f"  📝 Steps: **{len(audit.steps)}**",
            f"",
            f"**Roadmap:**",
        ]

        for step in audit.steps:
            method_icon = "🐍" if step.method == "script" else "🖱️" if step.method == "gui" else "👤"
            lines.append(
                f"  {step.id}. {method_icon} **{step.name}** — {step.description} "
                f"*({step.estimated_minutes}m)*"
            )

        lines.extend([
            "",
            "───────────────────────────────",
            f"🕐 Total ETA: **{audit.eta_human}**",
            "",
            "Reply **'proceed'** to start execution, or **'cancel'** to abort.",
            "Say **'modify step 3: use EEVEE instead'** to adjust the plan.",
        ])

        return "\n".join(lines)

    # ─── Persistence ──────────────────────────────────────────────────────

    def _save_history(self):
        try:
            data = {
                "active": self.active_project.to_dict() if self.active_project else None,
                "history": [p.to_dict() for p in self.project_history[-20:]],
                "saved_at": datetime.now().isoformat(),
            }
            with open(self.AUDIT_LOG, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.warning(f"[Auditor] Could not save: {e}")

    def _load_history(self):
        try:
            if os.path.exists(self.AUDIT_LOG):
                with open(self.AUDIT_LOG, "r", encoding="utf-8") as f:
                    data = json.load(f)
                log.info(f"[Auditor] Loaded {len(data.get('history', []))} past projects.")
        except Exception as e:
            log.warning(f"[Auditor] Could not load history: {e}")
