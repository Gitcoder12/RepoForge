"""Transactional RepoForge file actions with fail-closed path checks."""
from __future__ import annotations

import logging
import os
import stat
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from repoforge.policy import PolicyEngine

logger = logging.getLogger("RepoForge.ActionRunner")
MAX_TRANSACTION_BACKUP_BYTES = 25 * 1024 * 1024


class ActionRunner:
    """Execute approved file actions as a rollback-capable batch.

    This is a filesystem transaction with best-effort rollback, not a database
    transaction: process termination or hardware failure can still interrupt it.
    """

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
        self.executed, self.errors = [], []
        if not isinstance(dry_run, bool) or not isinstance(allow_delete, bool):
            raise TypeError("dry_run and allow_delete must be booleans")
        if not isinstance(actions, list):
            raise TypeError("actions must be a list")
        if not actions:
            return self._result("no_actions")

        if not dry_run:
            repository_result = self.policy.check_repository()
            if not repository_result.allowed:
                self.errors.append({
                    "policy": repository_result.rule_id,
                    "error": repository_result.reason,
                })
                return self._result("blocked")

        targets: list[Path] = []
        for action in actions:
            policy_result = self.policy.evaluate_action(
                action,
                approved_paths=approved_paths,
                allow_delete=allow_delete,
                dry_run=dry_run,
            )
            if not policy_result.allowed:
                self.errors.append({
                    "policy": policy_result.rule_id,
                    "path": policy_result.path,
                    "error": policy_result.reason,
                })
                continue
            try:
                self._preflight_file_action(action)
                targets.append(self._resolve_target(action["file"]))
            except (OSError, TypeError, ValueError) as exc:
                self.errors.append({"path": policy_result.path, "error": str(exc)})

        if self.errors:
            return self._result("blocked")

        snapshots: dict[Path, tuple[bytes, int] | None] = {}
        if not dry_run:
            total_backup = 0
            try:
                for target in targets:
                    if target in snapshots:
                        continue
                    if target.is_file():
                        data = target.read_bytes()
                        total_backup += len(data)
                        if total_backup > MAX_TRANSACTION_BACKUP_BYTES:
                            raise ValueError(
                                f"transaction backup exceeds {MAX_TRANSACTION_BACKUP_BYTES} bytes"
                            )
                        snapshots[target] = (data, stat.S_IMODE(target.stat().st_mode))
                    else:
                        snapshots[target] = None
            except (OSError, ValueError) as exc:
                self.errors.append({"error": f"transaction snapshot failed: {exc}"})
                return self._result("blocked")

        try:
            for action in actions:
                self._execute_dict_action(action, dry_run)
        except (OSError, TypeError, ValueError) as exc:
            logger.error("Action batch failed; attempting rollback: %s", exc)
            self.errors.append({"action": str(action)[:200], "error": str(exc)})
            if not dry_run:
                rollback_errors = self._rollback(snapshots)
                if rollback_errors:
                    self.errors.extend(
                        {"rollback_error": error} for error in rollback_errors
                    )
                    return self._result("rollback_failed")
                for item in self.executed:
                    item["status"] = "rolled_back"
                return self._result("rolled_back")
            return self._result("failed")

        return self._result("completed")

    def _rollback(
        self, snapshots: dict[Path, tuple[bytes, int] | None]
    ) -> list[str]:
        errors: list[str] = []
        for target, snapshot in reversed(list(snapshots.items())):
            try:
                if snapshot is None:
                    if target.exists():
                        target.unlink()
                    continue
                data, mode = snapshot
                target.parent.mkdir(parents=True, exist_ok=True)
                fd, temporary = tempfile.mkstemp(
                    prefix=f".{target.name}.repoforge-rollback-", dir=target.parent
                )
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(data)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.chmod(temporary, mode)
                    os.replace(temporary, target)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            except OSError as exc:
                errors.append(f"{target}: {type(exc).__name__}: {exc}")
        return errors

    def _result(self, status: str) -> dict[str, Any]:
        completed = sum(
            1 for item in self.executed
            if item.get("status") in ("created", "modified", "ok")
        )
        return {
            "status": status,
            "executed": self.executed,
            "errors": self.errors,
            "completed": completed,
            "policy_audit": list(self.policy.audit_events),
        }

    def _resolve_target(self, filepath: str) -> Path:
        """Resolve a canonical relative path and reject symlink traversal."""
        if not isinstance(filepath, str) or not filepath.strip():
            raise ValueError("action file path must be a non-empty string")
        windows = PureWindowsPath(filepath)
        relative = PurePosixPath(filepath.replace("\\", "/"))
        if windows.is_absolute() or windows.drive or relative.is_absolute():
            raise ValueError("absolute paths are not allowed")
        if any(part in {"", ".", ".."} for part in relative.parts):
            raise ValueError("non-canonical or traversal paths are not allowed")

        lexical = self.repo_path.joinpath(*relative.parts)
        current = self.repo_path
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError(f"symlink path components are not allowed: {filepath}")
        target = lexical.resolve()
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
        elif action_type == "delete":
            if not target.is_file():
                raise FileNotFoundError(
                    f"delete action target must be an existing regular file: {filepath}"
                )
        else:
            raise ValueError(f"unsupported or incomplete action type: {action_type!r}")

    def _execute_dict_action(self, action: dict[str, Any], dry_run: bool) -> None:
        action_type = str(action.get("type", "")).lower()
        filepath = action.get("file", "")
        if action_type in ("create", "modify"):
            self._write_file(filepath, action.get("content", ""), dry_run, mode=action_type)
        elif action_type == "delete":
            self._delete_file(filepath, dry_run)

    def _write_file(
        self, filepath: str, content: str, dry_run: bool, *, mode: str
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
            self.executed.append({"action": f"{mode.title()} {filepath}", "status": "dry_run"})
            return

        target.parent.mkdir(parents=True, exist_ok=True)
        if mode == "create":
            with target.open("x", encoding="utf-8", newline="") as stream:
                stream.write(content)
            status = "created"
        else:
            fd, temporary = tempfile.mkstemp(
                prefix=f".{target.name}.repoforge-", dir=target.parent
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temporary, stat.S_IMODE(target.stat().st_mode))
                os.replace(temporary, target)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            status = "modified"
        logger.info("%s: %s", status.title(), target)
        self.executed.append({"action": f"{mode.title()} {filepath}", "status": status})

    def _delete_file(self, filepath: str, dry_run: bool) -> None:
        target = self._resolve_target(filepath)
        if not target.is_file():
            raise FileNotFoundError(f"delete target does not exist: {filepath}")
        if dry_run:
            self.executed.append({"action": f"Delete {filepath}", "status": "dry_run"})
            return
        target.unlink()
        logger.info("Deleted: %s", target)
        self.executed.append({"action": f"Delete {filepath}", "status": "ok"})
