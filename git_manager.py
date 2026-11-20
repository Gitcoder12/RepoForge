from pathlib import Path
import subprocess
from typing import Dict, Any
import logging

logger = logging.getLogger("RepoForge.GitManager")


class GitManager:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()

    def run_git(self, *args) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["git", *args], cwd=self.repo_path,
                capture_output=True, text=True, timeout=60
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
            }
        except subprocess.TimeoutExpired:
            logger.error("Git command timed out")
            return {"success": False, "error": "Git command timed out"}
        except Exception as exc:
            logger.error("Git error: %s", exc)
            return {"success": False, "error": str(exc)}

    def is_git_repo(self):
        return self.run_git("rev-parse", "--is-inside-work-tree")["success"]

    def save_state(self, message: str = "RepoForge baseline checkpoint"):
        """Record a clean HEAD as the recovery baseline without staging user files.

        This deliberately does not run git add or create a commit. Existing
        user changes are never swept into an automated checkpoint.
        """
        if not self.is_git_repo():
            logger.warning("Not a git repository.")
            return {"success": False, "message": "Not a git repository"}

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

    def rollback(self):
        """Legacy destructive rollback; automatic invocation is disabled."""
        logger.warning("Rollback is destructive and is not invoked automatically.")
        return {
            "success": False,
            "error": "automatic rollback disabled; inspect and revert only approved paths",
        }
