"""RepoForge Action Runner.

Executes strictly parsed Forge actions while confining filesystem changes to
the selected repository root.
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("RepoForge.ActionRunner")


class ActionRunner:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.executed: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []

    def run(self, actions: list[dict[str, Any]], dry_run: bool = False) -> dict[str, Any]:
        if not actions:
            return {"status": "no_actions", "executed": [], "errors": [], "completed": 0}

        logger.info("Executing %s actions (dry_run=%s)", len(actions), dry_run)
        for action in actions:
            try:
                self._execute_dict_action(action, dry_run)
            except Exception as exc:
                logger.error("Action failed: %s", exc)
                self.errors.append({"action": str(action)[:200], "error": str(exc)})

        completed = sum(
            1 for item in self.executed
            if item.get("status") in ("created", "modified", "ok")
        )
        return {
            "status": "completed" if not self.errors else "partial",
            "executed": self.executed,
            "errors": self.errors,
            "completed": completed,
        }

    def _resolve_target(self, filepath: str) -> Path:
        """Resolve a relative path and reject traversal or symlink escapes."""
        if not isinstance(filepath, str) or not filepath.strip():
            raise ValueError("action file path must be a non-empty string")

        relative = Path(filepath)
        if relative.is_absolute():
            raise ValueError("absolute paths are not allowed")

        target = (self.repo_path / relative).resolve()
        try:
            target.relative_to(self.repo_path)
        except ValueError as exc:
            raise ValueError("action path escapes the repository root") from exc
        return target

    def _execute_dict_action(self, action: dict[str, Any], dry_run: bool) -> None:
        if not isinstance(action, dict):
            raise ValueError("action must be an object")

        action_type = str(action.get("type", "")).lower()
        filepath = action.get("file", "")
        content = action.get("content", "")

        if action_type in ("create", "modify") and filepath:
            self._write_file(filepath, content, dry_run, mode=action_type)
        elif action_type == "delete" and filepath:
            self._delete_file(filepath, dry_run)
        else:
            raise ValueError(f"unsupported or incomplete action type: {action_type!r}")

    def _write_file(
        self,
        filepath: str,
        content: str,
        dry_run: bool,
        *,
        mode: str = "write",
    ) -> None:
        target = self._resolve_target(filepath)

        if target.exists() and target.is_dir():
            raise ValueError("action target must be a file, not a directory")
        if mode == "create" and target.exists():
            raise FileExistsError(f"create action will not overwrite existing file: {filepath}")
        if mode == "modify" and not target.is_file():
            raise FileNotFoundError(f"modify action target does not exist: {filepath}")
        if not isinstance(content, str):
            raise ValueError("action content must be a string")

        if dry_run:
            logger.info("[DRY RUN] Would %s %s", mode, target)
            self.executed.append({"action": f"{mode.title()} {filepath}", "status": "dry_run"})
            return

        target.parent.mkdir(parents=True, exist_ok=True)
        if mode == "create":
            with target.open("x", encoding="utf-8") as stream:
                stream.write(content)
            status = "created"
        else:
            target.write_text(content, encoding="utf-8")
            status = "modified" if mode == "modify" else "created"

        logger.info("%s: %s", status.title(), target)
        self.executed.append({"action": f"{mode.title()} {filepath}", "status": status})

    def _delete_file(self, filepath: str, dry_run: bool) -> None:
        target = self._resolve_target(filepath)
        if not target.exists():
            return
        if not target.is_file():
            raise ValueError("delete action may only remove regular files")

        if dry_run:
            logger.info("[DRY RUN] Would delete %s", target)
            self.executed.append({"action": f"Delete {filepath}", "status": "dry_run"})
            return

        target.unlink()
        logger.info("Deleted: %s", target)
        self.executed.append({"action": f"Delete {filepath}", "status": "ok"})
