import os
import subprocess
from pathlib import Path

import pytest

from repoforge.action_runner import ActionRunner


def _git_repo(path: Path) -> None:
    subprocess.run(
        ["git", "init", "-b", "feature/action-runner-tests"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "config", "user.email", "tests@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "RepoForge Tests"], cwd=path, check=True)
    (path / ".baseline").write_text("baseline", encoding="utf-8")
    subprocess.run(["git", "add", ".baseline"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=path, check=True, capture_output=True)


def test_create_action_writes_inside_repository(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    runner = ActionRunner(str(tmp_path))
    result = runner.run(
        [{"type": "create", "file": "docs/notes.md", "content": "safe"}],
        approved_paths={"docs/notes.md"},
    )

    assert result["completed"] == 1
    assert (tmp_path / "docs" / "notes.md").read_text(encoding="utf-8") == "safe"


@pytest.mark.parametrize("filepath", ["../outside.txt", "/tmp/outside.txt"])
def test_write_rejects_paths_outside_repository(tmp_path: Path, filepath: str) -> None:
    _git_repo(tmp_path)
    runner = ActionRunner(str(tmp_path))
    result = runner.run([{"type": "create", "file": filepath, "content": "unsafe"}])

    assert result["completed"] == 0
    assert result["status"] == "blocked"
    assert result["errors"]
    assert not (tmp_path.parent / "outside.txt").exists()


def test_write_rejects_symlink_escape(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    outside = tmp_path.parent / "outside-dir"
    outside.mkdir()
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)
    subprocess.run(["git", "add", "linked"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "track symlink"], cwd=tmp_path, check=True, capture_output=True
    )

    runner = ActionRunner(str(tmp_path))
    result = runner.run(
        [{"type": "create", "file": "linked/payload.txt", "content": "unsafe"}],
        approved_paths={"linked/payload.txt"},
    )

    assert result["completed"] == 0
    assert result["status"] == "blocked"
    assert result["errors"]
    assert not (outside / "payload.txt").exists()


def test_create_does_not_overwrite_existing_file(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    target = tmp_path / "important.txt"
    target.write_text("original", encoding="utf-8")
    subprocess.run(["git", "add", "important.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "track important file"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    result = ActionRunner(str(tmp_path)).run(
        [{"type": "create", "file": "important.txt", "content": "replacement"}],
        approved_paths={"important.txt"},
    )

    assert result["completed"] == 0
    assert result["status"] == "blocked"
    assert target.read_text(encoding="utf-8") == "original"


def test_modify_requires_existing_file(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    result = ActionRunner(str(tmp_path)).run(
        [{"type": "modify", "file": "missing.txt", "content": "replacement"}],
        approved_paths={"missing.txt"},
    )

    assert result["completed"] == 0
    assert result["status"] == "blocked"
    assert result["errors"]



def test_write_rejects_internal_symlink_alias(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    source = tmp_path / "source.txt"
    source.write_text("original", encoding="utf-8")
    alias = tmp_path / "alias.txt"
    try:
        alias.symlink_to(source)
    except OSError:
        pytest.skip("Symlink creation is unavailable on this platform")
    subprocess.run(["git", "add", "source.txt", "alias.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "track internal symlink"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    result = ActionRunner(str(tmp_path)).run(
        [{"type": "modify", "file": "alias.txt", "content": "changed"}],
        approved_paths={"alias.txt"},
    )

    assert result["status"] == "blocked"
    assert source.read_text(encoding="utf-8") == "original"


def test_write_rejects_hard_link_target(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outside.write_text("original", encoding="utf-8")
    linked = tmp_path / "linked.txt"
    try:
        os.link(outside, linked)
    except OSError:
        pytest.skip("Hard-link creation is unavailable on this platform")
    subprocess.run(["git", "add", "linked.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "track hard link"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    result = ActionRunner(str(tmp_path)).run(
        [{"type": "modify", "file": "linked.txt", "content": "changed"}],
        approved_paths={"linked.txt"},
    )

    assert result["status"] == "blocked"
    assert outside.read_text(encoding="utf-8") == "original"


def test_windows_separators_resolve_to_repository_relative_paths(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    runner = ActionRunner(str(tmp_path))
    result = runner.run(
        [{"type": "create", "file": "docs\\notes.md", "content": "safe"}],
        approved_paths={"docs/notes.md"},
    )

    assert result["status"] == "completed"
    assert (tmp_path / "docs" / "notes.md").read_text(encoding="utf-8") == "safe"
