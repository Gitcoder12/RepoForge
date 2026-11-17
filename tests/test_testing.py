"""Tests for TestForge discovery and explicit execution safeguards."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from repoforge.testing import TestForge


def test_testforge_plans_python_tests_without_executing(tmp_path: Path, monkeypatch):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    def unexpected_run(*args, **kwargs):
        raise AssertionError("plan-only mode must not execute repository code")

    monkeypatch.setattr(subprocess, "run", unexpected_run)
    report = TestForge(tmp_path).run()

    assert report["mode"] == "plan_only"
    assert report["status"] == "planned"
    assert report["execution_is_sandboxed"] is False
    assert report["commands"][0]["ecosystem"] == "python"
    assert report["commands"][0]["command"][-2:] == ["pytest", "-q"]


def test_testforge_detects_go_and_javascript_test_commands(tmp_path: Path):
    (tmp_path / "go.mod").write_text("module example\n", encoding="utf-8")
    (tmp_path / "service_test.go").write_text("package example\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"scripts":{"test":"vitest run"}}', encoding="utf-8")
    (tmp_path / "app.test.ts").write_text("export {}\n", encoding="utf-8")

    commands = TestForge(tmp_path).plan()["commands"]

    assert {item["ecosystem"] for item in commands} == {"go", "javascript"}
    assert any(item["command"] == ["go", "test", "./..."] for item in commands)
    assert any(item["command"] == ["npm", "test"] for item in commands)


def test_testforge_returns_no_tests_for_empty_repository(tmp_path: Path):
    report = TestForge(tmp_path).plan()

    assert report["status"] == "no_tests_detected"
    assert report["commands"] == []


def test_testforge_executes_only_after_explicit_opt_in(tmp_path: Path, monkeypatch):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="1 passed", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    report = TestForge(tmp_path).run(execute=True, timeout=15)

    assert report["mode"] == "execute"
    assert report["status"] == "passed"
    assert report["results"][0]["status"] == "passed"
    assert captured["shell"] is False
    assert captured["timeout"] == 15
    assert captured["cwd"] == tmp_path


def test_testforge_reports_test_failures(tmp_path: Path, monkeypatch):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, stdout="1 failed", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    report = TestForge(tmp_path).run(execute=True)

    assert report["status"] == "failed"
    assert report["results"][0]["status"] == "failed"
    assert report["results"][0]["return_code"] == 1


def test_testforge_reports_timeout_and_missing_runner(tmp_path: Path, monkeypatch):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    def timeout_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"], output="still running")

    monkeypatch.setattr(subprocess, "run", timeout_run)
    report = TestForge(tmp_path).run(execute=True, timeout=2)

    assert report["status"] == "failed"
    assert report["results"][0]["status"] == "timed_out"


def test_testforge_rejects_invalid_timeout_and_execute_type(tmp_path: Path):
    runner = TestForge(tmp_path)

    with pytest.raises(ValueError, match="timeout"):
        runner.run(timeout=0)
    with pytest.raises(ValueError, match="execute"):
        runner.run(execute="yes")


def test_testforge_strips_common_credentials_from_child_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("PATH", "/usr/bin")

    environment = TestForge._safe_environment()

    assert "OPENAI_API_KEY" not in environment
    assert "GITHUB_TOKEN" not in environment
    assert environment["PATH"] == "/usr/bin"
