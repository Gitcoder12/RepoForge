from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from repoforge import repobox as repobox_module
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
    assert (
        record["head"]
        == subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
        ).strip()
    )


def test_workspace_is_a_detached_worktree_and_source_stays_untouched(
    tmp_path: Path,
) -> None:
    source = make_git_repo(tmp_path / "source")
    box = RepoBox(tmp_path / "box")
    record = box.import_repository(source)

    result = box.create_workspace(record["id"], "repair-001")
    workspace = Path(result["workspace"])

    assert workspace.is_dir()
    assert (
        subprocess.check_output(
            ["git", "-C", str(workspace), "rev-parse", "--is-inside-work-tree"],
            text=True,
        ).strip()
        == "true"
    )
    (workspace / "README.md").write_text("candidate change\n", encoding="utf-8")
    assert (source / "README.md").read_text(encoding="utf-8") == "original\n"
    assert (
        Path(record["managed_path"]) / "README.md"
    ).read_text(encoding="utf-8") == "original\n"


def test_import_rejects_non_git_directory(tmp_path: Path) -> None:
    source = tmp_path / "not-a-repository"
    source.mkdir()
    box = RepoBox(tmp_path / "box")

    with pytest.raises(RepoBoxError):
        box.import_repository(source)


def test_import_rejects_dirty_source_without_omitting_user_files(
    tmp_path: Path,
) -> None:
    source = make_git_repo(tmp_path / "source")
    untracked = source / "important-local-notes.txt"
    untracked.write_text("keep this file\n", encoding="utf-8")
    box = RepoBox(tmp_path / "box")

    with pytest.raises(RepoBoxError, match="uncommitted or untracked"):
        box.import_repository(source)

    assert untracked.read_text(encoding="utf-8") == "keep this file\n"
    assert box.list_repositories() == []
    assert list(box.repositories_dir.iterdir()) == []


def test_failed_clone_removes_partial_managed_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = make_git_repo(tmp_path / "source")
    box = RepoBox(tmp_path / "box")
    original_git = repobox_module._git

    def fail_after_creating_destination(
        args: list[str], *, cwd: Path | None = None
    ) -> str:
        if args and args[0] == "clone":
            Path(args[-1]).mkdir()
            raise RepoBoxError("simulated clone failure")
        return original_git(args, cwd=cwd)

    monkeypatch.setattr(repobox_module, "_git", fail_after_creating_destination)

    with pytest.raises(RepoBoxError, match="simulated clone failure"):
        box.import_repository(source)

    assert box.list_repositories() == []
    assert list(box.repositories_dir.iterdir()) == []


def test_concurrent_imports_do_not_lose_manifest_records(tmp_path: Path) -> None:
    source = make_git_repo(tmp_path / "source")
    box = RepoBox(tmp_path / "box")

    with ThreadPoolExecutor(max_workers=2) as executor:
        records = list(executor.map(lambda _: box.import_repository(source), range(2)))

    registered = box.list_repositories()
    assert len(records) == 2
    assert len(registered) == 2
    assert {record["id"] for record in records} == {
        record["id"] for record in registered
    }


def test_manifest_rejects_managed_paths_outside_storage(tmp_path: Path) -> None:
    source = make_git_repo(tmp_path / "source")
    box = RepoBox(tmp_path / "box")
    record = box.import_repository(source)
    manifest = box.manifest_path
    data = box._read_manifest()
    data["repositories"][0]["managed_path"] = str(tmp_path / "outside")
    manifest.write_text(__import__("json").dumps(data), encoding="utf-8")

    with pytest.raises(RepoBoxError, match="outside managed storage"):
        box.list_repositories()

    assert Path(record["managed_path"]).is_dir()


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
