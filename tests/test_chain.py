"""Tests for the multi-repository HookChain and LangFix bridge."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from repoforge.chain import HookChain
from repoforge.cli import app
from repoforge.langfix_bridge import LangFixBridge


def _repo(path: Path, *, rust: bool = False, readme: str = "# Demo\n") -> Path:
    path.mkdir()
    (path / "README.md").write_text(readme, encoding="utf-8")
    if rust:
        (path / "src").mkdir()
        (path / "src" / "main.rs").write_text(
            'fn main() { println!("hello"); }\n', encoding="utf-8"
        )
        (path / "Cargo.toml").write_text(
            '[package]\nname = "demo"\nversion = "0.1.0"\nedition = "2021"\n',
            encoding="utf-8",
        )
    else:
        (path / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    return path


def test_rust_blacksmith_repair_plan_adds_stack_specific_ignore_rules(tmp_path: Path):
    repo = _repo(tmp_path / "rust-app", rust=True)

    chain = HookChain()
    report = chain.inspect([repo])
    repair = next(item for item in report["selection_items"] if item["kind"] == "repair")
    assert repair["safe_to_apply"] is True
    applied = chain.apply_selected(report, [repair["id"]])

    ignore = (repo / ".gitignore").read_text(encoding="utf-8")
    assert applied["applied_count"] == 1
    assert "/target/" in ignore
    assert "**/*.rs.bk" in ignore
    assert "Cargo.lock" not in ignore


def test_hook_chain_emits_lifecycle_events_in_order(tmp_path: Path):
    one = _repo(tmp_path / "one")
    two = _repo(tmp_path / "two")
    seen: list[str] = []
    chain = HookChain()
    chain.register_hook(
        "repository.inspect.completed",
        lambda payload: seen.append(payload["repo_id"]),
    )
    report = chain.inspect([one, two])

    assert seen == ["r1-one", "r2-two"]
    events = [item["event"] for item in report["hook_trace"]]
    assert events[0] == "chain.started"
    assert events.count("repository.inspect.completed") == 2
    assert "megazords.completed" in events
    assert events[-1] == "chain.completed"


def test_hook_errors_are_recorded_without_triggering_repairs(tmp_path: Path):
    repo = _repo(tmp_path / "one")
    chain = HookChain()

    def broken_hook(payload):
        raise RuntimeError("observer broke")

    chain.register_hook("repository.inspect.completed", broken_hook)
    report = chain.inspect([repo])

    assert any(item["event"] == "hook.error" for item in report["hook_trace"])
    assert not (repo / ".gitignore").exists()
    assert report["safety"]["target_files_modified"] is False


def test_selection_board_never_applies_upgrade_or_megazord_items(tmp_path: Path):
    one = _repo(tmp_path / "frontend", readme="# React frontend UI\n")
    two = _repo(tmp_path / "backend", readme="# FastAPI backend REST API\n")
    chain = HookChain()
    report = chain.inspect([one, two])

    repair = next(
        item
        for item in report["selection_items"]
        if item["kind"] == "repair" and item["repository"] == "frontend"
    )
    upgrade = next(item for item in report["selection_items"] if item["kind"] == "upgrade")
    complement = next(item for item in report["selection_items"] if item["kind"] == "complement")
    outcomes = chain.apply_selected(report, [repair["id"], upgrade["id"], complement["id"]])

    assert outcomes["applied_count"] == 1
    assert outcomes["review_only_count"] == 2
    assert (one / ".gitignore").is_file()
    assert not (two / ".gitignore").exists()


def test_chain_rejects_unknown_or_duplicate_paths(tmp_path: Path):
    repo = _repo(tmp_path / "one")
    chain = HookChain()
    with pytest.raises(ValueError, match="duplicate"):
        chain.inspect([repo, repo])
    with pytest.raises(ValueError, match="unknown selection"):
        chain.apply_selected({"engine": "RepoForge HookChain", "selection_items": []}, ["missing"])


def test_langfix_bridge_reports_missing_cli_without_touching_target(tmp_path: Path):
    repo = _repo(tmp_path / "rust-app", rust=True)
    with patch("repoforge.langfix_bridge.shutil.which", return_value=None):
        result = LangFixBridge().scan(repo)

    assert result["status"] == "unavailable"
    assert not (repo / ".langfix_cache.json").exists()


def test_langfix_bridge_runs_preview_only_in_temporary_working_directory(tmp_path: Path):
    repo = _repo(tmp_path / "rust-app", rust=True)
    stdout = json.dumps(
        {
            "average_score": 90,
            "vibe": "GOOD",
            "files": [{"file": str(repo / "src" / "main.rs"), "score": 90, "vibe": "GOOD"}],
        }
    )
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["cwd"] = kwargs["cwd"]
        captured["shell"] = kwargs["shell"]
        return subprocess.CompletedProcess(command, 0, stdout, "")

    with (
        patch("repoforge.langfix_bridge.shutil.which", return_value="/usr/local/bin/langfix"),
        patch("repoforge.langfix_bridge.subprocess.run", side_effect=fake_run),
    ):
        result = LangFixBridge().scan(repo)

    assert result["status"] == "completed"
    assert result["languages"] == {"rust": 1}
    assert "--fix" not in captured["command"]
    assert captured["shell"] is False
    assert captured["cwd"] != str(repo)
    assert not (repo / ".langfix_cache.json").exists()


def test_langfix_bridge_handles_invalid_json_report(tmp_path: Path):
    repo = _repo(tmp_path / "repo")
    fake = subprocess.CompletedProcess(["langfix"], 0, "not-json", "")
    with (
        patch("repoforge.langfix_bridge.shutil.which", return_value="langfix"),
        patch("repoforge.langfix_bridge.subprocess.run", return_value=fake),
    ):
        result = LangFixBridge().scan(repo)

    assert result["status"] == "invalid_report"


def test_chain_cli_select_safe_applies_only_safe_repairs(tmp_path: Path):
    repo = _repo(tmp_path / "rust-cli", rust=True)
    output = tmp_path / "chain-report.json"
    result = CliRunner().invoke(
        app,
        ["chain", str(repo), "--select", "safe", "--apply-safe", "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["selection"]["selected_ids"]
    assert report["selection"]["applied"]["applied_count"] == 1
    assert "/target/" in (repo / ".gitignore").read_text(encoding="utf-8")


def test_chain_cli_rejects_report_inside_scanned_repo(tmp_path: Path):
    repo = _repo(tmp_path / "repo")
    result = CliRunner().invoke(
        app,
        ["chain", str(repo), "--output", str(repo / "report.json")],
    )
    assert result.exit_code != 0
    assert "outside every scanned repository" in result.output
