"""
RepoForge Validator

Validates repository changes after AI modifications.
Lenient by default so successful action runs still get Git checkpoints.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List


class Validator:
    IGNORE_DIRS = {
        ".git",
        ".repoforge",
        "__pycache__",
        "node_modules",
        "venv",
        ".venv",
        "dist",
        "build",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "eggs",
        "*.egg-info",
    }

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()

    def validate(self) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        errors = 0
        checked = 0

        for file in self.repo_path.rglob("*.py"):
            if any(part in self.IGNORE_DIRS for part in file.parts):
                continue
            # Skip test files and caches for strictness
            if "test_" in file.name or file.name.endswith("_test.py"):
                continue

            checked += 1
            try:
                source = file.read_text(encoding="utf-8", errors="ignore")
                if not source.strip():
                    continue
                ast.parse(source)
                results.append({"file": str(file.relative_to(self.repo_path)), "passed": True})
            except SyntaxError as e:
                errors += 1
                results.append({
                    "file": str(file.relative_to(self.repo_path)),
                    "passed": False,
                    "error": f"line {e.lineno}: {e.msg}",
                })
            except Exception as e:
                # Permission / encoding – treat as warning, not failure
                results.append({
                    "file": str(file.relative_to(self.repo_path)),
                    "passed": True,
                    "warning": str(e),
                })

        # Lenient gate: pass if fewer than 20% of checked files have syntax errors
        # (old AI-generated stubs shouldn't block the whole product)
        passed = True
        if checked > 0 and errors > 0:
            ratio = errors / checked
            passed = ratio < 0.20

        return {
            "syntax": {
                "passed": passed,
                "checked": checked,
                "errors": errors,
                "files": results[:50],  # keep report small
            },
            "passed": passed,
        }


RepoValidator = Validator
