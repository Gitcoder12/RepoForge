"""Local-first repository assessment and safe, reviewable repair planning.

The first Blacksmith release never executes target-repository code. It inspects
bounded file metadata and applies only explicit create-if-absent hygiene fixes.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from repoforge.upgrades import UpgradePlanner

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
    ".tox",
    ".idea",
    ".next",
}

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".cs": "C#",
    ".cpp": "C++",
    ".cc": "C++",
    ".c": "C",
    ".h": "C/C++",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".dart": "Dart",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
}

MANIFESTS = {
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "package.json",
    "go.mod",
    "cargo.toml",
    "pom.xml",
    "build.gradle",
    "gemfile",
    "composer.json",
}

GENERIC_GITIGNORE = """# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# JavaScript / TypeScript
node_modules/
dist/
.next/
coverage/

# Build and local environment
.env
.env.*
!.env.example
.DS_Store
Thumbs.db
.idea/
.vscode/
"""


class Blacksmith:
    """Inspect, rank, and safely improve a local repository."""

    def __init__(self, repo_path: str | Path = ".", *, max_files: int = 20_000) -> None:
        self.repo_path = Path(repo_path).expanduser().resolve()
        if not self.repo_path.exists() or not self.repo_path.is_dir():
            raise ValueError(f"repository path must be an existing directory: {repo_path}")
        if isinstance(max_files, bool) or not isinstance(max_files, int) or max_files < 1:
            raise ValueError("max_files must be a positive integer")
        self.max_files = max_files

    def _files(self) -> tuple[list[str], bool, list[str]]:
        """Return bounded paths and any traversal errors without following symlinks."""
        files: list[str] = []
        truncated = False
        scan_errors: list[str] = []
        root = self.repo_path

        def record_walk_error(error: OSError) -> None:
            scan_errors.append(f"{type(error).__name__}: {error}")

        for current, directories, filenames in os.walk(
            root, topdown=True, followlinks=False, onerror=record_walk_error
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
                try:
                    relative = path.relative_to(root).as_posix()
                except ValueError:
                    continue
                files.append(relative)
                if len(files) > self.max_files:
                    files.pop()
                    truncated = True
                    return sorted(files), truncated, scan_errors
        return sorted(files), truncated, scan_errors

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "E"

    @staticmethod
    def _contains_test(files: list[str]) -> bool:
        for file_path in files:
            path = Path(file_path)
            parts = {part.casefold() for part in path.parts}
            name = path.name.casefold()
            if (
                "test" in parts
                or "tests" in parts
                or name.startswith("test_")
                or name.endswith("_test.go")
                or ".test." in name
                or ".spec." in name
            ):
                return True
        return False

    def inspect(self) -> dict[str, Any]:
        """Create a transparent repository snapshot and a deterministic RepoRank."""
        files, truncated, scan_errors = self._files()
        scan_incomplete = truncated or bool(scan_errors)
        lower_files = {item.casefold() for item in files}
        languages: dict[str, int] = {}
        for file_path in files:
            language = LANGUAGE_EXTENSIONS.get(Path(file_path).suffix.lower())
            if language:
                languages[language] = languages.get(language, 0) + 1

        readme = any(
            Path(item).parent == Path(".") and Path(item).name.casefold().startswith("readme")
            for item in files
        )
        contributing = any(Path(item).name.casefold() == "contributing.md" for item in files)
        tests = self._contains_test(files)
        ci = any(
            item.startswith(".github/workflows/")
            or item in {".gitlab-ci.yml", "jenkinsfile", "azure-pipelines.yml"}
            for item in lower_files
        )
        manifest_names = sorted(
            {Path(item).name for item in files if Path(item).name.casefold() in MANIFESTS}
        )
        license_file = any(
            Path(item).parent == Path(".")
            and Path(item).name.casefold().startswith(("license", "copying"))
            for item in files
        )
        gitignore = ".gitignore" in lower_files
        security = any(
            item
            in {
                "security.md",
                ".github/dependabot.yml",
                ".github/dependabot.yaml",
                ".github/codeql.yml",
            }
            for item in lower_files
        )
        quality_config = any(
            Path(item).name.casefold()
            in {
                ".pre-commit-config.yaml",
                ".pre-commit-config.yml",
                ".editorconfig",
                ".ruff.toml",
                "ruff.toml",
                ".eslintrc",
                ".eslintrc.json",
                "eslint.config.js",
            }
            for item in files
        )

        dimensions = {
            "documentation": (12 if readme else 0) + (3 if contributing else 0),
            "tests": 20 if tests else 0,
            "continuous_integration": 20 if ci else 0,
            "project_configuration": 15 if manifest_names else 0,
            "licensing": 10 if license_file else 0,
            "ignore_rules": 5 if gitignore else 0,
            "security_process": 10 if security else 0,
            "quality_tooling": 5 if quality_config else 0,
        }
        score = sum(dimensions.values())
        findings = []
        checks = [
            (readme, "README file is missing"),
            (tests, "No recognisable test files or test directory were found"),
            (ci, "No CI workflow was detected"),
            (bool(manifest_names), "No common project manifest was detected"),
            (license_file, "No root-level LICENSE or COPYING file was detected"),
            (gitignore, "No .gitignore file was detected"),
            (security, "No security policy or dependency-update configuration was detected"),
            (quality_config, "No common formatter/linter/editor configuration was detected"),
        ]
        for passed, message in checks:
            if not passed:
                findings.append(message)
        if scan_incomplete:
            findings.append(
                "Repository scan incomplete because one or more directories could not be read"
            )

        # Capability labels are heuristics for discovery, not verified feature claims.
        readme_text = ""
        for file_path in files:
            if Path(file_path).parent == Path(".") and Path(file_path).name.casefold().startswith(
                "readme"
            ):
                try:
                    with (self.repo_path / file_path).open(
                        "r", encoding="utf-8", errors="replace"
                    ) as readme_file:
                        readme_text = readme_file.read(40_000).casefold()
                except OSError:
                    readme_text = ""
                break
        search_text = (
            f"{self.repo_path.name.casefold()} {readme_text} {' '.join(files[:500]).casefold()}"
        )
        capabilities = self._infer_capabilities(search_text, languages, lower_files)

        return {
            "name": self.repo_path.name,
            "path": str(self.repo_path),
            "files_scanned": len(files),
            "scan_truncated": truncated,
            "scan_incomplete": scan_incomplete,
            "scan_errors": scan_errors,
            "languages": dict(sorted(languages.items())),
            "manifests": manifest_names,
            "capabilities": sorted(capabilities),
            "signals": {
                "readme": readme,
                "tests": tests,
                "ci": ci,
                "license": license_file,
                "gitignore": gitignore,
                "security_process": security,
                "quality_tooling": quality_config,
            },
            "rank": {
                "score": score,
                "grade": self._grade(score),
                "maximum": 100,
                "dimensions": dimensions,
                "method": (
                    "deterministic repository-hygiene signals; not a code-quality "
                    "or security certification"
                ),
            },
            "findings": findings,
        }

    @staticmethod
    def _infer_capabilities(
        text: str, languages: dict[str, int], lower_files: set[str]
    ) -> set[str]:
        capabilities: set[str] = set()
        rules = {
            "ai_ml": (
                "machine learning",
                "deep learning",
                "llm",
                "transformer",
                "pytorch",
                "tensorflow",
                "artificial intelligence",
            ),
            "data": (
                "data pipeline",
                "data engineering",
                "etl",
                "dataset",
                "streaming",
                "analytics",
            ),
            "backend": ("fastapi", "flask", "django", "express", "backend", "rest api", "graphql"),
            "frontend": ("react", "next.js", "frontend", "user interface", "dashboard", "vite"),
            "robotics": ("robotics", "robot arm", "autonomous robot", "simulator"),
            "security": (
                "cybersecurity",
                "security scanner",
                "red team",
                "vulnerability",
                "penetration testing",
            ),
            "evaluation": (
                "benchmark",
                "evaluation harness",
                "red teaming",
                "test framework",
                "metrics",
            ),
            "infrastructure": (
                "docker",
                "kubernetes",
                "deployment",
                "terraform",
                "infrastructure as code",
            ),
            "research": ("research paper", "research framework", "experiment", "scientific"),
            "cli": ("command line", "cli tool", "terminal"),
        }
        for capability, phrases in rules.items():
            if any(phrase in text for phrase in phrases):
                capabilities.add(capability)
        if re.search(r"\bros\b", text):
            capabilities.add("robotics")
        if Blacksmith._contains_test(list(lower_files)):
            capabilities.add("testing")
        if any(item.startswith(".github/workflows/") for item in lower_files):
            capabilities.add("automation")
        return capabilities

    def repair_plan(self, snapshot: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Propose safe create-only repairs; never overwrite or delete user files."""
        snapshot = self.inspect() if snapshot is None else snapshot
        repairs: list[dict[str, Any]] = []
        if not snapshot["signals"]["gitignore"]:
            ignore_content = GENERIC_GITIGNORE
            if "Rust" in snapshot.get("languages", {}):
                ignore_content += "\n# Rust\n/target/\n**/*.rs.bk\n"
            repairs.append(
                {
                    "path": ".gitignore",
                    "operation": "create_if_absent",
                    "reason": (
                        "Add local environment, cache, build-output, and detected-stack "
                        "ignore rules"
                    ),
                    "safe_to_apply": True,
                    "content": ignore_content,
                }
            )
        if not snapshot["signals"]["ci"] and snapshot["languages"]:
            repairs.append(
                {
                    "path": ".github/workflows/ci.yml",
                    "operation": "review_required",
                    "reason": (
                        "A CI workflow is missing; commands must be tailored to "
                        "this repository's actual toolchain"
                    ),
                    "safe_to_apply": False,
                    "content": None,
                }
            )
        if not snapshot["signals"]["tests"]:
            repairs.append(
                {
                    "path": "tests/",
                    "operation": "human_design_required",
                    "reason": (
                        "Tests must assert real project behavior; Blacksmith will "
                        "not generate fake passing tests"
                    ),
                    "safe_to_apply": False,
                    "content": None,
                }
            )
        return repairs

    def apply_repairs(self, repairs: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Apply only safe create-if-absent repairs with atomic file creation."""
        applied: list[dict[str, str]] = []
        for repair in repairs:
            if repair.get("operation") != "create_if_absent" or not repair.get("safe_to_apply"):
                continue
            relative = Path(repair["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("repair path must stay inside the repository")
            target = self.repo_path / relative
            parent = target.parent
            while parent != self.repo_path:
                if parent.is_symlink():
                    raise ValueError(f"refusing to write through symlink directory: {parent}")
                parent = parent.parent
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                target.resolve().relative_to(self.repo_path)
            except ValueError as exc:
                raise ValueError("repair path escapes repository root") from exc
            if target.is_symlink():
                raise ValueError(f"refusing to write through symlink: {relative}")
            if target.exists():
                applied.append({"path": relative.as_posix(), "status": "skipped_exists"})
                continue
            try:
                with target.open("x", encoding="utf-8", newline="\n") as handle:
                    handle.write(repair["content"])
                applied.append({"path": relative.as_posix(), "status": "created"})
            except FileExistsError:
                applied.append({"path": relative.as_posix(), "status": "skipped_exists"})
        return applied

    def run(self, *, apply_fixes: bool = False) -> dict[str, Any]:
        """Return before/after RepoRank and the reviewed repair plan."""
        if not isinstance(apply_fixes, bool):
            raise ValueError("apply_fixes must be a boolean")
        before = self.inspect()
        plan = self.repair_plan(before)
        applied = self.apply_repairs(plan) if apply_fixes else []
        after = self.inspect() if applied else before
        return {
            "repository": before["name"],
            "mode": "apply_safe_repairs" if apply_fixes else "dry_run",
            "before": before,
            "repair_plan": [
                {key: value for key, value in repair.items() if key != "content"} for repair in plan
            ],
            "applied": applied,
            "after": after,
            "rank_change": after["rank"]["score"] - before["rank"]["score"],
            "upgrade_options": UpgradePlanner().build(after),
        }
