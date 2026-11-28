"""Canonical RepoForge Action Runner with constitutional mutation checks."""

from __future__ import annotations

import logging
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

from repoforge.policy import PolicyEngine

logger = logging.getLogger("RepoForge.ActionRunner")


class ActionRunner:
    """Execute a preflighted batch of approved repository file actions."""

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.executed: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.policy = PolicyEngine(self.repo_path)

    def run(
        self,
        actions: list[dict[str, Any]],
        dry_run: bool = False,
        *,
        approved_paths: set[str] | None = None,
        allow_delete: bool = False,
    ) -> dict[str, Any]:
        self.executed = []
        self.errors = []
        if not actions:
            return {"status": "no_actions", "executed": [], "errors": [], "completed": 0}

        if not dry_run:
            repository_result = self.policy.check_repository()
            if not repository_result.allowed:
                self.errors.append(
                    {"policy": repository_result.rule_id, "error": repository_result.reason}
                )
                return self._result("blocked")

        # Validate every action before the first write. A single denial blocks
        # the batch so a mixed approved/unapproved plan cannot partially apply.
        for action in actions:
            policy_result = self.policy.evaluate_action(
                action,
                approved_paths=approved_paths,
                allow_delete=allow_delete,
                dry_run=dry_run,
            )
            if not policy_result.allowed:
                self.errors.append(
                    {
                        "policy": policy_result.rule_id,
                        "path": policy_result.path,
                        "error": policy_result.reason,
                    }
                )
                continue
            try:
                self._preflight_file_action(action)
            except (OSError, TypeError, ValueError) as exc:
                self.errors.append({"path": policy_result.path, "error": str(exc)})

        if self.errors:
            return self._result("blocked")

        if dry_run:
            for action in actions:
                try:
                    self._execute_dict_action(action, True)
                except (OSError, TypeError, ValueError) as exc:
                    logger.error("Dry-run action failed: %s", exc)
                    self.errors.append({"action": str(action)[:200], "error": str(exc)})
            return self._result("completed" if not self.errors else "partial")

        # Snapshot every distinct target before the first mutation. If any
        # operation fails, restore the original bytes (or remove newly-created
        # files) so a failed batch does not silently leave a partial repair.
        snapshots: dict[Path, tuple[bytes, int] | None] = {}
        try:
            for action in actions:
                target = self._resolve_target(action["file"])
                if target not in snapshots:
                    snapshots[target] = (
                        (target.read_bytes(), stat.S_IMODE(target.stat().st_mode))
                        if target.is_file()
                        else None
                    )
        except (OSError, TypeError, ValueError, KeyError) as exc:
            self.errors.append({"error": f"could not snapshot mutation targets: {exc}"})
            return self._result("blocked")

        for action in actions:
            try:
                self._execute_dict_action(action, False)
            except (OSError, TypeError, ValueError) as exc:
                logger.error("Action failed; rolling back batch: %s", exc)
                self.errors.append({"action": str(action)[:200], "error": str(exc)})
                rollback_errors = self._restore_snapshot(snapshots)
                for item in self.executed:
                    if item.get("status") in ("created", "modified", "ok"):
                        item["status"] = "rolled_back"
                if rollback_errors:
                    self.errors.extend(rollback_errors)
                    return self._result("rollback_failed")
                return self._result("rolled_back")

        return self._result("completed")

    def _restore_snapshot(
        self, snapshots: dict[Path, tuple[bytes, int] | None]
    ) -> list[dict[str, str]]:
        """Restore original file contents after a failed mutation batch."""
        failures: list[dict[str, str]] = []
        for target, snapshot in reversed(list(snapshots.items())):
            temporary_path: str | None = None
            try:
                if snapshot is None:
                    target.unlink(missing_ok=True)
                    continue
                content, mode = snapshot
                target.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    dir=target.parent,
                    prefix=f".{target.name}.repoforge-rollback-",
                    delete=False,
                ) as stream:
                    stream.write(content)
                    temporary_path = stream.name
                os.chmod(temporary_path, mode)
                os.replace(temporary_path, target)
                temporary_path = None
            except OSError as exc:
                failures.append(
                    {"path": str(target), "rollback_error": f"{type(exc).__name__}: {exc}"}
                )
            finally:
                if temporary_path:
                    try:
                        Path(temporary_path).unlink(missing_ok=True)
                    except OSError:
                        pass
        return failures

    def _result(self, status: str) -> dict[str, Any]:
        completed = sum(
            1 for item in self.executed if item.get("status") in ("created", "modified", "ok")
        )
        return {
            "status": status,
            "executed": self.executed,
            "errors": self.errors,
            "completed": completed,
            "policy_audit": list(self.policy.audit_events),
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

    def _preflight_file_action(self, action: dict[str, Any]) -> None:
        if not isinstance(action, dict):
            raise ValueError("action must be an object")
        action_type = str(action.get("type", "")).lower()
        filepath = action.get("file", "")
        target = self._resolve_target(filepath)
        if action_type in ("create", "modify"):
            if not isinstance(action.get("content", ""), str):
                raise ValueError("action content must be a string")
            if target.exists() and target.is_dir():
                raise ValueError("action target must be a file, not a directory")
            if action_type == "create" and target.exists():
                raise FileExistsError(f"create action will not overwrite existing file: {filepath}")
            if action_type == "modify" and not target.is_file():
                raise FileNotFoundError(f"modify action target does not exist: {filepath}")
        elif action_type == "delete" and target.exists() and not target.is_file():
            raise ValueError("delete action may only remove regular files")
        elif action_type not in ("create", "modify", "delete"):
            raise ValueError(f"unsupported or incomplete action type: {action_type!r}")

    def _execute_dict_action(self, action: dict[str, Any], dry_run: bool) -> None:
        action_type = str(action.get("type", "")).lower()
        filepath = action.get("file", "")
        content = action.get("content", "")
        if action_type in ("create", "modify"):
            self._write_file(filepath, content, dry_run, mode=action_type)
        elif action_type == "delete":
            self._delete_file(filepath, dry_run)

    def _write_file(
        self,
        filepath: str,
        content: str,
        dry_run: bool,
        *,
        mode: str,
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
            status = "modified"
        logger.info("%s: %s", status.title(), target)
        self.executed.append({"action": f"{mode.title()} {filepath}", "status": status})

    def _delete_file(self, filepath: str, dry_run: bool) -> None:
        target = self._resolve_target(filepath)
        if not target.exists():
            raise FileNotFoundError(f"delete target does not exist: {filepath}")
        if not target.is_file():
            raise ValueError("delete action may only remove regular files")
        if dry_run:
            logger.info("[DRY RUN] Would delete %s", target)
            self.executed.append({"action": f"Delete {filepath}", "status": "dry_run"})
            return
        target.unlink()
        logger.info("Deleted: %s", target)
        self.executed.append({"action": f"Delete {filepath}", "status": "ok"})
