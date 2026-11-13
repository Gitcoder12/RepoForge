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
            return {"success": result.returncode == 0, "output": result.stdout.strip(), "error": result.stderr.strip()}
        except subprocess.TimeoutExpired:
            logger.error("Git command timed out")
            return {"success": False, "error": "Git command timed out"}
        except Exception as e:
            logger.error(f"Git error: {e}")
            return {"success": False, "error": str(e)}

    def is_git_repo(self):
        return self.run_git("rev-parse", "--is-inside-work-tree")["success"]

    def save_state(self, message: str = "RepoForge AI checkpoint"):
        if not self.is_git_repo():
            logger.warning("Not a git repository.")
            return {"success": False, "message": "Not a git repository"}

        if not self.run_git("add", ".")["success"]:
            return {"success": False, "message": "Git add failed"}

        commit_res = self.run_git("commit", "-m", message)
        if not commit_res["success"] and "nothing to commit" not in commit_res.get("error", "").lower():
            return {"success": False, "message": commit_res.get("error")}

        logger.info(f" Git Checkpoint: {message}")
        return {"success": True, "message": "Checkpoint created"}

    def rollback(self):
        logger.warning(" Rolling back git HEAD")
        return self.run_git("reset", "--hard", "HEAD")
