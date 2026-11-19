"""RepoBox: isolated local repository storage and disposable workspaces.

RepoBox never edits the imported source checkout. It clones a local Git
repository into its own managed store, then creates detached Git worktrees
for proposed changes. Network URLs are intentionally not accepted by import.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RepoBoxError(RuntimeError):
    """Raised when a RepoBox operation cannot be completed safely."""


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


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
        if not self.manifest_path.exists():
            self._write_manifest({"schema_version": 1, "repositories": []})

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
        return data

    def _write_manifest(self, data: dict[str, Any]) -> None:
        temporary = self.manifest_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.manifest_path)

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
        """Import a local Git checkout by cloning it into RepoBox."""
        source_path = Path(source).expanduser().resolve(strict=True)
        if not source_path.is_dir():
            raise ValueError("repository source must be a local directory")

        top_level = Path(
            _git(["-C", str(source_path), "rev-parse", "--show-toplevel"])
        ).resolve()
        if top_level != source_path:
            raise ValueError("source must be the root of a Git working tree")

        display_name = name or source_path.name
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", display_name).strip("-.") or "repository"
        repo_id = f"{self._validate_id(slug, 'repository name')}-{uuid.uuid4().hex[:8]}"
        destination = self.repositories_dir / repo_id
        _git(["clone", "--no-hardlinks", "--", str(source_path), str(destination)])

        record = {
            "id": repo_id,
            "name": display_name,
            "source_path": str(source_path),
            "managed_path": str(destination),
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "head": _git(["rev-parse", "HEAD"], cwd=destination),
        }
        try:
            manifest = self._read_manifest()
            manifest["repositories"].append(record)
            self._write_manifest(manifest)
        except Exception:
            subprocess.run(
                ["git", "worktree", "prune"],
                cwd=destination,
                capture_output=True,
                text=True,
                timeout=10,
            )
            import shutil

            shutil.rmtree(destination, ignore_errors=True)
            raise
        return record.copy()

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
