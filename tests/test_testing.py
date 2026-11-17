"""Tests for TestForge discovery and bounded, explicit test execution."""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import pytest

from repoforge.testing import MAX_OUTPUT_BYTES, TestForge


class FakeProcess:
    def __init__(
        self,
        command: list[str],
        *,
        return_code: int = 0,
        output: bytes = b"",
        timeout: bool = False,
    ) -> None:
        self.command = command
        self.return_code = return_code
        self.stdout = io.BytesIO(output)
        self.pid = 2_000_000_000
        self.timeout = timeout
        self.killed = False
        self.wait_calls: list[int | None] = []

    def wait(self, timeout: int | None = None) -> int:
        self.wait_calls.append(timeout)
        if self.timeout and timeout is not None:
            raise subprocess.TimeoutExpired(self.command, timeout)
        return self.return_code

    def kill(self) -> None:
        self.killed = True


def test_testforge_plans_python_tests_without_executing(tmp_path: Path, monkeypatch):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )

    def unexpected_popen(*args, **kwargs):
        raise AssertionError("plan-only mode must not execute repository code")

    monkeypatch.setattr(subprocess, "Popen", unexpected_popen)
    report = TestForge(tmp_path).run()

    assert report["mode"] == "plan_only"
    assert report["status"] == "planned"
    assert report["execution_is_sandboxed"] is False
    assert report["commands"][0]["ecosystem"] == "python"
    assert report["commands"][0]["command"][-2:] == ["pytest", "-q"]


def test_testforge_detects_go_and_javascript_test_commands(tmp_path: Path):
    (tmp_path / "go.mod").write_text("module example\n", encoding="utf-8")
    (tmp_path / "service_test.go").write_text("package example\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        '{"scripts":{"test":"vitest run"}}', encoding="utf-8"
    )
    (tmp_path / "app.test.ts").write_text("export {}\n", encoding="utf-8")

    commands = TestForge(tmp_path).plan()["commands"]

    assert {item["ecosystem"] for item in commands} == {"go", "javascript"}
    assert any(item["command"] == ["go", "test", "./..."] for item in commands)
    assert any(item["command"] == ["npm", "test"] for item in commands)


def test_testforge_skips_dependency_folders_and_bounds_the_scan(tmp_path: Path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dependency_test.go").write_text(
        "package dependency\n", encoding="utf-8"
    )
    (tmp_path / "one.py").write_text("print('one')\n", encoding="utf-8")
    (tmp_path / "two.py").write_text("print('two')\n", encoding="utf-8")

    report = TestForge(tmp_path, max_files=1).plan()

    assert report["scan"]["truncated"] is True
    assert report["scan"]["complete"] is False
    assert report["scan"]["files_scanned"] == 1
    assert report["status"] == "scan_incomplete"


def test_testforge_does_not_follow_symlink_directories(tmp_path: Path):
    external = tmp_path.parent / "testforge-external"
    external.mkdir(exist_ok=True)
    (external / "external_test.go").write_text("package external\n", encoding="utf-8")
    (tmp_path / "linked").symlink_to(external, target_is_directory=True)

    report = TestForge(tmp_path).plan()

    assert report["status"] == "no_tests_detected"
    assert report["scan"]["complete"] is True


def test_testforge_returns_no_tests_for_empty_repository(tmp_path: Path):
    report = TestForge(tmp_path).plan()

    assert report["status"] == "no_tests_detected"
    assert report["commands"] == []


def test_testforge_executes_only_after_explicit_opt_in(tmp_path: Path, monkeypatch):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    captured: dict = {}
    fake_process = FakeProcess(
        [sys.executable, "-m", "pytest", "-q"], output=b"1 passed"
    )

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        return fake_process

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    report = TestForge(tmp_path).run(execute=True, timeout=15)

    assert report["mode"] == "execute"
    assert report["status"] == "passed"
    assert report["results"][0]["status"] == "passed"
    assert captured["shell"] is False
    assert captured["cwd"] == tmp_path
    assert fake_process.wait_calls == [15]


def test_testforge_reports_test_failures(tmp_path: Path, monkeypatch):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    fake_process = FakeProcess(["python", "-m", "pytest"], return_code=1, output=b"1 failed")

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: fake_process)
    report = TestForge(tmp_path).run(execute=True)

    assert report["status"] == "failed"
    assert report["results"][0]["status"] == "failed"
    assert report["results"][0]["return_code"] == 1


def test_testforge_reports_timeout_and_kills_process(tmp_path: Path, monkeypatch):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    fake_process = FakeProcess(["python", "-m", "pytest"], timeout=True)

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: fake_process)
    report = TestForge(tmp_path).run(execute=True, timeout=2)

    assert report["status"] == "failed"
    assert report["results"][0]["status"] == "timed_out"
    assert fake_process.killed is True


def test_testforge_bounds_captured_output(tmp_path: Path, monkeypatch):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    fake_process = FakeProcess(["python", "-m", "pytest"], output=b"x" * 20_000)

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: fake_process)
    report = TestForge(tmp_path).run(execute=True)

    result = report["results"][0]
    assert len(result["output"].encode("utf-8")) <= MAX_OUTPUT_BYTES
    assert result["output_truncated"] is True


def test_testforge_reports_missing_runner(tmp_path: Path, monkeypatch):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )

    def missing_runner(*args, **kwargs):
        raise FileNotFoundError("pytest runner not found")

    monkeypatch.setattr(subprocess, "Popen", missing_runner)
    report = TestForge(tmp_path).run(execute=True)

    assert report["status"] == "failed"
    assert report["results"][0]["status"] == "unavailable"


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



def test_testforge_refuses_to_execute_after_an_incomplete_scan(tmp_path: Path, monkeypatch):
    (tmp_path / "one.py").write_text("print('one')\n", encoding="utf-8")
    (tmp_path / "two.py").write_text("print('two')\n", encoding="utf-8")

    def unexpected_popen(*args, **kwargs):
        raise AssertionError("incomplete scans must never execute a partial test plan")

    monkeypatch.setattr(subprocess, "Popen", unexpected_popen)
    report = TestForge(tmp_path, max_files=1).run(execute=True)

    assert report["status"] == "scan_incomplete"
    assert report["mode"] == "plan_only"
    assert "results" not in report
