"""Isolated, user-controlled project memory for RepoForge.

Memory is stored outside target repositories and is scoped to each resolved local
repository path. Notes are user-authored context, not trusted instructions.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_CONTEXT_NAME = 48
MAX_NOTE_CHARS = 4_000
MAX_NOTES = 200
MAX_CONTEXT_BYTES = 2_000_000

_SECRET_ASSIGNMENT = re.compile(
    r"(?im)(api[_-]?key|secret|token|password|authorization|private[_-]?key)"
    r"(\s*[=:]\s*)([\"'][^\"'\r\n]*[\"']|[^\s,;]+)"
)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_context_name(name: str) -> str:
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,47}", name):
        raise ValueError(
            "context name must be 1-48 characters and use letters, numbers, '.', '_' or '-'"
        )
    if name in {".", "..", "active"}:
        raise ValueError("reserved context name")
    return name


def _redact_note(note: str) -> str:
    return _SECRET_ASSIGNMENT.sub(r"\1\2[REDACTED]", note)


class MemoryContextStore:
    """Keep independent named memories for each local repository clone.

    There is no process-global 'current project' pointer. The active context is
    recorded inside a repository-specific directory, so switching project A
    cannot change the active context for project B.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        if root is not None:
            base = Path(root).expanduser()
        elif os.environ.get("REPOFORGE_HOME"):
            base = Path(os.environ["REPOFORGE_HOME"]).expanduser() / "memory"
        elif os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "RepoForge" / "memory"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
            base = base / "repoforge" / "memory"
        self.root = base.resolve()

    @staticmethod
    def _repository_path(repository: str | Path) -> Path:
        root = Path(repository).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"repository path must be an existing directory: {repository}")
        return root

    @staticmethod
    def _repository_key(root: Path) -> str:
        identity = os.path.normcase(str(root))
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]

    def _directory(self, root: Path, *, create: bool) -> Path:
        if self.root == root or root in self.root.parents:
            raise ValueError("memory storage must be outside the target repository")
        if not self.root.exists() and not create:
            return self.root / self._repository_key(root)
        if create:
            self.root.mkdir(parents=True, exist_ok=True)
        if self.root.is_symlink() or not self.root.is_dir():
            raise ValueError("memory storage root must be a real directory")
        directory = self.root / self._repository_key(root)
        if directory.is_symlink():
            raise ValueError("repository memory directory must not be a symlink")
        if create:
            directory.mkdir(mode=0o700, exist_ok=True)
        if not directory.exists():
            return directory
        if not directory.is_dir():
            raise ValueError("repository memory path is not a directory")
        return directory

    @staticmethod
    def _context_path(directory: Path, name: str) -> Path:
        return directory / f"{_validate_context_name(name)}.json"

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        if path.is_symlink() or not path.is_file():
            return None
        try:
            if path.stat().st_size > MAX_CONTEXT_BYTES:
                raise ValueError("memory context exceeds the maximum supported size")
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid memory context JSON: {path.name}") from exc
        except OSError as exc:
            raise ValueError(f"could not read memory context {path.name}: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"unsupported memory context format: {path.name}")
        return payload

    @staticmethod
    def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
        if path.is_symlink():
            raise ValueError("refusing to replace a symlink in memory storage")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.parent.is_symlink():
            raise ValueError("memory context directory must not be a symlink")
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=".repoforge-memory-",
                suffix=".tmp",
                dir=path.parent,
                delete=False,
            ) as handle:
                temporary = handle.name
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            if os.name != "nt":
                os.chmod(temporary, 0o600)
            os.replace(temporary, path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def _read_active_name(self, directory: Path) -> str | None:
        active = self._read_json(directory / "active.json")
        if active is None:
            return None
        name = active.get("context")
        if not isinstance(name, str):
            raise ValueError("active memory pointer has no valid context name")
        return _validate_context_name(name)

    def create(self, repository: str | Path, name: str, *, switch: bool = True) -> dict[str, Any]:
        """Create an empty named context and optionally make it active."""
        root = self._repository_path(repository)
        name = _validate_context_name(name)
        if not isinstance(switch, bool):
            raise ValueError("switch must be a boolean")
        directory = self._directory(root, create=True)
        destination = self._context_path(directory, name)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"memory context already exists: {name}")
        now = _timestamp()
        payload = {
            "schema_version": SCHEMA_VERSION,
            "repository": {"name": root.name, "path": str(root), "key": self._repository_key(root)},
            "name": name,
            "created_at": now,
            "updated_at": now,
            "notes": [],
        }
        self._atomic_write(destination, payload)
        if switch:
            self.switch(root, name)
        return payload

    def switch(self, repository: str | Path, name: str) -> dict[str, str]:
        """Switch only the active memory for the specified repository."""
        root = self._repository_path(repository)
        name = _validate_context_name(name)
        directory = self._directory(root, create=False)
        context_file = self._context_path(directory, name)
        if not context_file.is_file() or context_file.is_symlink():
            raise ValueError(f"memory context does not exist for this repository: {name}")
        self._read_json(context_file)
        payload = {"schema_version": SCHEMA_VERSION, "context": name, "updated_at": _timestamp()}
        self._atomic_write(directory / "active.json", payload)
        return payload

    def list_contexts(self, repository: str | Path) -> dict[str, Any]:
        """List available contexts and the active context for this repository."""
        root = self._repository_path(repository)
        directory = self._directory(root, create=False)
        if not directory.exists():
            return {"repository": str(root), "active": None, "contexts": []}
        active = self._read_active_name(directory)
        contexts = []
        for path in sorted(directory.glob("*.json")):
            if path.name == "active.json" or path.is_symlink():
                continue
            payload = self._read_json(path)
            if payload is None:
                continue
            contexts.append(
                {
                    "name": payload.get("name", path.stem),
                    "notes": len(payload.get("notes", []))
                    if isinstance(payload.get("notes"), list)
                    else 0,
                    "updated_at": payload.get("updated_at"),
                    "active": payload.get("name") == active,
                }
            )
        return {"repository": str(root), "active": active, "contexts": contexts}

    def load(
        self, repository: str | Path, *, name: str | None = None
    ) -> dict[str, Any] | None:
        """Load a named context or the active context; never search other repos."""
        root = self._repository_path(repository)
        directory = self._directory(root, create=False)
        if not directory.exists():
            if name is not None:
                raise ValueError(f"memory context does not exist for this repository: {name}")
            return None
        selected = _validate_context_name(name) if name is not None else self._read_active_name(
            directory
        )
        if selected is None:
            return None
        payload = self._read_json(self._context_path(directory, selected))
        if payload is None:
            raise ValueError(f"memory context does not exist for this repository: {selected}")
        repository_meta = payload.get("repository")
        if (
            not isinstance(repository_meta, dict)
            or repository_meta.get("key") != self._repository_key(root)
            or repository_meta.get("path") != str(root)
            or payload.get("name") != selected
            or not isinstance(payload.get("notes"), list)
        ):
            raise ValueError("memory context repository identity does not match")
        return payload

    def add_note(
        self,
        repository: str | Path,
        note: str,
        *,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Append a bounded user note to the active or explicitly named context."""
        if not isinstance(note, str) or not note.strip():
            raise ValueError("note must be non-empty text")
        if len(note) > MAX_NOTE_CHARS:
            raise ValueError(f"note must be at most {MAX_NOTE_CHARS} characters")
        root = self._repository_path(repository)
        payload = self.load(root, name=name)
        if payload is None:
            raise ValueError("no active memory context; create or switch a context first")
        notes = payload["notes"]
        if len(notes) >= MAX_NOTES:
            raise ValueError(f"memory context already contains {MAX_NOTES} notes")
        clean_note = _redact_note(note.strip())
        if not clean_note:
            raise ValueError("note is empty after redaction")
        item = {"id": uuid.uuid4().hex[:12], "created_at": _timestamp(), "text": clean_note}
        notes.append(item)
        payload["updated_at"] = item["created_at"]
        directory = self._directory(root, create=False)
        self._atomic_write(self._context_path(directory, payload["name"]), payload)
        return item

    def show(self, repository: str | Path, *, name: str | None = None) -> dict[str, Any] | None:
        return self.load(repository, name=name)
