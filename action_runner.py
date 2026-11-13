"""
RepoForge Action Runner
Executes strictly parsed Forge actions.
"""

from pathlib import Path
from typing import Any, Dict, List
import logging

logger = logging.getLogger("RepoForge.ActionRunner")

class ActionRunner:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.executed: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    def run(self, actions: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, Any]:
        if not actions:
            return {"status": "no_actions", "executed": [], "errors": [], "completed": 0}

        logger.info(f" Executing {len(actions)} actions (dry_run={dry_run})")

        for action in actions:
            try:
                self._execute_dict_action(action, dry_run)
            except Exception as e:
                logger.error(f"Action failed: {e}")
                self.errors.append({"action": str(action)[:200], "error": str(e)})

        completed = sum(1 for e in self.executed if e.get("status") in ("created", "modified", "ok"))
        return {
            "status": "completed" if not self.errors else "partial",
            "executed": self.executed,
            "errors": self.errors,
            "completed": completed,
        }

    def _execute_dict_action(self, action: Dict[str, Any], dry_run: bool):
        atype = action.get("type", "").lower()
        file = action.get("file", "")
        content = action.get("content", "")

        if atype in ("modify", "create", "write") and file:
            self._write_file(file, content, dry_run)
        elif atype == "delete" and file:
            self._delete_file(file, dry_run)
        else:
            logger.warning(f"Unknown action type: {atype}")

    def _write_file(self, filepath: str, content: str, dry_run: bool):
        full_path = self.repo_path / filepath
        if dry_run:
            logger.info(f" [DRY RUN] Would write: {full_path}")
            self.executed.append({"action": f"Write {filepath}", "status": "dry_run"})
            return
        
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        logger.info(f" Wrote: {full_path}")
        self.executed.append({"action": f"Write {filepath}", "status": "created"})

    def _delete_file(self, filepath: str, dry_run: bool):
        full_path = self.repo_path / filepath
        if not full_path.exists():
            return
        if dry_run:
            logger.info(f" [DRY RUN] Would delete: {full_path}")
            self.executed.append({"action": f"Delete {filepath}", "status": "dry_run"})
            return
        
        full_path.unlink()
        logger.info(f" Deleted: {full_path}")
        self.executed.append({"action": f"Delete {filepath}", "status": "ok"})
