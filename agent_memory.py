"""
Agent Memory – stores previous suggestions to avoid repetition.
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

DEFAULT_MEMORY = os.path.expanduser("~/.repoforge/memory.json")


class AgentMemory:
    def __init__(self, memory_path: Optional[str] = None):
        self.memory_path = memory_path or DEFAULT_MEMORY
        self._ensure_dir()
        self.memory = self._load()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)

    def _load(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.memory_path):
            return []
        try:
            with open(self.memory_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def save(self):
        with open(self.memory_path, "w") as f:
            json.dump(self.memory, f, indent=2)

    def remember(self, repo_path: str, suggestion: str, success: bool):
        """Store a suggestion with outcome."""
        entry = {
            "repo": repo_path,
            "suggestion": suggestion,
            "success": success,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
        self.memory.append(entry)
        self.save()

    def get_history(self, repo_path: str, limit: int = 10) -> List[str]:
        """Get past suggestions for a repo to avoid repeats."""
        history = [entry["suggestion"] for entry in self.memory if entry["repo"] == repo_path]
        return history[-limit:]

    def has_seen(self, repo_path: str, suggestion: str) -> bool:
        """Check if a suggestion was already made for this repo."""
        return any(entry["suggestion"] == suggestion for entry in self.memory if entry["repo"] == repo_path)