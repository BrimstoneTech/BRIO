import subprocess
import shutil
import os

class KimiBridge:
    """
    Bridge to interact with Kimi-CLI for advanced intelligence.
    """
    def __init__(self, kimi_path=r"C:\Users\Administrator\.local\bin\kimi-cli.exe"):
        self.kimi_path = kimi_path
        self.available = os.path.exists(self.kimi_path)

    def ask_kimi(self, query: str) -> str:
        """
        Sends a query to Kimi-CLI via pipes and returns the response.
        """
        if not self.available:
            return "Kimi-CLI is not available or not properly installed."
            
        try:
            # We use --quiet to get just the final response
            # and pipe the query into stdin as required by the CLI docs.
            command = [self.kimi_path, "--quiet"]
            
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(input=query, timeout=45)
            
            if process.returncode == 0:
                out = stdout.strip()
                if "LLM not set" in out:
                    return "ERROR: Kimi is not configured. I need the Master to log in and set up an LLM connection."
                return out
            else:
                err = stderr.strip()
                if "LLM not set" in err or "LLM not set" in stdout:
                    return "ERROR: Kimi is not configured. I need the Master to log in and set up an LLM connection."
                if "network" in err.lower() or "connection" in err.lower():
                    return "I'm sorry, I'm currently offline and cannot reach Kimi's intelligence."
                return f"Kimi encountered an error: {err}"
        except subprocess.TimeoutExpired:
            return "Kimi is taking too long to respond."
        except Exception as e:
            return f"Failed to connect to Kimi: {str(e)}"

if __name__ == "__main__":
    bridge = KimiBridge()
    print(f"Kimi Available: {bridge.available}")
    if bridge.available:
        print(bridge.ask_kimi("Tell me a short joke about AI."))
