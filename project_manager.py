"""
Project Manager – manage multiple repositories for RepoForge Engine.
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from .project_registry import ProjectRegistry


class ProjectManager:
    """Manages a list of repositories and coordinates runs across them."""

    def __init__(self, registry_path: Optional[str] = None):
        self.registry = ProjectRegistry(registry_path)
        self.projects = self.registry.load_all()

    def add_project(self, path: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Add a new project to the registry."""
        path = str(Path(path).resolve())
        if not name:
            name = Path(path).name
        project = {
            "path": path,
            "name": name,
            "last_analysis": None,
            "quality_score": 0,
            "grade": "N/A",
            "issues": 0,
            "last_action": None,
        }
        self.projects.append(project)
        self.registry.save_all(self.projects)
        return project

    def remove_project(self, path: str) -> bool:
        """Remove a project by path."""
        path = str(Path(path).resolve())
        original_len = len(self.projects)
        self.projects = [p for p in self.projects if p["path"] != path]
        if len(self.projects) < original_len:
            self.registry.save_all(self.projects)
            return True
        return False

    def list_projects(self) -> List[Dict[str, Any]]:
        """Return all registered projects."""
        return self.projects

    def get_project(self, path: str) -> Optional[Dict[str, Any]]:
        """Get a project by path."""
        path = str(Path(path).resolve())
        for p in self.projects:
            if p["path"] == path:
                return p
        return None

    def update_project(self, path: str, updates: Dict[str, Any]) -> bool:
        """Update a project's metadata."""
        project = self.get_project(path)
        if not project:
            return False
        project.update(updates)
        self.registry.save_all(self.projects)
        return True

    def run_all(self, prompt: str, approve: bool = False) -> List[Dict[str, Any]]:
        """
        Run RepoForge on all registered projects.
        Returns a list of results per project.
        """
        from repoforge.workflow_engine import WorkflowEngine

        results = []
        for project in self.projects:
            path = project["path"]
            print(f"\n🔨 Running on: {project['name']} ({path})")
            engine = WorkflowEngine(path)
            result = engine.execute(prompt)

            # Update project metadata
            score = result.get("quality_score", {}).get("score", 0)
            grade = result.get("quality_score", {}).get("grade", "N/A")
            v4 = result.get("stages", {}).get("v4_analysis", {})
            issues = len(v4.get("raw_issues", []))
            v5 = result.get("stages", {}).get("v5_agents", {})
            consensus = v5.get("consensus", {})
            selected_actions = consensus.get("selected_actions", [])
            last_action = selected_actions[0].get("action") if selected_actions else None

            self.update_project(path, {
                "last_analysis": result.get("stages", {}).get("scan", {}).get("timestamp"),
                "quality_score": score,
                "grade": grade,
                "issues": issues,
                "last_action": last_action,
            })

            results.append({
                "project": project,
                "result": result,
            })

        return results