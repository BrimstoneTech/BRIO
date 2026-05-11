"""
BRIO Autonomy Bridge (brio_autonomy.py)
=========================================
Wires BrioLocalAccess + BrioDesktopAgent into the Brain pipeline.

This is the "missing link" that gives BRIO real machine autonomy:
  - Natural language → intent detection → safe execution
  - Confirmation gate for destructive operations
  - Persistent action log
  - Unified response formatting

Usage (in brio_main.py _initialize_all_systems):
    from brio_autonomy import BrioAutonomy
    self.autonomy = BrioAutonomy(system_ref=self)

Usage (in BrioBrain.brio_core or handle_command):
    result = self.system.autonomy.handle(user_input)
    if result is not None:
        return result   # handled locally, skip Ollama
"""

import re
import json
import logging
import os
from datetime import datetime
from typing import Optional, Tuple, Dict, List

from brio_local_access import BrioLocalAccess
from brio_project_auditor import ProjectAuditor

log = logging.getLogger("brio.autonomy")

# ─── Desktop Agent is optional (needs pyautogui) ──────────────────────────────
try:
    from brio_desktop_agent import DesktopAgent
    HAS_AGENT = True
except ImportError:
    HAS_AGENT = False
    log.warning("[Autonomy] brio_desktop_agent not importable — GUI control disabled.")


# ─────────────────────────────────────────────────────────────────────────────
# SAFETY: Commands that require explicit user confirmation before running
# ─────────────────────────────────────────────────────────────────────────────
DESTRUCTIVE_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bdel\s+/[sS]\b",
    r"\bformat\b",
    r"\brmdir\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bpowershell.*Remove-Item\b",
    r"\bdrop\s+table\b",
    r"\btruncate\b",
    r"\bregdel\b",
    r"\breg\s+delete\b",
    r"\btaskkill\b",
]

# Commands always blocked — no override
BLOCKED_PATTERNS = [
    r"\bdelete_system\b",
    r"\bformat_drive\b",
    r"\bsend_private_data\b",
    r"\bharm.user\b",
]

# ─────────────────────────────────────────────────────────────────────────────
# Intent Keywords — match natural language to local actions
# ─────────────────────────────────────────────────────────────────────────────
LOCAL_INTENTS = {
    # File system
    "list_dir":     [r"^(ls|dir|list files?|show files?|what'?s? in)\s", r"list the files"],
    "read_file":    [r"^(cat|read|show|open file|print file)\s", r"read the file"],
    "write_file":   [r"^(write|create file|save file|make file)\s"],
    "find_files":   [r"^(find|search files?)\s"],
    "disk_usage":   [r"(disk usage|disk space|storage|free space)"],
    # Terminal
    "run_command":  [r"^(run|exec|execute|!\s|\$\s)", r"run the command", r"execute this"],
    "run_python":   [r"^(python|py|run python)\s", r"execute python"],
    "install_pkg":  [r"^(pip install|install package)\s"],
    # System
    "system_info":  [r"(system info|my computer|my machine|what computer|cpu|ram|specs)"],
    "processes":    [r"(processes|what'?s? running|task list|running apps|top processes)"],
    "network":      [r"(network info|ip address|local ip|my ip)"],
    # Apps & UI
    "open_file":    [r"^open\s+(?!app|application)", r"launch file"],
    "open_app":     [r"^(open app|launch app|start app|open application)\s"],
    "open_url":     [r"^(open url|browse to|go to|navigate to)\s"],
    "screenshot":   [r"(take a screenshot|capture screen|screenshot)"],
    "clipboard":    [r"(clipboard|what'?s? in my clipboard|read clipboard)"],
    # GUI Automation
    "gui_task":     [r"(click|type into|press|drag|scroll|focus window|close window)", 
                     r"(open paint|open notepad|open word|open excel|open browser)"],
    "draw":         [r"(draw|sketch|paint|doodle|create art|make a (drawing|picture|image))"],
    # Project Auditor
    "audit":        [r"^(assess|audit|plan|roadmap|eta|estimate|break down|deconstruct)\s",
                     r"how long will", r"give me a plan", r"create a roadmap"],
    "project_status": [r"^(status|progress|how far|project status)"],
}


def _classify_local_intent(text: str) -> Optional[str]:
    """Return intent key if the text matches a local action, else None."""
    text_lower = text.lower().strip()
    for intent, patterns in LOCAL_INTENTS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return intent
    return None


def _is_destructive(command: str) -> bool:
    """Return True if the command matches any destructive pattern."""
    for pattern in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False


def _is_blocked(command: str) -> bool:
    """Return True if the command is unconditionally blocked."""
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Main Autonomy Bridge
# ─────────────────────────────────────────────────────────────────────────────

