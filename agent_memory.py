import json
import os
import threading
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("RepoForge.Memory")
DEFAULT_MEMORY = os.path.expanduser("~/.repoforge/memory.json")

class AgentMemory:
    def __init__(self, memory_path: Optional[str] = None):
        self.memory_path = memory_path or DEFAULT_MEMORY
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        self.memory = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.memory_path): return []
        try:
            with open(self.memory_path, "r") as f: return json.load(f)
        except (json.JSONDecodeError, IOError): return []

    def save(self):
        with self._lock:
            with open(self.memory_path, "w") as f:
                json.dump(self.memory, f, indent=2)

    def remember(self, repo_path: str, suggestion: str, success: bool):
        entry = {
            "repo": repo_path, "suggestion": suggestion, "success": success,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
        with self._lock:
            self.memory.append(entry)
        self.save()

    def get_history(self, repo_path: str, limit: int = 10) -> List[str]:
        with self._lock:
            history = [e["suggestion"] for e in self.memory if e["repo"] == repo_path]
        return history[-limit:]

    def has_seen(self, repo_path: str, suggestion: str) -> bool:
        with self._lock:
            return any(e["suggestion"] == suggestion for e in self.memory if e["repo"] == repo_path)
