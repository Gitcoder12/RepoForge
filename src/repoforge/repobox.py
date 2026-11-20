"""RepoBox: isolated local repository storage and disposable workspaces.

RepoBox never edits the imported source checkout. It clones a clean local Git
repository into its own managed store, then creates detached Git worktrees
for proposed changes. Network URLs are intentionally not accepted by import.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class RepoBoxError(RuntimeError):
    """Raised when a RepoBox operation cannot be completed safely."""


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_VALID_GIT_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


def _git(args: list[str], *, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RepoBoxError(f"Git command could not complete: {exc}") from exc
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        raise RepoBoxError(detail)
    return result.stdout.strip()


class RepoBox:
    """Manage imported repositories and isolated worktrees under one storage root."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.repositories_dir = self.root / "repositories"
        self.workspaces_dir = self.root / "workspaces"
        self.manifest_path = self.root / "manifest.json"
        self.repositories_dir.mkdir(parents=True, exist_ok=True)
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        with self._manifest_lock():
            if not self.manifest_path.exists():
                self._write_manifest({"schema_version": 1, "repositories": []})

    @contextmanager
    def _manifest_lock(self) -> Iterator[None]:
        """Serialize manifest read-modify-write operations across processes.

        The lock is an atomic directory creation, so it works without an
        additional platform-specific locking dependency. A timed-out lock is
        never removed automatically: an operator must first verify that its
        owner process is no longer running.
        """
        lock_dir = self.root / ".manifest.lock"
        deadline = time.monotonic() + 15
        while True:
            try:
                lock_dir.mkdir()
                break
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise RepoBoxError(
                        "RepoBox manifest is locked; retry after the active operation "
                        "finishes. If a previous process crashed, verify it is stopped "
                        "before removing the stale .manifest.lock directory."
                    )
                time.sleep(0.05)

        try:
            (lock_dir / "owner.txt").write_text(
                f"pid={os.getpid()}\ncreated={datetime.now(timezone.utc).isoformat()}\n",
                encoding="utf-8",
            )
            yield
        finally:
            shutil.rmtree(lock_dir, ignore_errors=True)

    def _read_manifest(self) -> dict[str, Any]:
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RepoBoxError(f"RepoBox manifest is unreadable: {exc}") from exc
        if (
            not isinstance(data, dict)
            or data.get("schema_version") != 1
            or not isinstance(data.get("repositories"), list)
        ):
            raise RepoBoxError("RepoBox manifest has an unsupported or invalid schema")

        known_ids: set[str] = set()
        managed_root = self.repositories_dir.resolve()
        required = {"id", "name", "source_path", "managed_path", "imported_at", "head"}
        for index, record in enumerate(data["repositories"]):
            if not isinstance(record, dict) or not required.issubset(record):
                raise RepoBoxError(f"RepoBox manifest record {index} is incomplete")
            try:
                repo_id = self._validate_id(record["id"], "repository id")
            except (TypeError, ValueError) as exc:
                raise RepoBoxError(f"RepoBox manifest record {index} has an invalid id") from exc
            if repo_id in known_ids:
                raise RepoBoxError(f"RepoBox manifest contains duplicate repository id: {repo_id}")
            known_ids.add(repo_id)
            for field in ("name", "source_path", "managed_path", "imported_at"):
                if not isinstance(record[field], str) or not record[field]:
                    raise RepoBoxError(
                        f"RepoBox manifest record {index} has an invalid {field}"
                    )
            if not isinstance(record["head"], str) or not _VALID_GIT_SHA.fullmatch(
                record["head"]
            ):
                raise RepoBoxError(f"RepoBox manifest record {index} has an invalid Git HEAD")
            managed_path = Path(record["managed_path"]).resolve()
            if managed_path.parent != managed_root or managed_path.name != repo_id:
                raise RepoBoxError(
                    f"RepoBox manifest record {index} points outside managed storage"
                )
        return data

    def _write_manifest(self, data: dict[str, Any]) -> None:
        """Atomically replace the manifest; caller must hold the manifest lock."""
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.root,
                prefix=".manifest-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.manifest_path)
            if hasattr(os, "O_DIRECTORY"):
                directory_fd = os.open(self.root, os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except (OSError, TypeError, ValueError) as exc:
            raise RepoBoxError(f"RepoBox manifest could not be written atomically: {exc}") from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    @staticmethod
    def _validate_id(value: str, label: str) -> str:
        if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
            raise ValueError(
                f"{label} must be 1-64 safe characters: letters, numbers, dot, underscore or hyphen"
            )
        if value in {".", ".."}:
            raise ValueError(f"{label} is not a valid identifier")
        return value

    def import_repository(self, source: str | Path, *, name: str | None = None) -> dict[str, Any]:
        """Import a clean local Git checkout without changing the source tree."""
        source_path = Path(source).expanduser().resolve(strict=True)
        if not source_path.is_dir():
            raise ValueError("repository source must be a local directory")

        top_level = Path(
            _git(["-C", str(source_path), "rev-parse", "--show-toplevel"])
        ).resolve()
        if top_level != source_path:
            raise ValueError("source must be the root of a Git working tree")

        dirty_before = _git(
            ["status", "--porcelain", "--untracked-files=all"], cwd=source_path
        )
        if dirty_before:
            raise RepoBoxError(
                "source working tree has uncommitted or untracked changes; "
                "commit or stash them before importing"
            )
        source_head_before = _git(["rev-parse", "HEAD"], cwd=source_path)

        display_name = name or source_path.name
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", display_name).strip("-.") or "repository"
        repo_id = f"{self._validate_id(slug[:55], 'repository name')}-{uuid.uuid4().hex[:8]}"
        destination = self.repositories_dir / repo_id

        try:
            _git(["clone", "--no-hardlinks", "--", str(source_path), str(destination)])
            managed_head = _git(["rev-parse", "HEAD"], cwd=destination)
            source_head_after = _git(["rev-parse", "HEAD"], cwd=source_path)
            dirty_after = _git(
                ["status", "--porcelain", "--untracked-files=all"], cwd=source_path
            )
            if source_head_after != source_head_before or dirty_after:
                raise RepoBoxError(
                    "source repository changed during import; no managed copy was registered"
                )
            if managed_head != source_head_before:
                raise RepoBoxError(
                    "managed clone does not match the source HEAD observed before import"
                )

            record = {
                "id": repo_id,
                "name": display_name,
                "source_path": str(source_path),
                "managed_path": str(destination),
                "imported_at": datetime.now(timezone.utc).isoformat(),
                "head": managed_head,
            }
            with self._manifest_lock():
                manifest = self._read_manifest()
                manifest["repositories"].append(record)
                self._write_manifest(manifest)
            return record.copy()
        except Exception:
            # A failed clone can leave a partial destination. It is safe to
            # remove because this UUID path did not exist before this import.
            shutil.rmtree(destination, ignore_errors=True)
            raise

    def list_repositories(self) -> list[dict[str, Any]]:
        """Return registered repository records without changing their contents."""
        return [dict(item) for item in self._read_manifest()["repositories"]]

    def create_workspace(self, repo_id: str, task_id: str) -> dict[str, str]:
        """Create a detached worktree for a task inside the managed clone."""
        repo_id = self._validate_id(repo_id, "repository id")
        task_id = self._validate_id(task_id, "task id")
        records = {item["id"]: item for item in self._read_manifest()["repositories"]}
        if repo_id not in records:
            raise KeyError(f"unknown RepoBox repository: {repo_id}")

        managed = Path(records[repo_id]["managed_path"]).resolve()
        if managed.parent != self.repositories_dir.resolve() or not managed.is_dir():
            raise RepoBoxError("managed repository path is missing or outside RepoBox")

        workspace = (self.workspaces_dir / f"{repo_id}--{task_id}").resolve()
        if workspace.parent != self.workspaces_dir.resolve():
            raise ValueError("workspace path escapes RepoBox")
        if workspace.exists():
            raise FileExistsError(f"workspace already exists: {workspace}")

        _git(["worktree", "add", "--detach", str(workspace), "HEAD"], cwd=managed)
        return {"repository_id": repo_id, "task_id": task_id, "workspace": str(workspace)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RepoBox isolated repository workspaces")
    parser.add_argument(
        "--root",
        default=str(Path.home() / ".repoforge" / "repobox"),
        help="RepoBox storage directory",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("import", help="import a local Git checkout")
    add.add_argument("source")
    add.add_argument("--name")
    commands.add_parser("list", help="list imported repositories")
    workspace = commands.add_parser("workspace", help="create an isolated task worktree")
    workspace.add_argument("repository_id")
    workspace.add_argument("task_id")

    args = parser.parse_args(argv)
    box = RepoBox(args.root)
    try:
        if args.command == "import":
            result: Any = box.import_repository(args.source, name=args.name)
        elif args.command == "list":
            result = box.list_repositories()
        else:
            result = box.create_workspace(args.repository_id, args.task_id)
    except (RepoBoxError, OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
