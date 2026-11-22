"""Reproducible, read-only sampling audits for local Git repositories."""

from __future__ import annotations

import os
import random
import secrets
from pathlib import Path
from typing import Any

from repoforge.blacksmith import Blacksmith
from repoforge.dictionary import CodebaseIndexer
from repoforge.memory import MemoryContextStore
from repoforge.testing import TestForge

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".next",
    ".nuxt",
    "vendor",
    "dist",
    "build",
    "target",
    "coverage",
    ".idea",
    ".vscode",
    ".repoforge",
}


def _is_git_repository(path: Path) -> bool:
    marker = path / ".git"
    return not marker.is_symlink() and (marker.is_dir() or marker.is_file())


def discover_repositories(
    workspace: str | Path,
    *,
    max_depth: int = 5,
    max_repositories: int = 1_000,
) -> list[Path]:
    """Find local Git roots without following symlinks or entering Git internals."""
    root = Path(workspace).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"workspace must be an existing directory: {workspace}")
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or not 0 <= max_depth <= 12:
        raise ValueError("max_depth must be an integer between 0 and 12")
    if (
        isinstance(max_repositories, bool)
        or not isinstance(max_repositories, int)
        or not 1 <= max_repositories <= 10_000
    ):
        raise ValueError("max_repositories must be an integer between 1 and 10000")

    found: list[Path] = []
    for current, directories, _ in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts)
        directories[:] = sorted(
            name
            for name in directories
            if name.casefold() not in SKIP_DIRS and not (current_path / name).is_symlink()
        )
        if _is_git_repository(current_path):
            found.append(current_path)
            directories[:] = []
            if len(found) >= max_repositories:
                break
            continue
        if depth >= max_depth:
            directories[:] = []
    return sorted(set(found), key=lambda item: item.as_posix().casefold())


def _audit_one(repository: Path, *, max_files: int) -> dict[str, Any]:
    """Run metadata-only checks. No repository commands or test code are executed."""
    result: dict[str, Any] = {
        "repository": repository.name,
        "path": str(repository),
        "status": "completed",
        "checks": {},
    }

    try:
        blacksmith = Blacksmith(repository, max_files=max_files).inspect()
        result["checks"]["repository_health"] = {
            "score": blacksmith["rank"]["score"],
            "grade": blacksmith["rank"]["grade"],
            "files_scanned": blacksmith["files_scanned"],
            "scan_incomplete": blacksmith["scan_incomplete"],
            "languages": blacksmith["languages"],
            "signals": blacksmith["signals"],
            "findings": blacksmith["findings"],
            "method": blacksmith["rank"]["method"],
        }
    except Exception as exc:  # Keep the random batch useful when one repository is unreadable.
        result["checks"]["repository_health"] = {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
        }
        result["status"] = "partial"

    try:
        test_plan = TestForge(repository, max_files=max_files).plan()
        result["checks"]["test_discovery"] = {
            "status": test_plan["status"],
            "scan": test_plan["scan"],
            "commands": test_plan["commands"],
            "execution_performed": False,
            "execution_is_sandboxed": False,
        }
    except Exception as exc:
        result["checks"]["test_discovery"] = {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "execution_performed": False,
        }
        result["status"] = "partial"

    try:
        dictionary = CodebaseIndexer(
            repository,
            max_files=min(max_files, 10_000),
            max_file_bytes=1_000_000,
        ).build()
        result["checks"]["codebase_index"] = {
            "languages": dictionary["languages"],
            "summary": dictionary["summary"],
            "persisted": False,
        }
    except Exception as exc:
        result["checks"]["codebase_index"] = {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "persisted": False,
        }
        result["status"] = "partial"
    return result


def _audit_memory_note(repository_report: dict[str, Any]) -> str:
    health = repository_report["checks"].get("repository_health", {})
    index = repository_report["checks"].get("codebase_index", {})
    tests = repository_report["checks"].get("test_discovery", {})
    findings = health.get("findings", [])
    languages = health.get("languages", {})
    summary = index.get("summary", {})
    return (
        "Random audit snapshot (static/read-only): "
        f"health={health.get('score', 'unavailable')}/100 "
        f"({health.get('grade', 'n/a')}); "
        f"files={health.get('files_scanned', summary.get('indexed_files', 'n/a'))}; "
        f"languages={languages or index.get('languages', {})}; "
        f"test discovery={tests.get('status', 'unavailable')}; "
        f"index symbols={summary.get('symbols', 'n/a')}; "
        f"findings={'; '.join(findings[:8]) if findings else 'none recorded'}."
    )


def run_random_audit(
    workspace: str | Path,
    *,
    count: int = 3,
    seed: int | None = None,
    max_depth: int = 5,
    max_repositories: int = 1_000,
    max_files: int = 20_000,
    remember: bool = False,
    memory_context: str = "random-audits",
    memory_store: MemoryContextStore | None = None,
) -> dict[str, Any]:
    """Select a seeded random subset and statically audit each local Git repository."""
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 100:
        raise ValueError("count must be an integer between 1 and 100")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValueError("seed must be an integer")
    if isinstance(max_files, bool) or not isinstance(max_files, int) or not 1 <= max_files <= 100_000:
        raise ValueError("max_files must be an integer between 1 and 100000")
    if not isinstance(remember, bool):
        raise ValueError("remember must be a boolean")
    if remember and (
        not isinstance(memory_context, str)
        or not memory_context
        or len(memory_context) > 48
    ):
        raise ValueError("memory_context must be a non-empty context name of at most 48 characters")

    root = Path(workspace).expanduser().resolve()
    repositories = discover_repositories(
        root, max_depth=max_depth, max_repositories=max_repositories
    )
    if not repositories:
        raise ValueError(f"no local Git repositories found under workspace: {root}")

    actual_seed = secrets.randbits(32) if seed is None else seed
    selected_count = min(count, len(repositories))
    selected = random.Random(actual_seed).sample(repositories, k=selected_count)
    results: list[dict[str, Any]] = []
    store = memory_store or MemoryContextStore()

    for repository in selected:
        item = _audit_one(repository, max_files=max_files)
        if remember:
            try:
                try:
                    existing = store.load(repository, name=memory_context)
                except ValueError as exc:
                    if "does not match" in str(exc):
                        raise
                    existing = None
                if existing is None:
                    store.create(repository, memory_context, switch=False)
                note = store.add_note(repository, _audit_memory_note(item), name=memory_context)
                item["memory"] = {
                    "saved": True,
                    "context": memory_context,
                    "note_id": note["id"],
                }
            except (OSError, ValueError, FileExistsError) as exc:
                item["memory"] = {
                    "saved": False,
                    "context": memory_context,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                item["status"] = "partial"
        results.append(item)

    return {
        "engine": "RepoForge Random Audit",
        "mode": "static_read_only",
        "workspace": str(root),
        "requested_count": count,
        "available_repositories": len(repositories),
        "selected_count": len(selected),
        "seed": actual_seed,
        "max_depth": max_depth,
        "max_files_per_repository": max_files,
        "execution_performed": False,
        "repository_files_modified": False,
        "dictionary_files_written": False,
        "repositories": results,
        "limitations": [
            "Only local Git repositories under the supplied workspace are eligible.",
            "TestForge discovers test commands but does not execute them.",
            "Repository hygiene scores are heuristics, not code-quality or security certifications.",
            "The random sample is reproducible when the returned seed is reused.",
        ],
    }
