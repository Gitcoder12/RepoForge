"""Optional, preview-only adapter for the standalone LangFix CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class LangFixBridge:
    """Run LangFix as a separate process without asking it to write target files.

    The bridge deliberately never passes LangFix's --fix flag. Its working
    directory is an isolated temporary directory so LangFix's scan cache is
    not written into the repository being inspected.
    """

    def scan(self, repo_path: str | Path, *, timeout: int = 180) -> dict[str, Any]:
        root = Path(repo_path).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"repository path must be an existing directory: {repo_path}")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout < 1:
            raise ValueError("timeout must be a positive integer")

        executable = shutil.which("langfix")
        if executable is None:
            return {
                "engine": "LangFix",
                "status": "unavailable",
                "message": (
                    "LangFix CLI was not found on PATH; install the LangFix package "
                    "to enable this hook."
                ),
                "files_scanned": 0,
            }

        command = [executable, str(root), "--json", "--workers", "4"]
        try:
            with tempfile.TemporaryDirectory(prefix="repoforge-langfix-") as cache_dir:
                completed = subprocess.run(
                    command,
                    cwd=cache_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                    shell=False,
                )
        except subprocess.TimeoutExpired:
            return {
                "engine": "LangFix",
                "status": "timeout",
                "message": f"LangFix exceeded the {timeout}s timeout.",
                "files_scanned": 0,
            }
        except OSError as exc:
            return {
                "engine": "LangFix",
                "status": "failed",
                "message": f"Could not start LangFix: {type(exc).__name__}",
                "files_scanned": 0,
            }

        output = completed.stdout.strip()
        try:
            report = json.loads(output)
        except json.JSONDecodeError:
            detail = (completed.stderr or output or "LangFix returned no JSON report")[-2000:]
            return {
                "engine": "LangFix",
                "status": "invalid_report",
                "return_code": completed.returncode,
                "message": detail,
                "files_scanned": 0,
            }

        if not isinstance(report, dict) or not isinstance(report.get("files"), list):
            return {
                "engine": "LangFix",
                "status": "invalid_report",
                "return_code": completed.returncode,
                "message": "LangFix JSON did not contain a files array.",
                "files_scanned": 0,
            }

        files = report["files"]
        languages: dict[str, int] = {}
        extension_languages = {
            ".py": "python", ".pyw": "python", ".js": "javascript",
            ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "typescript", ".java": "java",
            ".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp",
            ".cxx": "cpp", ".hpp": "cpp", ".go": "go", ".rs": "rust",
            ".sql": "sql", ".html": "html", ".htm": "html", ".css": "css",
            ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".rb": "ruby",
            ".php": "php", ".sh": "shell", ".bash": "shell",
            ".kt": "kotlin", ".kts": "kotlin", ".swift": "swift",
        }
        for item in files:
            if not isinstance(item, dict):
                continue
            suffix = Path(str(item.get("file", ""))).suffix.lower()
            language = extension_languages.get(suffix)
            if language:
                languages[language] = languages.get(language, 0) + 1

        return {
            "engine": "LangFix",
            "status": "completed" if completed.returncode == 0 else "failed",
            "return_code": completed.returncode,
            "average_score": report.get("average_score"),
            "vibe": report.get("vibe"),
            "files_scanned": len(files),
            "languages": dict(sorted(languages.items())),
            "findings": sum(
                1
                for item in files
                if isinstance(item, dict) and item.get("vibe") in {"FAIL", "POOR"}
            ),
            "message": (
                "Preview-only scan; no --fix option was supplied and the scan cache "
                "was isolated from the target repository."
            ),
            "stderr": completed.stderr[-2000:] if completed.stderr else "",
        }
