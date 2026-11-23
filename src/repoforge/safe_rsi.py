"""Deterministic, approval-gated single-step RSI transaction."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from repoforge.action_runner import ActionRunner
from repoforge.git_manager import GitManager
from repoforge.validator import Validator


def _normalize_actions(
    repo_root: Path,
    actions: list[dict[str, str]],
    approved_paths: set[str],
) -> tuple[list[dict[str, str]], list[str]]:
    if not isinstance(actions, list) or not actions:
        raise ValueError("actions must be a non-empty list")
    if not isinstance(approved_paths, set) or not all(
        isinstance(path, str) for path in approved_paths
    ):
        raise ValueError("approved_paths must be a set of repository-relative strings")

    normalized: list[dict[str, str]] = []
    paths: list[str] = []
    seen: set[str] = set()
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError("each action must be an object")
        action_type = action.get("type")
        filepath = action.get("file")
        content = action.get("content")
        if action_type not in {"create", "modify"}:
            raise ValueError("create/modify only; delete is disabled")
        if not isinstance(filepath, str) or not isinstance(content, str):
            raise ValueError("each action requires string file and content fields")

        relative = filepath.replace("\\", "/")
        path = PurePosixPath(relative)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in relative.split("/")):
            raise ValueError(f"unsafe repository-relative path: {filepath!r}")
        normalized_path = path.as_posix()
        if normalized_path in seen:
            raise ValueError(f"duplicate action path: {normalized_path}")
        seen.add(normalized_path)
        if Path(normalized_path).suffix.casefold() != ".py":
            raise ValueError(
                f"unsupported validation language for {normalized_path}; "
                "Phase 1 validates Python files only"
            )

        target = repo_root / normalized_path
        if target.is_symlink():
            raise ValueError(f"symlink targets are denied: {normalized_path}")
        try:
            target.resolve().relative_to(repo_root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise ValueError(f"target escapes repository root: {normalized_path}") from exc

        normalized.append({"type": action_type, "file": normalized_path, "content": content})
        paths.append(normalized_path)

    if approved_paths != set(paths):
        missing = sorted(set(paths) - approved_paths)
        extra = sorted(approved_paths - set(paths))
        raise PermissionError(
            f"approval must exactly match proposed paths; missing={missing}, extra={extra}"
        )
    return normalized, paths


def _validate_proposed_python(actions: list[dict[str, str]]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="repoforge-preflight-") as temporary:
        root = Path(temporary).resolve()
        targets: list[str] = []
        for action in actions:
            target = root / action["file"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(action["content"], encoding="utf-8")
            targets.append(action["file"])
        return asyncio.run(Validator(root).validate(target_files=targets))


def _snapshot_paths(root: Path, paths: list[str]) -> dict[str, tuple[bytes, int] | None]:
    snapshots: dict[str, tuple[bytes, int] | None] = {}
    for relative in paths:
        target = root / relative
        if target.is_symlink():
            raise ValueError(f"symlink targets are denied: {relative}")
        target.resolve().relative_to(root)
        if not target.exists():
            snapshots[relative] = None
        elif not target.is_file():
            raise ValueError(f"target is not a regular file: {relative}")
        else:
            stat = target.stat()
            snapshots[relative] = (target.read_bytes(), stat.st_mode & 0o777)
    return snapshots


def _restore_paths(
    root: Path,
    actions: list[dict[str, str]],
    snapshots: dict[str, tuple[bytes, int] | None],
) -> dict[str, Any]:
    """Restore only files that still match this step's proposed output."""
    restored: list[str] = []
    conflicts: list[str] = []
    action_by_path = {item["file"]: item for item in actions}

    for relative, original in snapshots.items():
        target = root / relative
        expected = action_by_path[relative]["content"].encode("utf-8")
        try:
            if target.is_symlink():
                conflicts.append(relative)
                continue
            if original is None:
                if not target.exists():
                    continue
                if not target.is_file() or target.read_bytes() != expected:
                    conflicts.append(relative)
                    continue
                target.unlink()
                restored.append(relative)
                continue

            original_bytes, original_mode = original
            if target.is_file() and target.read_bytes() == original_bytes:
                continue
            if not target.is_file() or target.read_bytes() != expected:
                conflicts.append(relative)
                continue

            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".repoforge-restore-", dir=str(target.parent)
            )
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(original_bytes)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temporary_name, original_mode)
                os.replace(temporary_name, target)
            finally:
                if os.path.exists(temporary_name):
                    os.unlink(temporary_name)
            restored.append(relative)
        except (OSError, RuntimeError, ValueError):
            conflicts.append(relative)

    return {
        "status": "conflict" if conflicts else "restored",
        "restored_paths": restored,
        "conflict_paths": conflicts,
    }


