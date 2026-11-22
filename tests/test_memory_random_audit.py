"""Tests for isolated project memory and read-only random repository audits."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from repoforge.cli import app
from repoforge.memory import MemoryContextStore
from repoforge.random_audit import discover_repositories, run_random_audit


def _make_git_repo(path: Path, *, language: str = "python") -> Path:
    path.mkdir(parents=True)
    (path / ".git").mkdir()
    (path / "README.md").write_text(f"# {path.name}\n", encoding="utf-8")
    if language == "python":
        (path / "pyproject.toml").write_text("[project]\nname = 'sample'\n", encoding="utf-8")
        (path / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
        tests = path / "tests"
        tests.mkdir()
        (tests / "test_side_effect.py").write_text(
            "from pathlib import Path\n"
            "Path('EXECUTED_BY_REPOFORGE').write_text('bad')\n",
            encoding="utf-8",
        )
    elif language == "javascript":
        (path / "package.json").write_text(
            '{"name":"sample","scripts":{"test":"echo never-run"}}\n',
            encoding="utf-8",
        )
        (path / "src").mkdir()
        (path / "src" / "index.js").write_text("export const value = 1;\n", encoding="utf-8")
    return path


def test_empty_memory_store_is_a_valid_first_run(tmp_path: Path) -> None:
    repository = _make_git_repo(tmp_path / "repo")
    store = MemoryContextStore(tmp_path / "memory")

    assert store.load(repository) is None
    assert store.list_contexts(repository) == {
        "repository": str(repository.resolve()),
        "active": None,
        "contexts": [],
    }


def test_memory_contexts_are_isolated_per_repository_and_switch_independently(
    tmp_path: Path,
) -> None:
    first = _make_git_repo(tmp_path / "first")
    second = _make_git_repo(tmp_path / "second")
    store = MemoryContextStore(tmp_path / "memory")

    store.create(first, "backend")
    store.add_note(first, "Keep the REST API backwards compatible.")
    store.create(first, "research", switch=False)
    store.create(second, "robotics")
    store.add_note(second, "Use the simulator before touching hardware.")

    store.switch(first, "research")

    first_active = store.load(first)
    second_active = store.load(second)
    assert first_active is not None and first_active["name"] == "research"
    assert second_active is not None and second_active["name"] == "robotics"
    assert store.load(first, name="backend")["notes"][0]["text"] == (
        "Keep the REST API backwards compatible."
    )
    assert "backwards compatible" not in json.dumps(second_active)


def test_memory_notes_are_bounded_and_redact_obvious_secret_assignments(
    tmp_path: Path,
) -> None:
    repository = _make_git_repo(tmp_path / "repo")
    store = MemoryContextStore(tmp_path / "memory")
    store.create(repository, "audit")

    saved = store.add_note(repository, "Remember API_KEY=very-secret-value before release.")

    assert "very-secret-value" not in saved["text"]
    assert "[REDACTED]" in saved["text"]
    with pytest.raises(ValueError, match="context name"):
        store.create(repository, "../other-repo")
    with pytest.raises(ValueError, match="at most"):
        store.add_note(repository, "x" * 4_001)


def test_memory_does_not_fall_back_to_another_repository_context(tmp_path: Path) -> None:
    first = _make_git_repo(tmp_path / "first")
    second = _make_git_repo(tmp_path / "second")
    store = MemoryContextStore(tmp_path / "memory")
    store.create(first, "private-notes")
    store.add_note(first, "First repo only.")

    with pytest.raises(ValueError, match="does not exist for this repository"):
        store.load(second, name="private-notes")


def test_discovery_finds_nested_git_and_worktree_markers_without_following_symlinks(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    one = _make_git_repo(workspace / "one")
    two = workspace / "two"
    two.mkdir(parents=True)
    (two / ".git").write_text("gitdir: ../.git/worktrees/two\n", encoding="utf-8")
    ignored = workspace / "node_modules" / "not-a-repo"
    ignored.mkdir(parents=True)
    (ignored / ".git").mkdir()
    outside = _make_git_repo(tmp_path / "outside")
    (workspace / "linked").symlink_to(outside, target_is_directory=True)

    found = discover_repositories(workspace)

    assert found == sorted([one.resolve(), two.resolve()], key=lambda item: item.as_posix().casefold())


def test_random_audit_is_seeded_read_only_and_never_executes_tests(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    repositories = [
        _make_git_repo(workspace / "alpha"),
        _make_git_repo(workspace / "beta", language="javascript"),
        _make_git_repo(workspace / "gamma"),
    ]
    before = {
        str(path.relative_to(workspace)): path.read_bytes()
        for repository in repositories
        for path in repository.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }

    first = run_random_audit(workspace, count=2, seed=73)
    second = run_random_audit(workspace, count=2, seed=73)

    first_paths = [item["path"] for item in first["repositories"]]
    second_paths = [item["path"] for item in second["repositories"]]
    assert first_paths == second_paths
    assert first["seed"] == 73
    assert first["available_repositories"] == 3
    assert first["selected_count"] == 2
    assert first["mode"] == "static_read_only"
    assert first["repository_files_modified"] is False
    assert first["dictionary_files_written"] is False
    assert all(item["checks"]["test_discovery"]["execution_performed"] is False for item in first["repositories"])
    assert all(item["checks"]["codebase_index"]["persisted"] is False for item in first["repositories"])
    assert not any((repository / "EXECUTED_BY_REPOFORGE").exists() for repository in repositories)
    after = {
        str(path.relative_to(workspace)): path.read_bytes()
        for repository in repositories
        for path in repository.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    assert before == after


def test_random_audit_can_store_summary_in_separate_repo_contexts(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    first = _make_git_repo(workspace / "first")
    second = _make_git_repo(workspace / "second")
    store = MemoryContextStore(tmp_path / "memory")

    report = run_random_audit(
        workspace,
        count=2,
        seed=10,
        remember=True,
        memory_context="random-checks",
        memory_store=store,
    )

    assert report["selected_count"] == 2
    for repository in (first, second):
        saved = store.load(repository, name="random-checks")
        assert saved is not None
        assert len(saved["notes"]) == 1
        assert "Random audit snapshot" in saved["notes"][0]["text"]


def test_random_audit_cli_outputs_json_and_does_not_write_targets(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    repository = _make_git_repo(workspace / "repo")
    result = CliRunner().invoke(app, ["random-check", str(workspace), "--count", "1", "--seed", "5"])

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["selected_count"] == 1
    assert report["repositories"][0]["path"] == str(repository.resolve())
    assert not (repository / "repo_dictionary.json").exists()


def test_memory_store_refuses_to_write_inside_a_target_repository(tmp_path: Path) -> None:
    repository = _make_git_repo(tmp_path / "repo")
    store = MemoryContextStore(repository / ".repoforge")

    with pytest.raises(ValueError, match="outside the target repository"):
        store.create(repository, "must-not-write")

    assert not (repository / ".repoforge").exists()
