from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from repoforge.repobox import RepoBox, RepoBoxError


def make_git_repo(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "RepoBox Test"],
        check=True,
    )
    (path / "README.md").write_text("original\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-qm", "initial"],
        check=True,
    )
    return path


def test_import_clones_repository_without_modifying_source(tmp_path: Path) -> None:
    source = make_git_repo(tmp_path / "source")
    box = RepoBox(tmp_path / "box")

    record = box.import_repository(source)

    assert Path(record["managed_path"]).is_dir()
    assert (source / "README.md").read_text(encoding="utf-8") == "original\n"
    assert len(box.list_repositories()) == 1
    assert record["head"] == subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()


def test_workspace_is_a_detached_worktree_and_source_stays_untouched(
    tmp_path: Path,
) -> None:
    source = make_git_repo(tmp_path / "source")
    box = RepoBox(tmp_path / "box")
    record = box.import_repository(source)

    result = box.create_workspace(record["id"], "repair-001")
    workspace = Path(result["workspace"])

    assert workspace.is_dir()
    assert subprocess.check_output(
        ["git", "-C", str(workspace), "rev-parse", "--is-inside-work-tree"],
        text=True,
    ).strip() == "true"
    (workspace / "README.md").write_text("candidate change\n", encoding="utf-8")
    assert (source / "README.md").read_text(encoding="utf-8") == "original\n"
    assert (Path(record["managed_path"]) / "README.md").read_text(
        encoding="utf-8"
    ) == "original\n"


def test_import_rejects_non_git_directory(tmp_path: Path) -> None:
    source = tmp_path / "not-a-repository"
    source.mkdir()
    box = RepoBox(tmp_path / "box")

    with pytest.raises(RepoBoxError):
        box.import_repository(source)


def test_workspace_rejects_path_traversal(tmp_path: Path) -> None:
    source = make_git_repo(tmp_path / "source")
    box = RepoBox(tmp_path / "box")
    record = box.import_repository(source)

    with pytest.raises(ValueError, match="task id"):
        box.create_workspace(record["id"], "../outside")


def test_workspace_rejects_unknown_repository(tmp_path: Path) -> None:
    box = RepoBox(tmp_path / "box")

    with pytest.raises(KeyError, match="unknown RepoBox"):
        box.create_workspace("missing", "task-1")


def test_workspace_does_not_overwrite_existing_task_workspace(tmp_path: Path) -> None:
    source = make_git_repo(tmp_path / "source")
    box = RepoBox(tmp_path / "box")
    record = box.import_repository(source)
    box.create_workspace(record["id"], "same-task")

    with pytest.raises(FileExistsError):
        box.create_workspace(record["id"], "same-task")