def safe_rsi_step(
    repo_path: str | Path,
    actions: list[dict[str, str]],
    *,
    approved_paths: set[str],
    apply: bool = False,
) -> dict[str, Any]:
    """Checkpoint, dry-run, validate, apply approved paths, and recover on failure.

    The working tree must be clean and on an unprotected branch. Phase 1 accepts
    Python files only because the current validator is Python-AST-only.
    Target tests are never executed by this function.
    """
    root = Path(repo_path).expanduser().resolve()
    report: dict[str, Any] = {
        "operation": "safe_rsi_step",
        "status": "blocked",
        "checkpoint": None,
        "approved_paths": sorted(approved_paths) if isinstance(approved_paths, set) else [],
        "dry_run": None,
        "pre_validation": None,
        "mutation": {"status": "not_started"},
        "post_validation": None,
        "rollback": {"status": "not_needed"},
        "tests": {"status": "not_run"},
    }
    if not root.is_dir():
        report["reason"] = "repository path is not a directory"
        return report
    if not isinstance(apply, bool):
        report["reason"] = "apply must be a boolean"
        return report

    try:
        normalized, paths = _normalize_actions(root, actions, approved_paths)
        checkpoint = GitManager(root).save_state()
        if not checkpoint.get("success"):
            report["reason"] = checkpoint.get("message", "checkpoint failed")
            return report
        report["checkpoint"] = checkpoint["checkpoint"]

        runner = ActionRunner(root)
        dry_run = runner.run(normalized, dry_run=True)
        report["dry_run"] = dry_run
        if dry_run.get("status") != "completed":
            report["reason"] = "dry-run preflight failed"
            return report

        pre_validation = _validate_proposed_python(normalized)
        report["pre_validation"] = pre_validation
        if not pre_validation.get("passed"):
            report["reason"] = "proposed code failed pre-validation"
            return report

        if not apply:
            report["status"] = "previewed"
            report["reason"] = "validated plan only; no repository files changed"
            return report

        snapshots = _snapshot_paths(root, paths)
        mutation = runner.run(
            normalized,
            dry_run=False,
            approved_paths=set(paths),
            allow_delete=False,
        )
        report["mutation"] = mutation
        if mutation.get("status") != "completed":
            report["rollback"] = _restore_paths(root, normalized, snapshots)
            report["status"] = (
                "rolled_back"
                if report["rollback"]["status"] == "restored"
                else "rollback_conflict"
            )
            report["reason"] = "apply did not complete; path-scoped recovery attempted"
            return report

        post_validation = asyncio.run(Validator(root).validate(target_files=paths))
        report["post_validation"] = post_validation
        if not post_validation.get("passed"):
            report["rollback"] = _restore_paths(root, normalized, snapshots)
            report["status"] = (
                "rolled_back"
                if report["rollback"]["status"] == "restored"
                else "rollback_conflict"
            )
            report["reason"] = "post-validation failed; path-scoped recovery attempted"
            return report

        report["status"] = "applied"
        report["reason"] = "approved paths applied and post-validation passed"
        return report
    except (OSError, RuntimeError, TypeError, ValueError, PermissionError) as exc:
        report["reason"] = f"{type(exc).__name__}: {exc}"
        return report