class BrioAutonomy:
    """
    The bridge between BRIO's language understanding and real machine control.

    Add to BrioSystem._initialize_all_systems():
        from brio_autonomy import BrioAutonomy
        self.autonomy = BrioAutonomy(system_ref=self)

    Call from BrioBrain.brio_core() or handle_command() BEFORE hitting Ollama:
        result = self.system.autonomy.handle(user_input)
        if result is not None:
            return result
    """

    ACTION_LOG_FILE = "brio_actions.log"

    def __init__(self, system_ref=None):
        self.system = system_ref
        self.local = BrioLocalAccess()
        self.agent = DesktopAgent(self.local) if HAS_AGENT else None
        self.auditor = ProjectAuditor(system_ref=system_ref)
        self._pending_confirmation: Optional[Dict] = None  # Awaiting user yes/no
        log.info(f"[Autonomy] Initialized. LocalAccess={'OK' if self.local.is_local else 'Cloud'}, "
                 f"DesktopAgent={'OK' if self.agent else 'N/A'}, Auditor=OK")

    # ─── Main Dispatch ────────────────────────────────────────────────────────

    def handle(self, text: str) -> Optional[str]:
        """
        Main entry point. Returns a response string if handled, None to fall
        through to Ollama.
        """
        # 1. Check if we're waiting for a confirmation (yes/no) response
        if self._pending_confirmation:
            return self._resolve_confirmation(text)

        # 1b. Check for project control commands (proceed/cancel/status)
        text_lower = text.lower().strip()
        if text_lower in ("proceed", "go ahead", "start execution", "approved", "do it"):
            msg = self.auditor.approve()
            if self.agent and self.auditor.active_project:
                exec_msg = self.agent.execute_project(self.auditor.active_project)
                return f"{msg}\n\n{exec_msg}"
            return msg
        if text_lower in ("cancel", "abort", "stop", "nevermind", "cancel project"):
            return self.auditor.reject()

        # 2. Classify intent
        intent = _classify_local_intent(text)
        if intent is None:
            return None  # Not a local command — let Ollama handle it

        # 3. Dispatch
        try:
            response = self._dispatch(intent, text)
            if response is not None:
                self._log_action(intent, text, response)
            return response
        except Exception as e:
            log.error(f"[Autonomy] Dispatch error for intent '{intent}': {e}")
            return f"⚠️ I encountered an error while trying to execute that: `{e}`"

    # ─── Confirmation Gate ────────────────────────────────────────────────────

    def request_confirmation(self, action_label: str, command: str) -> str:
        """Store pending confirmation and return a question to the user."""
        self._pending_confirmation = {"action": action_label, "command": command}
        return (
            f"⚠️ **Confirmation required.** I'm about to `{action_label}`, which "
            f"is a potentially destructive operation.\n\n"
            f"Command: `{command}`\n\n"
            f"Reply **yes** to proceed or **no** to cancel."
        )

    def _resolve_confirmation(self, text: str) -> str:
        """Handle a yes/no reply to a pending confirmation."""
        pending = self._pending_confirmation
        self._pending_confirmation = None
        text_lower = text.lower().strip()

        if any(w in text_lower for w in ["yes", "y", "confirm", "proceed", "do it", "go ahead"]):
            command = pending["command"]
            result = self.local.run_command(command)
            output = result.get("stdout", "") or result.get("stderr", "") or "(no output)"
            return f"✅ Done.\n```\n{output.strip()}\n```"
        else:
            return "✋ Cancelled. That operation was not executed."

    # ─── Intent Dispatcher ───────────────────────────────────────────────────

    def _dispatch(self, intent: str, text: str) -> Optional[str]:
        method = getattr(self, f"_do_{intent}", None)
        if method:
            return method(text)
        return None

    # ─── File System Actions ──────────────────────────────────────────────────

    def _do_list_dir(self, text: str) -> str:
        # Extract path from command
        path = self._extract_arg(text, ["ls", "dir", "list files", "list", "show files", "what's in"])
        entries = self.local.list_directory(path or None)
        if entries is None:
            return f"❌ Cannot access: `{path or self.local.cwd}`"
        dirs  = [e for e in entries if e.get("type") == "dir"]
        files = [e for e in entries if e.get("type") == "file"]
        lines = [f"📂 `{path or self.local.cwd}`"]
        for d in dirs[:30]:
            lines.append(f"  📁 {d['name']}/")
        for f in files[:30]:
            lines.append(f"  📄 {f['name']} ({self.local._human_size(f.get('size', 0))})")
        if len(entries) > 60:
            lines.append(f"  … and {len(entries) - 60} more items")
        return "\n".join(lines)

    def _do_read_file(self, text: str) -> str:
        path = self._extract_arg(text, ["cat", "read", "show", "open file", "print file"])
        if not path:
            return "❓ Please specify a file path. Example: `read C:\\Users\\me\\notes.txt`"
        content = self.local.read_file(path)
        if content is None:
            return f"❌ Cannot read: `{path}`"
        preview = content[:3000] + (f"\n… (truncated, {len(content)} total chars)" if len(content) > 3000 else "")
        return f"📄 `{path}`\n```\n{preview}\n```"

    def _do_find_files(self, text: str) -> str:
        pattern = self._extract_arg(text, ["find", "search files"])
        if not pattern:
            return "❓ Specify a search pattern. Example: `find *.py`"
        results = self.local.find_files(pattern)
        if not results:
            return f"🔍 No files found matching `{pattern}`."
        lines = [f"🔍 Found {len(results)} file(s) matching `{pattern}`:"]
        for r in results[:20]:
            lines.append(f"  `{r}`")
        return "\n".join(lines)

    def _do_disk_usage(self, text: str) -> str:
        info = self.local.get_disk_usage()
        if not info:
            return "❌ Could not retrieve disk usage."
        return (f"💾 **Disk Usage** (`{info['path']}`)\n"
                f"  Total: {info['total']}  |  Used: {info['used']} ({info['percent_used']}%)  |  Free: {info['free']}")

    # ─── Terminal Actions ─────────────────────────────────────────────────────

    def _do_run_command(self, text: str) -> str:
        cmd = self._extract_arg(text, ["run", "exec", "execute", "!", "$"])
        if not cmd:
            return "❓ Specify a command. Example: `run dir C:\\`"

        # Safety gate
        if _is_blocked(cmd):
            return "🚫 That command is blocked by BRIO's safety protocol."
        if _is_destructive(cmd):
            return self.request_confirmation(f"run: {cmd}", cmd)

        result = self.local.run_command(cmd)
        output = (result.get("stdout", "") + result.get("stderr", "")).strip() or "(no output)"
        exit_code = result.get("exit_code", "?")
        status = "✅" if exit_code == 0 else "❌"
        return f"{status} `{cmd}` (exit {exit_code})\n```\n{output}\n```"

    def _do_run_python(self, text: str) -> str:
        code = self._extract_arg(text, ["python", "py", "run python"])
        if not code:
            return "❓ Specify Python code to run. Example: `python print('hello')`"
        result = self.local.run_python(code)
        output = (result.get("stdout", "") + result.get("stderr", "")).strip() or "(no output)"
        return f"🐍 Python output:\n```\n{output}\n```"

    def _do_install_pkg(self, text: str) -> str:
        pkg = self._extract_arg(text, ["pip install", "install package"])
        if not pkg:
            return "❓ Specify a package. Example: `pip install requests`"
        result = self.local.install_package(pkg)
        output = (result.get("stdout", "") + result.get("stderr", "")).strip()
        return f"📦 Installing `{pkg}`…\n```\n{output[:2000]}\n```"

    # ─── System Info Actions ──────────────────────────────────────────────────

    def _do_system_info(self, text: str) -> str:
        info = self.local.get_system_info()
        lines = [f"🖥️ **{info.get('hostname', 'Your Machine')}**"]
        lines.append(f"  OS: {info.get('os')} {info.get('os_release', '')}")
        lines.append(f"  CPU: {info.get('processor', 'Unknown')} ({info.get('cpu_count', '?')} cores)")
        if info.get("ram_total"):
            lines.append(f"  RAM: {info['ram_total']}")
        if info.get("disk"):
            d = info["disk"]
            lines.append(f"  Disk: {d.get('used','?')} / {d.get('total','?')} ({d.get('percent_used','?')}% used)")
        lines.append(f"  Python: {info.get('python_version', '?')}")
        lines.append(f"  User: {info.get('username', '?')}")
        return "\n".join(lines)

    def _do_processes(self, text: str) -> str:
        procs = self.local.get_running_processes(20)
        if not procs:
            return "Could not retrieve process list."
        lines = ["⚙️ **Running Processes:**"]
        for p in procs[:15]:
            name = p.get("name", p.get("command", "?"))[:50]
            pid  = p.get("pid", "?")
            mem  = p.get("memory", p.get("mem", ""))
            lines.append(f"  {name} (PID {pid}) {mem}")
        return "\n".join(lines)

    def _do_network(self, text: str) -> str:
        net = self.local.get_network_info()
        ips = net.get("local_ips", [])
        if not ips:
            return "🌐 Could not retrieve network info."
        return "🌐 **Network:**\n" + "\n".join(f"  IP: {ip}" for ip in ips)

    # ─── App & File Opening ───────────────────────────────────────────────────

    def _do_open_file(self, text: str) -> str:
        path = self._extract_arg(text, ["open", "launch file"])
        if not path:
            return "❓ Specify a file path."
        ok = self.local.open_file(path)
        return f"📂 Opened `{path}`." if ok else f"❌ Could not open `{path}`."

    def _do_open_app(self, text: str) -> str:
        app = self._extract_arg(text, ["open app", "launch app", "start app", "open application"])
        if not app:
            return "❓ Specify an application name."
        ok = self.local.open_application(app)
        return f"🚀 Launching `{app}`…" if ok else f"❌ Could not launch `{app}`."

    def _do_open_url(self, text: str) -> str:
        url = self._extract_arg(text, ["open url", "browse to", "go to", "navigate to"])
        if not url:
            return "❓ Specify a URL."
        ok = self.local.open_url(url)
        return f"🌐 Opening {url} in your browser…" if ok else f"❌ Could not open URL."

    def _do_screenshot(self, text: str) -> str:
        path = self.local.take_screenshot()
        return f"📸 Screenshot saved: `{path}`" if path else "❌ Could not take screenshot."

    def _do_clipboard(self, text: str) -> str:
        content = self.local.get_clipboard()
        if not content:
            return "📋 Clipboard is empty or inaccessible."
        preview = content[:500] + ("…" if len(content) > 500 else "")
        return f"📋 **Clipboard contents:**\n```\n{preview}\n```"

    # ─── GUI Automation Actions ───────────────────────────────────────────────

    def _do_gui_task(self, text: str) -> str:
        if not self.agent:
            return "🖱️ GUI automation is not available (pyautogui not installed)."
        result = self.agent.handle_command(text)
        return result or "🖱️ GUI task queued."

    def _do_draw(self, text: str) -> str:
        if not self.agent:
            return "🎨 Drawing requires GUI automation (pyautogui not installed)."
        result = self.agent.handle_command(text)
        return result or "🎨 Drawing task queued."

    # ─── Project Auditor Actions ──────────────────────────────────────────────

    def _do_audit(self, text: str) -> str:
        """Break down a complex task into a roadmap with ETA."""
        task = self._extract_arg(text, [
            "assess", "audit", "plan", "roadmap", "eta", "estimate",
            "break down", "deconstruct", "give me a plan", "create a roadmap",
        ])
        if not task:
            return (
                "❓ Tell me what to assess. Examples:\n"
                "  • `assess: build a low-poly house in Blender`\n"
                "  • `plan: design a logo for my company`\n"
                "  • `roadmap: create a 3D landscape`"
            )
        return self.auditor.audit(task)

    def _do_project_status(self, text: str) -> str:
        """Return the current project's progress."""
        return self.auditor.get_status()

    # ─── Utilities ────────────────────────────────────────────────────────────

    def _extract_arg(self, text: str, prefixes: List[str]) -> str:
        """Strip a command prefix and return the remaining argument."""
        text_lower = text.lower().strip()
        for prefix in sorted(prefixes, key=len, reverse=True):  # Longest match first
            if text_lower.startswith(prefix.lower()):
                return text[len(prefix):].strip()
        # Fallback: return everything after first word
        parts = text.split(None, 1)
        return parts[1].strip() if len(parts) > 1 else ""

    def _log_action(self, intent: str, command: str, response: str):
        """Append action to persistent log file."""
        try:
            entry = {
                "ts": datetime.now().isoformat(),
                "intent": intent,
                "command": command[:200],
                "response_len": len(response),
            }
            with open(self.ACTION_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            log.warning(f"[Autonomy] Could not write action log: {e}")

    def get_capabilities(self) -> str:
        """Return a human-readable list of what BRIO can do locally."""
        caps = [
            "📁 Browse, read, write, find, and move files",
            "💻 Run any shell command (with safety checks)",
            "🐍 Execute Python code",
            "📦 Install Python packages via pip",
            "🖥️ Get system info, CPU, RAM, disk, network",
            "⚙️ List running processes",
            "🚀 Launch applications and open files",
            "🌐 Open URLs in your browser",
            "📸 Take screenshots",
            "📋 Read and write your clipboard",
            "📋 Assess complex tasks with ETA & roadmaps",
            "📊 Track project progress step-by-step",
        ]
        if self.agent:
            caps += [
                "🖱️ Control your mouse and keyboard",
                "👁️ Read text from your screen (OCR)",
                "🎨 Draw shapes and artwork in Paint/Canva",
                "🪟 Find, focus, and close windows",
                "🧊 Work inside Blender (3D modeling)",
            ]
        return "**BRIO Local Capabilities:**\n" + "\n".join(caps)
