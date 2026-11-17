"""Fast, explicit test discovery and execution for local repositories.

TestForge plans commands without executing repository code by default. Running a
repository's tests is arbitrary code execution, not a sandbox; use --execute
only for repositories you trust.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
    ".next",
}


class TestForge:
    """Detect conventional test runners and execute them only after opt-in."""

    def __init__(self, repo_path: str | Path = ".") -> None:
        self.repo_path = Path(repo_path).expanduser().resolve()
        if not self.repo_path.is_dir():
            raise ValueError(f"repository path must be an existing directory: {repo_path}")

    def _has_python_tests(self) -> bool:
        tests_dir = self.repo_path / "tests"
        if tests_dir.is_dir():
            return any(tests_dir.rglob("test_*.py")) or any(
                tests_dir.rglob("*_test.py")
            )
        return any(self.repo_path.glob("test_*.py")) or any(
            self.repo_path.glob("*_test.py")
        )

    def _has_go_tests(self) -> bool:
        return any(
            path.name.endswith("_test.go")
            for path in self.repo_path.rglob("*_test.go")
            if not any(part in SKIP_DIRS for part in path.relative_to(self.repo_path).parts)
        )

    def _has_javascript_tests(self) -> bool:
        for path in self.repo_path.rglob("*"):
            if any(part in SKIP_DIRS for part in path.relative_to(self.repo_path).parts):
                continue
            name = path.name.casefold()
            if path.is_file() and (".test." in name or ".spec." in name):
                return True
        return False

    def plan(self) -> dict[str, Any]:
        """Return detected test commands without executing any target code."""
        commands: list[dict[str, Any]] = []

        if self._has_python_tests():
            python = sys.executable
            for candidate in (
                self.repo_path / ".venv" / "bin" / "python",
                self.repo_path / "venv" / "bin" / "python",
                self.repo_path / ".venv" / "Scripts" / "python.exe",
                self.repo_path / "venv" / "Scripts" / "python.exe",
            ):
                if candidate.is_file():
                    python = str(candidate)
                    break
            commands.append(
                {
                    "ecosystem": "python",
                    "command": [python, "-m", "pytest", "-q"],
                    "reason": "Python test files or a tests/ directory were detected.",
                }
            )

        package_json = self.repo_path / "package.json"
        if package_json.is_file() and self._has_javascript_tests():
            try:
                package = json.loads(package_json.read_text(encoding="utf-8")[:1_000_000])
                test_script = package.get("scripts", {}).get("test")
            except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
                test_script = None
            if isinstance(test_script, str) and test_script.strip():
                if (self.repo_path / "pnpm-lock.yaml").exists():
                    runner = "pnpm"
                elif (self.repo_path / "yarn.lock").exists():
                    runner = "yarn"
                else:
                    runner = "npm"
                commands.append(
                    {
                        "ecosystem": "javascript",
                        "command": [runner, "test"],
                        "reason": "JavaScript tests and a package.json test script were detected.",
                    }
                )

        if (self.repo_path / "go.mod").is_file() and self._has_go_tests():
            commands.append(
                {
                    "ecosystem": "go",
                    "command": ["go", "test", "./..."],
                    "reason": "go.mod and conventional *_test.go files were detected.",
                }
            )

        if (self.repo_path / "Cargo.toml").is_file():
            commands.append(
                {
                    "ecosystem": "rust",
                    "command": ["cargo", "test"],
                    "reason": (
                        "Cargo.toml was detected; cargo test is the standard test entry point."
                    ),
                }
            )

        if (self.repo_path / "pom.xml").is_file() and (
            self.repo_path / "src" / "test"
        ).is_dir():
            commands.append(
                {
                    "ecosystem": "java-maven",
                    "command": ["mvn", "-q", "test"],
                    "reason": "Maven project and conventional test source directory were detected.",
                }
            )

        gradle_wrapper = self.repo_path / ("gradlew.bat" if os.name == "nt" else "gradlew")
        if gradle_wrapper.is_file() and (self.repo_path / "src" / "test").is_dir():
            commands.append(
                {
                    "ecosystem": "java-gradle",
                    "command": [str(gradle_wrapper), "test", "--no-daemon"],
                    "reason": (
                        "Gradle wrapper and conventional test source directory were detected."
                    ),
                }
            )

        dotnet_projects = list(self.repo_path.glob("*.sln")) + list(
            self.repo_path.glob("*.csproj")
        )
        if dotnet_projects:
            commands.append(
                {
                    "ecosystem": "dotnet",
                    "command": ["dotnet", "test", "--nologo"],
                    "reason": "A .NET solution or project file was detected.",
                }
            )

        return {
            "repository": self.repo_path.name,
            "path": str(self.repo_path),
            "mode": "plan_only",
            "execution_is_sandboxed": False,
            "warning": (
                "Executing tests runs repository-controlled code. This runner is not an OS "
                "sandbox; only use --execute for repositories you trust."
            ),
            "commands": commands,
            "status": "planned" if commands else "no_tests_detected",
        }

    @staticmethod
    def _safe_environment() -> dict[str, str]:
        """Preserve runtime essentials while removing common credential variables."""
        blocked_fragments = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
        blocked_prefixes = ("AWS_", "AZURE_", "GOOGLE_", "GITHUB_", "GH_")
        env = {
            key: value
            for key, value in os.environ.items()
            if not any(fragment in key.upper() for fragment in blocked_fragments)
            and not key.upper().startswith(blocked_prefixes)
        }
        env.update(
            {
                "CI": "1",
                "NO_COLOR": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            }
        )
        return env

    def run(self, *, execute: bool = False, timeout: int = 120) -> dict[str, Any]:
        """Plan tests, or run detected commands after explicit opt-in."""
        if not isinstance(execute, bool):
            raise ValueError("execute must be a boolean")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 1800:
            raise ValueError("timeout must be an integer between 1 and 1800 seconds")

        report = self.plan()
        if not execute or not report["commands"]:
            return report

        report["mode"] = "execute"
        report["results"] = []
        report["status"] = "passed"
        environment = self._safe_environment()

        for item in report["commands"]:
            started = time.monotonic()
            try:
                completed = subprocess.run(
                    item["command"],
                    cwd=self.repo_path,
                    env=environment,
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=timeout,
                    check=False,
                    shell=False,
                )
                result = {
                    **item,
                    "status": "passed" if completed.returncode == 0 else "failed",
                    "return_code": completed.returncode,
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "output": (completed.stdout + completed.stderr)[-8000:],
                }
            except subprocess.TimeoutExpired as exc:
                output = exc.stdout or ""
                error = exc.stderr or ""
                if isinstance(output, bytes):
                    output = output.decode(errors="replace")
                if isinstance(error, bytes):
                    error = error.decode(errors="replace")
                result = {
                    **item,
                    "status": "timed_out",
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "output": (output + error)[-8000:],
                }
            except FileNotFoundError as exc:
                result = {
                    **item,
                    "status": "unavailable",
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "output": str(exc),
                }

            report["results"].append(result)
            if result["status"] != "passed":
                report["status"] = "failed"
                break

        return report
