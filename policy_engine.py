"""Fail-closed engineering policy for RepoForge repository mutations."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    rule_id: str
    reason: str
    path: str | None = None


class PolicyEngine:
    """Checks repository state and per-path authorization before writes."""

    PROTECTED_BRANCHES = frozenset({"main", "master", "develop", "production", "release"})

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.audit_events: list[dict[str, Any]] = []

    def _record(self, result: PolicyResult, operation: str) -> PolicyResult:
        self.audit_events.append({
            "operation": operation,
            "allowed": result.allowed,
            "rule_id": result.rule_id,
            "path": result.path,
            "reason": result.reason,
        })
        if len(self.audit_events) > 1000:
            del self.audit_events[:-1000]
        return result

    def check_repository(self) -> PolicyResult:
        if not self.repo_path.is_dir():
            return self._record(PolicyResult(False, "RF-01", "repository path is not a directory"), "repository")
        try:
            root = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.repo_path, capture_output=True, text=True, timeout=10, check=False,
            )
            if root.returncode != 0:
                return self._record(PolicyResult(False, "RF-02", "target is not a Git working tree"), "repository")
            actual_root = Path(root.stdout.strip()).resolve()
            if actual_root != self.repo_path:
                return self._record(PolicyResult(False, "RF-01", "target path is not the Git repository root"), "repository")

            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path, capture_output=True, text=True, timeout=10, check=False,
            )
            if branch.returncode != 0 or not branch.stdout.strip():
                return self._record(PolicyResult(False, "RF-03", "cannot verify branch; detached or unknown HEAD is denied"), "repository")
            branch_name = branch.stdout.strip()
            if branch_name.lower() in self.PROTECTED_BRANCHES:
                return self._record(PolicyResult(False, "RF-03", f"writes to protected branch '{branch_name}' are denied"), "repository")

            status = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=all"],
                cwd=self.repo_path, capture_output=True, text=True, timeout=10, check=False,
            )
            if status.returncode != 0:
                return self._record(PolicyResult(False, "RF-02", "cannot verify working-tree state"), "repository")
            if status.stdout.strip():
                return self._record(PolicyResult(False, "RF-02", "working tree is dirty; preserving existing user changes"), "repository")
            return self._record(PolicyResult(True, "RF-00", f"clean working tree on branch '{branch_name}'"), "repository")
        except (OSError, subprocess.TimeoutExpired) as exc:
            return self._record(PolicyResult(False, "RF-02", f"repository preflight failed: {type(exc).__name__}"), "repository")

    @staticmethod
    def _normalize_path(value: Any) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        if PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute():
            return None
        path = PurePosixPath(value.replace("\\", "/"))
        if any(part in ("", ".", "..") for part in path.parts):
            return None
        return path.as_posix()

    def evaluate_action(
        self,
        action: dict[str, Any],
        *,
        approved_paths: set[str] | None = None,
        allow_delete: bool = False,
        dry_run: bool = False,
    ) -> PolicyResult:
        if not isinstance(action, dict):
            return self._record(PolicyResult(False, "RF-04", "action must be an object"), "action")
        action_type = str(action.get("type", "")).lower()
        path = self._normalize_path(action.get("file"))
        if path is None:
            return self._record(PolicyResult(False, "RF-04", "invalid, absolute, or traversal path denied"), action_type or "unknown")
        if action_type not in {"create", "modify", "delete"}:
            return self._record(PolicyResult(False, "RF-04", f"unsupported action type: {action_type!r}", path), action_type)
        if action_type == "delete" and not (allow_delete or dry_run):
            return self._record(PolicyResult(False, "RF-06", "delete requires explicit allow_delete approval", path), action_type)
        approved = {
            normalized for item in (approved_paths or set())
            if (normalized := self._normalize_path(item)) is not None
        }
        if not dry_run and path not in approved:
            return self._record(PolicyResult(False, "RF-06", "exact target path has not been approved", path), action_type)
        reason = "dry-run preview; no filesystem mutation" if dry_run else "exact path approved"
        return self._record(PolicyResult(True, "RF-00", reason, path), action_type)
