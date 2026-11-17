"""Tests for RepoForge's Blacksmith and Megazord workflows."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from repoforge.blacksmith import Blacksmith
from repoforge.cli import app
from repoforge.megazord import MegazordEngine


def test_blacksmith_inspects_repo_and_explains_rank_dimensions(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_demo.py").write_text("def test_demo():\n    assert True\n", encoding="utf-8")

    report = Blacksmith(tmp_path).inspect()

    assert report["name"] == tmp_path.name
    assert report["signals"]["readme"] is True
    assert report["signals"]["tests"] is True
    assert report["rank"]["maximum"] == 100
    assert report["rank"]["dimensions"]["documentation"] == 12
    assert "Python" in report["languages"]


def test_blacksmith_excludes_virtualenv_git_and_symlink_escape(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Safe\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "fake.py").write_text("secret", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "environment.py").write_text("secret", encoding="utf-8")
    outside = tmp_path.parent / "outside-blacksmith.py"
    outside.write_text("outside", encoding="utf-8")
    (tmp_path / "escape.py").symlink_to(outside)

    report = Blacksmith(tmp_path).inspect()

    assert report["files_scanned"] == 1
    assert report["languages"] == {}


def test_blacksmith_dry_run_never_changes_files(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")

    result = Blacksmith(tmp_path).run()

    assert result["mode"] == "dry_run"
    assert result["applied"] == []
    assert result["before"]["rank"]["score"] == result["after"]["rank"]["score"]
    assert not (tmp_path / ".gitignore").exists()
    assert any(item["path"] == ".gitignore" for item in result["repair_plan"])


def test_blacksmith_apply_only_creates_missing_gitignore_and_reports_rank_delta(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    before = Blacksmith(tmp_path).inspect()["rank"]["score"]

    result = Blacksmith(tmp_path).run(apply_fixes=True)

    assert (tmp_path / ".gitignore").is_file()
    assert result["applied"] == [{"path": ".gitignore", "status": "created"}]
    assert result["before"]["rank"]["score"] == before
    assert result["after"]["rank"]["score"] == before + 5
    assert result["rank_change"] == 5


def test_blacksmith_never_overwrites_existing_gitignore(tmp_path: Path):
    existing = tmp_path / ".gitignore"
    existing.write_text("custom-ignore-rule\n", encoding="utf-8")

    result = Blacksmith(tmp_path).run(apply_fixes=True)

    assert existing.read_text(encoding="utf-8") == "custom-ignore-rule\n"
    assert result["applied"] == []


def test_blacksmith_rejects_non_directory_and_invalid_scan_limit(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("text", encoding="utf-8")

    with pytest.raises(ValueError, match="existing directory"):
        Blacksmith(file_path)
    with pytest.raises(ValueError, match="max_files"):
        Blacksmith(tmp_path, max_files=0)


def _make_repo(path: Path, name: str, readme: str, manifest: str = "[project]\nname='demo'\n"):
    path.mkdir()
    (path / "README.md").write_text(readme, encoding="utf-8")
    (path / "pyproject.toml").write_text(manifest, encoding="utf-8")
    (path / "main.py").write_text("# implementation\n", encoding="utf-8")


def test_megazord_finds_complementary_ai_and_evaluation_repositories(tmp_path: Path):
    ai = tmp_path / "model-lab"
    evaluation = tmp_path / "evaluation-suite"
    _make_repo(
        ai,
        "model-lab",
        "# Model Lab\nMachine learning models and data pipeline experiments.",
    )
    _make_repo(
        evaluation,
        "evaluation-suite",
        "# Evaluation Suite\nBenchmark and evaluation harness for model quality.",
    )

    before_files = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    result = MegazordEngine().suggest([ai, evaluation])

    assert result["mode"] == "recommend_only"
    assert result["pairings_evaluated"] == 1
    suggestion = result["suggestions"][0]
    assert suggestion["fit_score"] > 0
    assert any(
        "evaluation" in item["capabilities"] and "ai_ml" in item["capabilities"]
        for item in suggestion["complementarity"]
    )
    after_files = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    assert before_files == after_files


def test_megazord_rejects_duplicate_or_too_few_repositories(tmp_path: Path):
    repo = tmp_path / "repo"
    _make_repo(repo, "repo", "# Backend API\nA REST API service.")

    with pytest.raises(ValueError, match="at least two"):
        MegazordEngine().suggest([repo])
    with pytest.raises(ValueError, match="duplicate"):
        MegazordEngine().suggest([repo, repo])
    with pytest.raises(ValueError, match="top_k"):
        MegazordEngine().suggest([repo, tmp_path], top_k=0)


def test_megazord_rejects_missing_repository_paths(tmp_path: Path):
    existing = tmp_path / "one"
    _make_repo(existing, "one", "# Project")
    with pytest.raises(ValueError, match="existing directory"):
        MegazordEngine().suggest([existing, tmp_path / "missing"])


def test_blacksmith_does_not_mistake_latest_filename_for_test_coverage(tmp_path: Path):
    (tmp_path / "latest.py").write_text("VALUE = 1\n", encoding="utf-8")

    report = Blacksmith(tmp_path).inspect()

    assert report["signals"]["tests"] is False
    assert "testing" not in report["capabilities"]


def test_blacksmith_scan_limit_is_not_truncated_when_exactly_full(tmp_path: Path):
    (tmp_path / "one.py").write_text("VALUE = 1\n", encoding="utf-8")
    report = Blacksmith(tmp_path, max_files=1).inspect()

    assert report["files_scanned"] == 1
    assert report["scan_truncated"] is False


def test_blacksmith_cli_returns_before_after_rank_json(tmp_path: Path):
    (tmp_path / "README.md").write_text("# CLI sample\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["blacksmith", str(tmp_path)])

    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["mode"] == "dry_run"
    assert report["before"]["rank"]["score"] == report["after"]["rank"]["score"]


def test_megazords_cli_returns_pairing_json(tmp_path: Path):
    first = tmp_path / "frontend-ui"
    second = tmp_path / "backend-api"
    _make_repo(first, "frontend-ui", "# React frontend UI")
    _make_repo(second, "backend-api", "# FastAPI backend REST API")

    result = CliRunner().invoke(app, ["megazords", str(first), str(second)])

    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["repositories_analyzed"] == 2
    assert report["pairings_evaluated"] == 1


def test_blacksmith_recognises_go_and_javascript_test_file_conventions(tmp_path: Path):
    (tmp_path / "foo_test.go").write_text("package demo\n", encoding="utf-8")
    report = Blacksmith(tmp_path).inspect()

    assert report["signals"]["tests"] is True
    assert "testing" in report["capabilities"]


def test_blacksmith_does_not_infer_robotics_from_ros_substring(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Across the roadmap\n", encoding="utf-8")
    report = Blacksmith(tmp_path).inspect()

    assert "robotics" not in report["capabilities"]


def test_blacksmith_infers_robotics_from_ros_token(tmp_path: Path):
    (tmp_path / "README.md").write_text("# ROS integration\n", encoding="utf-8")
    report = Blacksmith(tmp_path).inspect()

    assert "robotics" in report["capabilities"]


def test_blacksmith_marks_scan_incomplete_on_walk_error(tmp_path: Path, monkeypatch):
    import repoforge.blacksmith as blacksmith_module

    def failing_walk(root, *, topdown, followlinks, onerror):
        onerror(PermissionError("directory unreadable"))
        yield str(root), [], []

    monkeypatch.setattr(blacksmith_module.os, "walk", failing_walk)
    report = Blacksmith(tmp_path).inspect()

    assert report["scan_incomplete"] is True
    assert report["scan_truncated"] is False
    assert report["scan_errors"]
    assert any("scan incomplete" in item.casefold() for item in report["findings"])



def test_blacksmith_reports_truncated_scan_as_incomplete(tmp_path: Path):
    (tmp_path / "one.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "two.py").write_text("VALUE = 2\n", encoding="utf-8")

    report = Blacksmith(tmp_path, max_files=1).inspect()

    assert report["scan_truncated"] is True
    assert report["scan_incomplete"] is True
    assert any("scan incomplete" in item.casefold() for item in report["findings"])
