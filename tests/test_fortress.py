"""Tests for Fortress workspace allocation and cleanup."""

import json
import time
from pathlib import Path

import pytest

from repoforge.fortress import (
    Fortress,
    WorkspaceBackend,
    WorkspaceUnavailable,
)


def test_acquire_creates_isolated_workspace_and_release_cleans_it(tmp_path):
    pool = Fortress([WorkspaceBackend("primary", tmp_path / "primary")])
    with pool.acquire("task-1") as lease:
        assert lease.path.is_dir()
        assert (lease.path / Fortress.LEASE_FILE).is_file()
        assert lease.path.parent == (tmp_path / "primary").resolve()
    assert not lease.path.exists()


def test_failover_uses_next_backend_when_first_root_is_unusable(tmp_path):
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("occupied", encoding="utf-8")
    fallback = tmp_path / "fallback"
    pool = Fortress(
        [
            WorkspaceBackend("unusable", blocked),
            WorkspaceBackend("fallback", fallback),
        ]
    )
    lease = pool.acquire("task-2")
    try:
        assert lease.backend.name == "fallback"
        assert lease.path.parent == fallback.resolve()
    finally:
        lease.release()


def test_capacity_exhaustion_fails_fast_without_overallocating(tmp_path):
    pool = Fortress([WorkspaceBackend("small", tmp_path, max_workspaces=1)])
    lease = pool.acquire("task-3")
    try:
        with pytest.raises(WorkspaceUnavailable, match="capacity"):
            pool.acquire("task-4")
    finally:
        lease.release()


def test_stale_marked_workspace_is_reclaimed(tmp_path):
    root = tmp_path / "pool"
    root.mkdir()
    stale = root / "lease-stale"
    stale.mkdir()
    (stale / Fortress.LEASE_FILE).write_text(
        json.dumps({"lease_id": "old", "heartbeat": time.time() - 1000}),
        encoding="utf-8",
    )
    pool = Fortress(
        [WorkspaceBackend("pool", root, max_workspaces=1)],
        stale_after_seconds=10,
    )
    lease = pool.acquire("task-5")
    try:
        assert not stale.exists()
        assert lease.path.exists()
    finally:
        lease.release()


def test_unmarked_directories_are_never_deleted(tmp_path):
    root = tmp_path / "pool"
    root.mkdir()
    user_data = root / "lease-user-data"
    user_data.mkdir()
    (user_data / "keep.txt").write_text("keep", encoding="utf-8")
    pool = Fortress([WorkspaceBackend("pool", root, max_workspaces=2)])
    lease = pool.acquire("task-6")
    try:
        assert (user_data / "keep.txt").read_text(encoding="utf-8") == "keep"
    finally:
        lease.release()


def test_invalid_backend_capacity_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="max_workspaces"):
        WorkspaceBackend("bad", tmp_path, max_workspaces=0)
