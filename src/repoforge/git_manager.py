"""Safe Git baseline helpers for RepoForge.

The checkpoint operation is intentionally read-only: it records a clean HEAD
and never stages or commits user files.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("RepoForge.GitManager")


class GitManager:
    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path).resolve()

    def run_git(self, *args: str) -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.error("Git command failed: %s", type(exc).__name__)
            return {"success": False, "error": str(exc)}

    def is_git_repo(self) -> bool:
        return self.run_git("rev-parse", "--is-inside-work-tree")["success"]

    def save_state(self, message: str = "RepoForge baseline checkpoint") -> dict[str, Any]:
        """Record a clean HEAD without staging or committing any working files."""
        del message  # Kept for call compatibility with the previous implementation.
        if not self.is_git_repo():
            return {"success": False, "message": "Not a Git repository"}

        status = self.run_git("status", "--porcelain", "--untracked-files=all")
        if not status["success"]:
            return {"success": False, "message": "Could not verify working-tree state"}
        if status.get("output"):
            return {
                "success": False,
                "message": "Working tree is dirty; refusing to stage or checkpoint user changes",
            }

        head = self.run_git("rev-parse", "HEAD")
        if not head["success"] or not head.get("output"):
            return {"success": False, "message": "Could not record current HEAD"}
        logger.info("Recorded clean HEAD baseline: %s", head["output"])
        return {
            "success": True,
            "message": "Clean HEAD baseline recorded; no files staged or committed",
            "checkpoint": head["output"],
        }

    def rollback(self) -> dict[str, Any]:
        """Disable implicit destructive rollback; recovery must be path-scoped."""
        logger.warning("Automatic hard reset is disabled by the engineering constitution.")
        return {
            "success": False,
            "error": "automatic rollback disabled; inspect and revert only approved paths",
        }
