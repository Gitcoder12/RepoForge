"""
Project Registry – persistent storage of project metadata.
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

DEFAULT_REGISTRY = os.path.expanduser("~/.repoforge/projects.json")


class ProjectRegistry:
    def __init__(self, registry_path: Optional[str] = None):
        self.registry_path = registry_path or DEFAULT_REGISTRY
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)

    def load_all(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.registry_path):
            return []
        try:
            with open(self.registry_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def save_all(self, projects: List[Dict[str, Any]]):
        with open(self.registry_path, "w") as f:
            json.dump(projects, f, indent=2)