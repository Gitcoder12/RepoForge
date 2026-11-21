"""Fortress: bounded, failover-capable local workspaces for RepoForge agents.

Fortress does not promise infinite compute or storage. It provides multiple
independent workspace roots, capacity-aware allocation, stale-lease recovery,
and safe backpressure when every configured root is unavailable.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class WorkspaceUnavailable(RuntimeError):
    """Raised when no configured workspace backend can safely accept a lease."""


@dataclass(frozen=True)
class WorkspaceBackend:
    """One independent local workspace root."""

    name: str
    root: Path
    max_workspaces: int = 8
    min_free_bytes: int = 256 * 1024 * 1024

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("backend name must not be empty")
        if self.max_workspaces < 1:
            raise ValueError("max_workspaces must be at least 1")
        if self.min_free_bytes < 0:
            raise ValueError("min_free_bytes cannot be negative")


class WorkspaceLease:
    """A single isolated workspace. Use as a context manager."""

    def __init__(self, pool: "Fortress", backend: WorkspaceBackend, path: Path) -> None:
        self._pool = pool
        self.backend = backend
        self.path = path
        self.lease_id = path.name
        self._released = False

    def heartbeat(self) -> None:
        """Refresh the lease timestamp so recovery does not reclaim active work."""
        if self._released:
            raise RuntimeError("cannot heartbeat a released workspace")
        self._pool._write_lease(self.path, self.lease_id)

    def release(self, *, preserve: bool = False) -> None:
        """Release the workspace; preserve=True leaves its contents for inspection."""
        if self._released:
            return
        self._pool._release(self, preserve=preserve)
        self._released = True

    def __enter__(self) -> "WorkspaceLease":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()


class Fortress:
    """Capacity-aware workspace pool with ordered backend failover.

    Roots must be dedicated to Fortress. Only directories containing the
    Fortress lease marker are eligible for stale cleanup or deletion.
    """

    LEASE_FILE = ".fortress-lease.json"

    def __init__(
        self,
        backends: Iterable[WorkspaceBackend],
        *,
        stale_after_seconds: int = 6 * 60 * 60,
        wait_poll_seconds: float = 0.25,
    ) -> None:
        self.backends = tuple(backends)
        if not self.backends:
            raise ValueError("at least one workspace backend is required")
        if len({backend.name for backend in self.backends}) != len(self.backends):
            raise ValueError("workspace backend names must be unique")
        if stale_after_seconds < 1:
            raise ValueError("stale_after_seconds must be positive")
        if wait_poll_seconds <= 0:
            raise ValueError("wait_poll_seconds must be positive")
        self.stale_after_seconds = stale_after_seconds
        self.wait_poll_seconds = wait_poll_seconds
        self._condition = threading.Condition()
        self._active: set[Path] = set()
        self._next_backend = 0

    def acquire(
        self,
        task_id: str,
        *,
        timeout: float = 0,
    ) -> WorkspaceLease:
        """Acquire a fresh workspace, waiting up to timeout for capacity."""
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        if timeout < 0:
            raise ValueError("timeout cannot be negative")
        deadline = time.monotonic() + timeout
        last_errors: list[str] = []
        while True:
            lease = self._try_acquire(task_id.strip(), last_errors)
            if lease is not None:
                return lease
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                detail = "; ".join(last_errors) or "all backends are at capacity"
                raise WorkspaceUnavailable(f"Fortress has no available workspace: {detail}")
            with self._condition:
                self._condition.wait(min(self.wait_poll_seconds, remaining))

    def _try_acquire(
        self,
        task_id: str,
        errors: list[str],
    ) -> WorkspaceLease | None:
        count = len(self.backends)
        for offset in range(count):
            index = (self._next_backend + offset) % count
            backend = self.backends[index]
            try:
                root = backend.root.expanduser().resolve()
                root.mkdir(parents=True, exist_ok=True)
                self._reclaim_stale(backend, root)
                usage = shutil.disk_usage(root)
                if usage.free < backend.min_free_bytes:
                    errors.append(f"{backend.name}: insufficient free disk space")
                    continue
                entries = [p for p in root.iterdir() if p.is_dir() and p.name.startswith("lease-")]
                with self._condition:
                    if len(entries) >= backend.max_workspaces:
                        errors.append(f"{backend.name}: workspace capacity reached")
                        continue
                    path = Path(tempfile.mkdtemp(prefix="lease-", dir=root)).resolve()
                    path.relative_to(root)
                    self._active.add(path)
                lease_id = uuid.uuid4().hex
                self._write_lease(path, lease_id, task_id)
                self._next_backend = (index + 1) % count
                return WorkspaceLease(self, backend, path)
            except (OSError, ValueError) as exc:
                errors.append(f"{backend.name}: {type(exc).__name__}: {exc}")
        return None

    def _write_lease(self, path: Path, lease_id: str, task_id: str = "") -> None:
        marker = path / self.LEASE_FILE
        payload = {
            "lease_id": lease_id,
            "task_id": task_id,
            "heartbeat": time.time(),
            "pid": __import__("os").getpid(),
        }
        temporary = marker.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload), encoding="utf-8")
        temporary.replace(marker)

    def _reclaim_stale(self, backend: WorkspaceBackend, root: Path) -> None:
        now = time.time()
        with self._condition:
            active = set(self._active)
        for candidate in root.iterdir():
            if not candidate.is_dir() or not candidate.name.startswith("lease-"):
                continue
            if candidate.resolve() in active:
                continue
            marker = candidate / self.LEASE_FILE
            try:
                data = json.loads(marker.read_text(encoding="utf-8"))
                heartbeat = float(data["heartbeat"])
                if now - heartbeat > self.stale_after_seconds:
                    shutil.rmtree(candidate)
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
                # Unmarked or malformed directories are never deleted automatically.
                continue

    def _release(self, lease: WorkspaceLease, *, preserve: bool) -> None:
        path = lease.path.resolve()
        root = lease.backend.root.expanduser().resolve()
        path.relative_to(root)
        with self._condition:
            self._active.discard(path)
            if not preserve:
                marker = path / self.LEASE_FILE
                if marker.is_file():
                    try:
                        data = json.loads(marker.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        data = {}
                    if data.get("lease_id") == lease.lease_id:
                        shutil.rmtree(path)
            self._condition.notify_all()
