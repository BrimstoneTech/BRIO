"""
BRIO Local Machine Access Module
==================================
When BRIO runs on localhost, it has full access to the user's machine:
- File system browsing, reading, writing
- Terminal command execution
- System information gathering
- Application launching
- Clipboard access
- Screenshot capture
- Process management

⚠️ SAFETY: Only enabled when running on localhost (not on HF Spaces).
All actions are logged and the user is informed.
"""

import os
import sys
import json
import platform
import subprocess
import logging
import shutil
import glob as glob_module
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

log = logging.getLogger("brio.local_access")


class BrioLocalAccess:
    """Full local machine access for BRIO when running on localhost."""

    def __init__(self):
        self.is_local = self._detect_local()
        self.home_dir = str(Path.home())
        self.os_type = platform.system()  # Windows, Linux, Darwin
        self.action_log: List[Dict] = []
        self.cwd = self.home_dir  # Current working directory

        if self.is_local:
            log.info(f"[LocalAccess] Enabled — {self.os_type} detected, home: {self.home_dir}")
        else:
            log.info("[LocalAccess] Disabled — running in cloud mode")

    def _detect_local(self) -> bool:
        """Detect if running on localhost vs cloud (HF Spaces)."""
        # HF Spaces sets SPACE_ID
        if os.environ.get("SPACE_ID"):
            return False
        # HF Spaces Docker also sets these
        if os.environ.get("SYSTEM") == "spaces":
            return False
        # Check for typical cloud indicators
        if os.path.exists("/.dockerenv") and os.environ.get("SPACE_ID"):
            return False
        return True

    def _log_action(self, action: str, details: str, success: bool):
        """Log all actions for transparency."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "success": success,
        }
        self.action_log.append(entry)
        if len(self.action_log) > 500:
            self.action_log = self.action_log[-250:]
        level = log.info if success else log.warning
        level(f"[LocalAccess] {action}: {details} ({'ok' if success else 'failed'})")

    def _require_local(self) -> bool:
        """Check if local access is available."""
        if not self.is_local:
            log.warning("[LocalAccess] Blocked — not running locally")
            return False
        return True

    # ═══════════════════════════════════════════════════════════════
    #  📁 FILE SYSTEM
    # ═══════════════════════════════════════════════════════════════

    def list_directory(self, path: str = None) -> Optional[List[Dict]]:
        """List contents of a directory."""
        if not self._require_local():
            return None
        path = path or self.cwd
        path = os.path.expanduser(path)
        try:
            entries = []
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)
                try:
                    stat = os.stat(full)
                    entries.append({
                        "name": name,
                        "type": "dir" if os.path.isdir(full) else "file",
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "readable": os.access(full, os.R_OK),
                        "writable": os.access(full, os.W_OK),
                    })
                except (PermissionError, OSError):
                    entries.append({"name": name, "type": "unknown", "error": "permission denied"})
            self._log_action("list_dir", path, True)
            return entries
        except Exception as e:
            self._log_action("list_dir", f"{path} — {e}", False)
            return None

    def read_file(self, path: str, max_bytes: int = 100000) -> Optional[str]:
        """Read a text file."""
        if not self._require_local():
            return None
        path = os.path.expanduser(path)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_bytes)
            self._log_action("read_file", f"{path} ({len(content)} chars)", True)
            return content
        except Exception as e:
            self._log_action("read_file", f"{path} — {e}", False)
            return None

    def write_file(self, path: str, content: str) -> bool:
        """Write content to a file."""
        if not self._require_local():
            return False
        path = os.path.expanduser(path)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self._log_action("write_file", f"{path} ({len(content)} chars)", True)
            return True
        except Exception as e:
            self._log_action("write_file", f"{path} — {e}", False)
            return False

    def append_file(self, path: str, content: str) -> bool:
        """Append content to a file."""
        if not self._require_local():
            return False
        path = os.path.expanduser(path)
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
            self._log_action("append_file", f"{path} ({len(content)} chars)", True)
            return True
        except Exception as e:
            self._log_action("append_file", f"{path} — {e}", False)
            return False

    def create_directory(self, path: str) -> bool:
        """Create a directory (and parents)."""
        if not self._require_local():
            return False
        path = os.path.expanduser(path)
        try:
            os.makedirs(path, exist_ok=True)
            self._log_action("create_dir", path, True)
            return True
        except Exception as e:
            self._log_action("create_dir", f"{path} — {e}", False)
            return False

    def delete_file(self, path: str) -> bool:
        """Delete a file."""
        if not self._require_local():
            return False
        path = os.path.expanduser(path)
        try:
            os.remove(path)
            self._log_action("delete_file", path, True)
            return True
        except Exception as e:
            self._log_action("delete_file", f"{path} — {e}", False)
            return False

    def move_file(self, src: str, dst: str) -> bool:
        """Move/rename a file or directory."""
        if not self._require_local():
            return False
        src, dst = os.path.expanduser(src), os.path.expanduser(dst)
        try:
            shutil.move(src, dst)
            self._log_action("move", f"{src} → {dst}", True)
            return True
        except Exception as e:
            self._log_action("move", f"{src} → {dst} — {e}", False)
            return False

    def copy_file(self, src: str, dst: str) -> bool:
        """Copy a file."""
        if not self._require_local():
            return False
        src, dst = os.path.expanduser(src), os.path.expanduser(dst)
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            self._log_action("copy", f"{src} → {dst}", True)
            return True
        except Exception as e:
            self._log_action("copy", f"{src} → {dst} — {e}", False)
            return False

    def find_files(self, pattern: str, path: str = None) -> List[str]:
        """Find files matching a glob pattern."""
        if not self._require_local():
            return []
        path = os.path.expanduser(path or self.cwd)
        try:
            results = glob_module.glob(os.path.join(path, "**", pattern), recursive=True)
            self._log_action("find_files", f"{pattern} in {path} ({len(results)} found)", True)
            return results[:100]  # Cap at 100 results
        except Exception as e:
            self._log_action("find_files", f"{pattern} — {e}", False)
            return []

    def get_file_info(self, path: str) -> Optional[Dict]:
        """Get detailed file information."""
        if not self._require_local():
            return None
        path = os.path.expanduser(path)
        try:
            stat = os.stat(path)
            return {
                "path": path,
                "name": os.path.basename(path),
                "type": "directory" if os.path.isdir(path) else "file",
                "size_bytes": stat.st_size,
                "size_human": self._human_size(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
                "readable": os.access(path, os.R_OK),
                "writable": os.access(path, os.W_OK),
                "executable": os.access(path, os.X_OK),
            }
        except Exception as e:
            return None

    def change_directory(self, path: str) -> bool:
        """Change BRIO's current working directory."""
        if not self._require_local():
            return False
        path = os.path.expanduser(path)
        if os.path.isdir(path):
            self.cwd = os.path.abspath(path)
            self._log_action("cd", self.cwd, True)
            return True
        return False

    def get_disk_usage(self, path: str = None) -> Optional[Dict]:
        """Get disk usage for a path."""
        if not self._require_local():
            return None
        path = path or self.home_dir
        try:
            usage = shutil.disk_usage(path)
            return {
                "path": path,
                "total": self._human_size(usage.total),
                "used": self._human_size(usage.used),
                "free": self._human_size(usage.free),
                "percent_used": round(usage.used / usage.total * 100, 1),
            }
        except Exception:
            return None

    # ═══════════════════════════════════════════════════════════════
    #  💻 TERMINAL / COMMAND EXECUTION
    # ═══════════════════════════════════════════════════════════════

    def run_command(self, command: str, timeout: int = 30, cwd: str = None) -> Dict:
        """Execute a shell command and return output."""
        if not self._require_local():
            return {"error": "Not running locally", "exit_code": -1}
        cwd = cwd or self.cwd
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env={**os.environ, "LANG": "en_US.UTF-8"}
            )
            output = {
                "command": command,
                "stdout": result.stdout[-5000:] if result.stdout else "",  # Cap output
                "stderr": result.stderr[-2000:] if result.stderr else "",
                "exit_code": result.returncode,
                "cwd": cwd,
            }
            self._log_action("run_command", f"{command} (exit {result.returncode})", result.returncode == 0)
            return output
        except subprocess.TimeoutExpired:
            self._log_action("run_command", f"{command} (TIMEOUT after {timeout}s)", False)
            return {"command": command, "error": f"Timed out after {timeout}s", "exit_code": -1}
        except Exception as e:
            self._log_action("run_command", f"{command} — {e}", False)
            return {"command": command, "error": str(e), "exit_code": -1}

    def run_python(self, code: str, timeout: int = 30) -> Dict:
        """Execute Python code and return output."""
        if not self._require_local():
            return {"error": "Not running locally"}
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=timeout, cwd=self.cwd
            )
            self._log_action("run_python", f"({len(code)} chars, exit {result.returncode})", result.returncode == 0)
            return {
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:],
                "exit_code": result.returncode,
            }
        except Exception as e:
            return {"error": str(e)}

    def install_package(self, package: str) -> Dict:
        """Install a Python package via pip."""
        return self.run_command(f"{sys.executable} -m pip install {package}", timeout=120)

    # ═══════════════════════════════════════════════════════════════
    #  🖥️ SYSTEM INFORMATION
    # ═══════════════════════════════════════════════════════════════

    def get_system_info(self) -> Dict:
        """Comprehensive system information."""
        if not self._require_local():
            return {"error": "Not running locally"}
        info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "home_directory": self.home_dir,
            "current_directory": self.cwd,
            "username": os.environ.get("USER") or os.environ.get("USERNAME", "unknown"),
        }

        # CPU count
        try:
            info["cpu_count"] = os.cpu_count()
        except Exception:
            pass

        # Memory (cross-platform)
        try:
            if self.os_type == "Linux":
                with open("/proc/meminfo") as f:
                    meminfo = f.read()
                for line in meminfo.split("\n"):
                    if "MemTotal" in line:
                        kb = int(line.split()[1])
                        info["ram_total"] = self._human_size(kb * 1024)
                    elif "MemAvailable" in line:
                        kb = int(line.split()[1])
                        info["ram_available"] = self._human_size(kb * 1024)
            elif self.os_type == "Darwin":
                result = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
                if result.returncode == 0:
                    info["ram_total"] = self._human_size(int(result.stdout.strip()))
            elif self.os_type == "Windows":
                result = subprocess.run(
                    ["wmic", "OS", "get", "TotalVisibleMemorySize"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    if len(lines) > 1:
                        kb = int(lines[1].strip())
                        info["ram_total"] = self._human_size(kb * 1024)
        except Exception:
            pass

        # Disk
        disk = self.get_disk_usage()
        if disk:
            info["disk"] = disk

        return info

    def get_running_processes(self, limit: int = 20) -> List[Dict]:
        """List running processes."""
        if not self._require_local():
            return []
        try:
            if self.os_type == "Windows":
                result = subprocess.run(
                    ["tasklist", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True, timeout=10
                )
                procs = []
                for line in result.stdout.strip().split("\n")[:limit]:
                    parts = line.strip('"').split('","')
                    if len(parts) >= 2:
                        procs.append({"name": parts[0], "pid": parts[1], "memory": parts[-1] if len(parts) > 4 else ""})
                return procs
            else:
                result = subprocess.run(
                    ["ps", "aux", "--sort=-pcpu"],
                    capture_output=True, text=True, timeout=10
                )
                procs = []
                for line in result.stdout.strip().split("\n")[1:limit + 1]:
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        procs.append({
                            "user": parts[0], "pid": parts[1],
                            "cpu": parts[2], "mem": parts[3],
                            "command": parts[10][:80],
                        })
                return procs
        except Exception:
            return []

    def get_network_info(self) -> Dict:
        """Basic network information."""
        if not self._require_local():
            return {}
        result = {}
        try:
            if self.os_type in ("Linux", "Darwin"):
                out = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=5)
                if out.returncode == 0:
                    result["local_ips"] = out.stdout.strip().split()
            elif self.os_type == "Windows":
                out = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=5)
                if out.returncode == 0:
                    import re
                    ips = re.findall(r"IPv4.*?:\s*([\d.]+)", out.stdout)
                    result["local_ips"] = ips
        except Exception:
            pass
        return result

    # ═══════════════════════════════════════════════════════════════
    #  🚀 APPLICATION LAUNCHING
    # ═══════════════════════════════════════════════════════════════

    def open_file(self, path: str) -> bool:
        """Open a file with the default application."""
        if not self._require_local():
            return False
        path = os.path.expanduser(path)
        try:
            if self.os_type == "Windows":
                os.startfile(path)
            elif self.os_type == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            self._log_action("open_file", path, True)
            return True
        except Exception as e:
            self._log_action("open_file", f"{path} — {e}", False)
            return False

    def open_url(self, url: str) -> bool:
        """Open a URL in the default browser."""
        if not self._require_local():
            return False
        try:
            import webbrowser
            webbrowser.open(url)
            self._log_action("open_url", url, True)
            return True
        except Exception as e:
            self._log_action("open_url", f"{url} — {e}", False)
            return False

    def open_application(self, app_name: str) -> bool:
        """Launch an application by name."""
        if not self._require_local():
            return False
        try:
            if self.os_type == "Windows":
                subprocess.Popen(["start", app_name], shell=True)
            elif self.os_type == "Darwin":
                subprocess.Popen(["open", "-a", app_name])
            else:
                subprocess.Popen([app_name], start_new_session=True)
            self._log_action("open_app", app_name, True)
            return True
        except Exception as e:
            self._log_action("open_app", f"{app_name} — {e}", False)
            return False

    # ═══════════════════════════════════════════════════════════════
    #  📋 CLIPBOARD
    # ═══════════════════════════════════════════════════════════════

    def get_clipboard(self) -> Optional[str]:
        """Read clipboard contents."""
        if not self._require_local():
            return None
        try:
            if self.os_type == "Windows":
                result = subprocess.run(
                    ["powershell", "-command", "Get-Clipboard"],
                    capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip() if result.returncode == 0 else None
            elif self.os_type == "Darwin":
                result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
                return result.stdout if result.returncode == 0 else None
            else:
                result = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                                        capture_output=True, text=True, timeout=5)
                return result.stdout if result.returncode == 0 else None
        except Exception:
            return None

    def set_clipboard(self, text: str) -> bool:
        """Set clipboard contents."""
        if not self._require_local():
            return False
        try:
            if self.os_type == "Windows":
                subprocess.run(
                    ["powershell", "-command", f"Set-Clipboard -Value '{text}'"],
                    timeout=5
                )
            elif self.os_type == "Darwin":
                subprocess.run(["pbcopy"], input=text.encode(), timeout=5)
            else:
                subprocess.run(["xclip", "-selection", "clipboard"],
                               input=text.encode(), timeout=5)
            self._log_action("set_clipboard", f"({len(text)} chars)", True)
            return True
        except Exception as e:
            self._log_action("set_clipboard", str(e), False)
            return False

    # ═══════════════════════════════════════════════════════════════
    #  📸 SCREENSHOT
    # ═══════════════════════════════════════════════════════════════

    def take_screenshot(self, output_path: str = None) -> Optional[str]:
        """Take a screenshot and save to file."""
        if not self._require_local():
            return None
        output_path = output_path or os.path.join(self.home_dir, f"brio_screenshot_{int(datetime.now().timestamp())}.png")
        try:
            if self.os_type == "Windows":
                # Use PowerShell to take screenshot
                ps_script = f"""
                Add-Type -AssemblyName System.Windows.Forms
                $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
                $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
                $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
                $bitmap.Save('{output_path}')
                """
                subprocess.run(["powershell", "-command", ps_script], timeout=10)
            elif self.os_type == "Darwin":
                subprocess.run(["screencapture", "-x", output_path], timeout=10)
            else:
                # Try scrot, gnome-screenshot, or import
                for cmd in [
                    ["scrot", output_path],
                    ["gnome-screenshot", "-f", output_path],
                    ["import", "-window", "root", output_path],
                ]:
                    try:
                        result = subprocess.run(cmd, timeout=10, capture_output=True)
                        if result.returncode == 0:
                            break
                    except FileNotFoundError:
                        continue

            if os.path.exists(output_path):
                self._log_action("screenshot", output_path, True)
                return output_path
            return None
        except Exception as e:
            self._log_action("screenshot", str(e), False)
            return None

    # ═══════════════════════════════════════════════════════════════
    #  🔧 UTILITIES
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """Convert bytes to human-readable size."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if abs(size_bytes) < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def get_action_log(self, limit: int = 20) -> List[Dict]:
        """Get recent action log entries."""
        return self.action_log[-limit:]

    def handle_command(self, text: str) -> Optional[str]:
        """
        Parse natural language or command-style requests for local access.
        Returns a response string if this module can handle it, None otherwise.
        """
        if not self.is_local:
            return None

        text_lower = text.lower().strip()

        # System info
        if any(p in text_lower for p in ["system info", "my computer", "my machine", "what computer", "specs"]):
            info = self.get_system_info()
            lines = [f"🖥️ *{info.get('hostname', 'Your Machine')}*"]
            lines.append(f"  OS: {info.get('os')} {info.get('os_release', '')}")
            lines.append(f"  CPU: {info.get('processor', 'Unknown')} ({info.get('cpu_count', '?')} cores)")
            if info.get("ram_total"):
                lines.append(f"  RAM: {info['ram_total']}" + (f" ({info.get('ram_available', '?')} free)" if info.get('ram_available') else ""))
            if info.get("disk"):
                d = info["disk"]
                lines.append(f"  Disk: {d.get('used', '?')} / {d.get('total', '?')} ({d.get('percent_used', '?')}% used)")
            lines.append(f"  Python: {info.get('python_version', '?')}")
            lines.append(f"  User: {info.get('username', '?')}")
            return "\n".join(lines)

        # List directory
        if text_lower.startswith(("ls ", "dir ", "list ")):
            path = text[text.index(" "):].strip() or self.cwd
            entries = self.list_directory(path)
            if entries is None:
                return f"❌ Cannot access: {path}"
            dirs = [e for e in entries if e["type"] == "dir"]
            files = [e for e in entries if e["type"] == "file"]
            lines = [f"📂 {path}"]
            for d in dirs[:30]:
                lines.append(f"  📁 {d['name']}/")
            for f in files[:30]:
                lines.append(f"  📄 {f['name']} ({self._human_size(f.get('size', 0))})")
            if len(entries) > 60:
                lines.append(f"  ... and {len(entries) - 60} more")
            return "\n".join(lines)

        # Read file
        if text_lower.startswith(("cat ", "read ", "show ", "open file ")):
            path = text[text.index(" "):].strip()
            content = self.read_file(path)
            if content is None:
                return f"❌ Cannot read: {path}"
            if len(content) > 3000:
                content = content[:3000] + f"\n... (truncated, {len(content)} total chars)"
            return f"📄 *{os.path.basename(path)}*\n```\n{content}\n```"

        # Run command
        if text_lower.startswith(("run ", "exec ", "execute ", "$", "! ")):
            # Extract command
            for prefix in ["run ", "exec ", "execute ", "$ ", "! "]:
                if text_lower.startswith(prefix):
                    cmd = text[len(prefix):].strip()
                    break
            result = self.run_command(cmd)
            output = result.get("stdout", "") + result.get("stderr", "")
            if not output.strip():
                output = "(no output)"
            return f"💻 `{cmd}` (exit {result.get('exit_code', '?')})\n```\n{output.strip()}\n```"

        # Process list
        if any(p in text_lower for p in ["processes", "what's running", "task list", "running apps"]):
            procs = self.get_running_processes()
            if not procs:
                return "Could not get process list."
            lines = ["⚙️ *Running Processes (top by CPU):*"]
            for p in procs[:15]:
                if "cpu" in p:
                    lines.append(f"  {p.get('command', p.get('name', '?'))[:50]}  CPU:{p['cpu']}% MEM:{p['mem']}%")
                else:
                    lines.append(f"  {p.get('name', '?')} (PID {p.get('pid', '?')})")
            return "\n".join(lines)

        # CD
        if text_lower.startswith("cd "):
            path = text[3:].strip()
            if self.change_directory(path):
                return f"📂 Now in: {self.cwd}"
            return f"❌ Directory not found: {path}"

        # Find files
        if text_lower.startswith(("find ", "search files ")):
            pattern = text[text.index(" "):].strip()
            results = self.find_files(pattern)
            if not results:
                return f"No files found matching: {pattern}"
            lines = [f"🔍 Found {len(results)} files matching '{pattern}':"]
            for r in results[:20]:
                lines.append(f"  {r}")
            return "\n".join(lines)

        # Clipboard
        if "clipboard" in text_lower and any(w in text_lower for w in ["read", "get", "show", "what"]):
            content = self.get_clipboard()
            return f"📋 Clipboard:\n{content}" if content else "📋 Clipboard is empty or inaccessible."

        # Screenshot
        if "screenshot" in text_lower:
            path = self.take_screenshot()
            return f"📸 Screenshot saved: {path}" if path else "❌ Could not take screenshot."

        return None

    def get_status(self) -> Dict:
        """Module status."""
        return {
            "enabled": self.is_local,
            "os": self.os_type if self.is_local else "cloud",
            "home": self.home_dir if self.is_local else None,
            "cwd": self.cwd if self.is_local else None,
            "actions_logged": len(self.action_log),
            "capabilities": [
                "file_system", "terminal", "system_info",
                "process_management", "clipboard", "screenshot",
                "app_launching", "python_execution"
            ] if self.is_local else [],
        }
