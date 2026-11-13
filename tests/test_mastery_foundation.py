from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from repoforge.cli import app
from repoforge.providers.factory import create_provider
from repoforge.providers.mock import MockProvider
from repoforge.repository import (
    _github_remote,
    collect_repository_context,
    resolve_repository,
)
from repoforge.turbo import apply_edit, propose_edit


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def test_github_reference_parser_accepts_url_owner_repo_and_ssh() -> None:
    assert _github_remote("Gitcoder12/RepoForge") == ("Gitcoder12", "RepoForge")
    assert _github_remote("https://github.com/Gitcoder12/RepoForge") == (
        "Gitcoder12",
        "RepoForge",
    )
    assert _github_remote("git@github.com:Gitcoder12/RepoForge.git") == (
        "Gitcoder12",
        "RepoForge",
    )


def test_github_reference_parser_rejects_non_github_host() -> None:
    with pytest.raises(ValueError, match="Only HTTPS GitHub URLs"):
        _github_remote("https://example.com/owner/repo")


def test_resolve_repository_accepts_local_git_directory(tmp_path: Path) -> None:
    repository = init_repo(tmp_path / "project")
    result = resolve_repository(str(repository))
    assert result.path == repository.resolve()
    assert result.cloned is False


def test_resolve_repository_rejects_non_git_directory(tmp_path: Path) -> None:
    directory = tmp_path / "not-a-repo"
    directory.mkdir()
    with pytest.raises(ValueError, match="not a Git repository"):
        resolve_repository(str(directory))


def test_collect_context_excludes_secrets_and_symlinks(tmp_path: Path) -> None:
    repository = init_repo(tmp_path / "project")
    (repository / "README.md").write_text("# Project\n", encoding="utf-8")
    (repository / "app.py").write_text("print('safe')\n", encoding="utf-8")
    (repository / ".env").write_text("API_KEY=do-not-read\n", encoding="utf-8")
    outside = tmp_path / "outside.py"
    outside.write_text("secret = True\n", encoding="utf-8")
    (repository / "escape.py").symlink_to(outside)

    context = collect_repository_context(repository)

    assert "README.md" in context["files"]
    assert "app.py" in context["files"]
    assert ".env" not in context["files"]
    assert "escape.py" not in context["files"]
    assert "Python" in context["languages"]


def test_context_limits_are_enforced(tmp_path: Path) -> None:
    repository = init_repo(tmp_path / "project")
    (repository / "large.py").write_text("x = 1\n" * 100, encoding="utf-8")
    context = collect_repository_context(
        repository, max_files=1, max_file_chars=20, max_total_chars=30
    )
    assert len(context["files"]) <= 1
    assert sum(len(value) for value in context["files"].values()) <= 60


def test_openrouter_factory_uses_openrouter_endpoint_and_model(monkeypatch) -> None:
    captured = {}

    class FakeProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "vendor/model-name")
    with patch("repoforge.providers.factory.OpenAICompatibleProvider", FakeProvider):
        provider = create_provider("openrouter")

    assert isinstance(provider, FakeProvider)
    assert captured["api_key"] == "test-key"
    assert captured["model"] == "vendor/model-name"
    assert captured["base_url"] == "https://openrouter.ai/api/v1"


def test_openrouter_factory_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        create_provider("openrouter")


def test_provider_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported provider"):
        create_provider("unknown-provider")


def test_turbo_proposal_does_not_modify_file_until_apply(tmp_path: Path) -> None:
    repository = init_repo(tmp_path / "project")
    target = repository / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")

    proposal = propose_edit(repository, "app.py", "Change value to 2", MockProvider("value = 2\n"))

    assert target.read_text(encoding="utf-8") == "value = 1\n"
    assert "value = 2" in proposal.diff
    backup = apply_edit(proposal)
    assert target.read_text(encoding="utf-8") == "value = 2\n"
    assert backup.is_file()
    assert backup.read_text(encoding="utf-8") == "value = 1\n"


def test_turbo_rejects_invalid_python_syntax(tmp_path: Path) -> None:
    repository = init_repo(tmp_path / "project")
    (repository / "app.py").write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid Python syntax"):
        propose_edit(repository, "app.py", "Break it", MockProvider("def broken(:\n"))


def test_turbo_refuses_secrets_and_path_traversal(tmp_path: Path) -> None:
    repository = init_repo(tmp_path / "project")
    (repository / "app.py").write_text("value = 1\n", encoding="utf-8")
    (repository / ".env").write_text("API_KEY=secret\n", encoding="utf-8")

    with pytest.raises(ValueError, match="secret or credential"):
        propose_edit(repository, ".env", "Edit this", MockProvider("changed"))
    with pytest.raises(ValueError, match="prohibited path"):
        propose_edit(repository, "../outside.py", "Edit this", MockProvider("changed"))


def test_turbo_detects_concurrent_file_changes(tmp_path: Path) -> None:
    repository = init_repo(tmp_path / "project")
    target = repository / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    proposal = propose_edit(repository, "app.py", "Change value", MockProvider("value = 2\n"))
    target.write_text("value = 3\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="changed after proposal"):
        apply_edit(proposal)
    assert target.read_text(encoding="utf-8") == "value = 3\n"


def test_cli_exposes_repository_first_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "forge" in result.stdout
    assert "turbo" in result.stdout
    assert "inspect" in result.stdout
    assert "models" in result.stdout
