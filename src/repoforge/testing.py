"""Fast, explicit test discovery and bounded-output execution for local repositories.

TestForge plans commands without executing repository code by default. Running a
repository's tests is arbitrary code execution, not a sandbox; use --execute only
for repositories you trust.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
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
DEFAULT_MAX_FILES = 20_000
MAX_OUTPUT_BYTES = 8_000


class TestForge:
    """Detect conventional test runners and execute them only after opt-in."""

    def __init__(self, repo_path: str | Path = ".", *, max_files: int = DEFAULT_MAX_FILES) -> None:
        self.repo_path = Path(repo_path).expanduser().resolve()
        if not self.repo_path.is_dir():
            raise ValueError(f"repository path must be an existing directory: {repo_path}")
        if isinstance(max_files, bool) or not isinstance(max_files, int) or max_files < 1:
            raise ValueError("max_files must be a positive integer")
        self.max_files = max_files

    def _files(self) -> tuple[list[str], bool, list[str]]:
        """Perform one bounded walk, pruning ignored and symlink directories."""
        files: list[str] = []
        truncated = False
        scan_errors: list[str] = []

        def record_error(error: OSError) -> None:
            scan_errors.append(f"{type(error).__name__}: {error}")

        for current, directories, filenames in os.walk(
            self.repo_path,
            topdown=True,
            followlinks=False,
            onerror=record_error,
        ):
            current_path = Path(current)
            directories[:] = [
                name
                for name in directories
                if name not in SKIP_DIRS and not (current_path / name).is_symlink()
            ]
            for filename in filenames:
                path = current_path / filename
                if path.is_symlink() or not path.is_file():
                    continue
                relative = path.relative_to(self.repo_path).as_posix()
                files.append(relative)
                if len(files) > self.max_files:
                    files.pop()
                    truncated = True
                    return sorted(files), truncated, scan_errors

        return sorted(files), truncated, scan_errors

    @staticmethod
    def _is_python_test(path: str) -> bool:
        name = Path(path).name.casefold()
        return name.startswith("test_") or name.endswith("_test.py")

    @staticmethod
    def _is_javascript_test(path: str) -> bool:
        name = Path(path).name.casefold()
        parts = {part.casefold() for part in Path(path).parts}
        return ".test." in name or ".spec." in name or "__tests__" in parts

    def plan(self) -> dict[str, Any]:
        """Return detected test commands without executing target code."""
        files, truncated, scan_errors = self._files()
        file_set = {item.casefold() for item in files}
        commands: list[dict[str, Any]] = []

        python_tests = []
        for item in files:
            if Path(item).suffix.casefold() == ".py" and self._is_python_test(item):
                python_tests.append(item)
        if python_tests:
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
                    "reason": "Conventional Python test files were detected.",
                }
            )

        package_json = self.repo_path / "package.json"
        javascript_tests = [item for item in files if self._is_javascript_test(item)]
        if package_json.is_file() and javascript_tests:
            try:
                with package_json.open("r", encoding="utf-8") as package_file:
                    package = json.load(package_file)
                scripts = package.get("scripts", {})
                test_script = scripts.get("test") if isinstance(scripts, dict) else None
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

        if "go.mod" in file_set and any(Path(item).name.endswith("_test.go") for item in files):
            commands.append(
                {
                    "ecosystem": "go",
                    "command": ["go", "test", "./..."],
                    "reason": "go.mod and conventional *_test.go files were detected.",
                }
            )

        if "cargo.toml" in file_set:
            commands.append(
                {
                    "ecosystem": "rust",
                    "command": ["cargo", "test"],
                    "reason": "Cargo.toml detected; run cargo test.",
                }
            )

        java_test_roots = set()
        for item in files:
            parts = Path(item).parts
            for index in range(len(parts) - 1):
                if parts[index : index + 2] == ("src", "test"):
                    java_test_roots.add("/".join(parts[:index]))

        if java_test_roots:
            if "pom.xml" in file_set:
                maven_poms = ["pom.xml"]
            else:
                maven_poms = sorted(
                    f"{root}/pom.xml" if root else "pom.xml"
                    for root in java_test_roots
                    if (f"{root}/pom.xml" if root else "pom.xml") in file_set
                )
            for pom_path in maven_poms:
                commands.append(
                    {
                        "ecosystem": "java-maven",
                        "command": ["mvn", "-q", "-f", pom_path, "test"],
                        "reason": "Maven manifest and module test sources were detected.",
                    }
                )

        gradle_wrapper_name = "gradlew.bat" if os.name == "nt" else "gradlew"
        gradle_wrapper = self.repo_path / gradle_wrapper_name
        if gradle_wrapper.is_file() and java_test_roots:
            gradle_command = (
                [str(gradle_wrapper), "test", "--no-daemon"]
                if os.name == "nt"
                else ["bash", str(gradle_wrapper), "test", "--no-daemon"]
            )
            commands.append(
                {
                    "ecosystem": "java-gradle",
                    "command": gradle_command,
                    "reason": "Gradle wrapper and conventional test source files were detected.",
                }
            )

        dotnet_projects = [
            item for item in files if item.casefold().endswith((".sln", ".slnx", ".csproj"))
        ]
        if dotnet_projects:
            solutions = [
                item for item in dotnet_projects if item.casefold().endswith((".sln", ".slnx"))
            ]
            projects = [item for item in dotnet_projects if item.casefold().endswith(".csproj")]
            targets = solutions or projects
            for target in targets:
                commands.append(
                    {
                        "ecosystem": "dotnet",
                        "command": ["dotnet", "test", target, "--nologo"],
                        "reason": "A .NET solution or project file was detected.",
                    }
                )

        return {
            "repository": self.repo_path.name,
            "path": str(self.repo_path),
            "mode": "plan_only",
            "execution_is_sandboxed": False,
            "scan": {
                "files_scanned": len(files),
                "truncated": truncated,
                "complete": not truncated and not scan_errors,
                "errors": scan_errors,
                "max_files": self.max_files,
            },
            "warning": (
                "Executing tests runs repository-controlled code. This runner is not an OS "
                "sandbox; only use --execute for repositories you trust."
            ),
            "commands": commands,
            "status": (
                "scan_incomplete"
                if truncated or scan_errors
                else ("planned" if commands else "no_tests_detected")
            ),
        }

    @staticmethod
    def _safe_environment() -> dict[str, str]:
        """Preserve runtime essentials while removing common credential variables."""
        blocked_fragments = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "AUTH")
        blocked_names = {
            "DATABASE_URL",
            "DOCKER_AUTH_CONFIG",
            "DOCKER_CONFIG",
            "NETRC",
            "NPM_CONFIG_USERCONFIG",
            "PIP_INDEX_URL",
            "PIP_EXTRA_INDEX_URL",
        }
        blocked_prefixes = (
            "AWS_",
            "AZURE_",
            "GOOGLE_",
            "GITHUB_",
            "GH_",
            "DOCKER_",
            "NPM_CONFIG_",
        )
        environment = {
            key: value
            for key, value in os.environ.items()
            if key.upper() not in blocked_names
            and not any(fragment in key.upper() for fragment in blocked_fragments)
            and not key.upper().startswith(blocked_prefixes)
        }
        environment.update(
            {
                "CI": "1",
                "NO_COLOR": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            }
        )
        return environment

    @staticmethod
    def _kill_process(process: subprocess.Popen[bytes]) -> None:
        """Stop the command and its child process tree after a timeout."""
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                if result.returncode == 0:
                    return
                if process.poll() is not None:
                    return
                process.kill()
                return
            except (OSError, subprocess.TimeoutExpired):
                process.kill()
                return

        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            process.kill()

    @staticmethod
    def _capture_tail(stream: Any, destination: bytearray, truncated_flag: list[bool]) -> None:
        """Drain output continuously while retaining only the final bounded bytes."""
        total_bytes = 0
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    break
                total_bytes += len(chunk)
                destination.extend(chunk)
                overflow = len(destination) - MAX_OUTPUT_BYTES
                if overflow > 0:
                    del destination[:overflow]
            truncated_flag[0] = total_bytes > MAX_OUTPUT_BYTES
        except (OSError, ValueError):
            pass

    def _execute_one(
        self, item: dict[str, Any], *, environment: dict[str, str], timeout: int
    ) -> dict[str, Any]:
        started = time.monotonic()
        launch_options: dict[str, Any] = {}
        if os.name != "nt":
            launch_options["start_new_session"] = True
        else:
            launch_options["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        try:
            process = subprocess.Popen(
                item["command"],
                cwd=self.repo_path,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
                bufsize=0,
                **launch_options,
            )
        except OSError as exc:
            return {
                **item,
                "status": "unavailable",
                "duration_seconds": round(time.monotonic() - started, 3),
                "output": str(exc)[-MAX_OUTPUT_BYTES:],
            }

        output_tail = bytearray()
        output_truncated = [False]
        reader = threading.Thread(
            target=self._capture_tail,
            args=(process.stdout, output_tail, output_truncated),
            daemon=True,
        )
        reader.start()

        timed_out = False
        try:
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._kill_process(process)
            return_code = process.wait()

        reader.join(timeout=2)
        output = output_tail.decode("utf-8", errors="replace")
        status = "timed_out" if timed_out else ("passed" if return_code == 0 else "failed")
        result = {
            **item,
            "status": status,
            "return_code": return_code,
            "duration_seconds": round(time.monotonic() - started, 3),
            "output": output,
            "output_truncated": output_truncated[0],
        }
        return result

    def run(self, *, execute: bool = False, timeout: int = 120) -> dict[str, Any]:
        """Plan tests, or run detected commands after explicit opt-in."""
        if not isinstance(execute, bool):
            raise ValueError("execute must be a boolean")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 1800:
            raise ValueError("timeout must be an integer between 1 and 1800 seconds")

        report = self.plan()
        if not report["scan"]["complete"]:
            report["status"] = "scan_incomplete"
            report["warning"] = (
                "The repository scan was incomplete. No test commands were executed; "
                "increase max_files or fix the traversal errors before relying on results."
            )
            return report
        if not execute or not report["commands"]:
            return report

        report["mode"] = "execute"
        report["results"] = []
        report["status"] = "passed"
        environment = self._safe_environment()

        for item in report["commands"]:
            result = self._execute_one(item, environment=environment, timeout=timeout)
            report["results"].append(result)
            if result["status"] != "passed":
                report["status"] = "failed"
                break

        return report
