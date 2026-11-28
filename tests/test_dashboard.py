from pathlib import Path

import pytest

from repoforge.dashboard import (
    AGENT_FOCUSES,
    discover_repositories,
    filter_repositories,
    is_git_repository,
    run_local_agent_review,
)


def _make_repo(root: Path, name: str) -> Path:
    path = root / name
    path.mkdir(parents=True)
    (path / ".git").mkdir()
    (path / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    return path


def test_discover_repositories_finds_nested_git_worktrees(tmp_path: Path):
    first = _make_repo(tmp_path, "alpha")
    nested_parent = tmp_path / "clients"
    nested_parent.mkdir()
    second = _make_repo(nested_parent, "beta")
    (tmp_path / "node_modules").mkdir()
    _make_repo(tmp_path / "node_modules", "ignored")

    found = discover_repositories(tmp_path)

    expected = sorted(
        [first.resolve(), second.resolve()],
        key=lambda path: (path.name.casefold(), str(path).casefold()),
    )
    assert found == expected


def test_discover_returns_workspace_itself_when_it_is_a_repository(tmp_path: Path):
    (tmp_path / ".git").write_text("gitdir: ../worktrees/demo", encoding="utf-8")
    assert discover_repositories(tmp_path) == [tmp_path.resolve()]
    assert is_git_repository(tmp_path)


def test_discover_does_not_follow_symlink_directories(tmp_path: Path):
    repo = _make_repo(tmp_path, "actual")
    link = tmp_path / "linked"
    try:
        link.symlink_to(repo, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is unavailable on this platform")

    found = discover_repositories(tmp_path)

    assert found == [repo.resolve()]


def test_discover_respects_depth_and_result_limits(tmp_path: Path):
    for name in ["one", "two", "three"]:
        _make_repo(tmp_path, name)
    assert len(discover_repositories(tmp_path, max_results=2)) == 2
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    _make_repo(deep, "too-deep")
    assert all(path.name != "too-deep" for path in discover_repositories(tmp_path, max_depth=1))


def test_repository_search_filters_name_and_path(tmp_path: Path):
    first = _make_repo(tmp_path, "ARK")
    second = _make_repo(tmp_path, "RepoForge")
    assert filter_repositories([first, second], "ark") == [first]
    assert filter_repositories([first, second], "repoforge") == [second]
    assert filter_repositories([first, second], "") == [first, second]


def test_agent_catalog_is_searchable_and_has_named_focus_prompts():
    assert {"Architect", "Testing", "Security", "Code Review"} <= set(AGENT_FOCUSES)
    assert all(item["description"] and item["request"] for item in AGENT_FOCUSES.values())


def test_agent_focus_rejects_unknown_roles(tmp_path: Path):
    with pytest.raises(ValueError, match="Unknown agent focus"):
        run_local_agent_review(tmp_path, "Unlisted Agent")


def test_agent_review_rejects_non_string_focus(tmp_path: Path):
    with pytest.raises(ValueError, match="Unknown agent focus"):
        run_local_agent_review(tmp_path, ["Security"])


def test_agent_review_rejects_non_string_additional_request(tmp_path: Path):
    with pytest.raises(ValueError, match="additional request must be text"):
        run_local_agent_review(tmp_path, "Security", request=123)
