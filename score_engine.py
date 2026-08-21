"""
RepoForge Score Engine V5

Realistic repository intelligence scoring using scan metadata.
"""

from __future__ import annotations

from typing import Any, Dict


class ScoreEngine:
    def calculate(self, scan: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(scan, dict):
            scan = {}

        stats = scan.get("statistics", {}) or {}
        metadata = scan.get("metadata", {}) or {}
        profile = scan.get("profile", {}) or {}
        languages = scan.get("languages", {}) or {}
        structure = scan.get("structure", {}) or {}
        issues = scan.get("issues", []) or []
        security_findings = scan.get("security", []) or []
        todos = scan.get("todos", []) or []

        files = int(stats.get("files") or stats.get("total_files") or 0)
        lines = int(stats.get("lines") or stats.get("total_lines") or 0)

        # --- Documentation (start 40, earn points) ---
        documentation = 40
        has_readme = bool(metadata.get("has_readme"))
        has_docs = bool(metadata.get("has_docs_dir"))
        has_license = bool(metadata.get("has_license"))

        # Fallback: structure keys
        if not has_readme:
            for item in list(structure.keys()) if isinstance(structure, dict) else structure:
                if "readme" in str(item).lower():
                    has_readme = True
                    break

        if has_readme:
            documentation += 35
        if has_docs:
            documentation += 15
        if has_license:
            documentation += 10
        documentation = min(100, documentation)

        # --- Testing ---
        testing = 30
        has_tests = bool(metadata.get("has_tests_dir"))
        if not has_tests:
            for item in list(structure.keys()) if isinstance(structure, dict) else structure:
                if "test" in str(item).lower():
                    has_tests = True
                    break
        # Language-aware: look for test files in important_files
        important = scan.get("important_files") or []
        for f in important:
            fl = str(f).lower()
            if "test" in fl or fl.startswith("tests/") or "/tests/" in fl:
                has_tests = True
                break

        if has_tests:
            testing = 85
            # Slight penalty if very large repo but only weak test signal
            if files > 2000 and testing > 70:
                testing = 75
        else:
            testing = 25
        testing = max(0, min(100, testing))

        # --- Security ---
        security_score = 70
        has_ci = bool(metadata.get("has_github_actions") or metadata.get("has_ci_config"))
        has_dockerfile = bool(metadata.get("has_dockerfile"))
        if has_ci:
            security_score += 10
        if has_license:
            security_score += 5
        # Penalties
        security_score -= min(40, len(security_findings) * 12)
        # Large untested surface
        if not has_tests and files > 100:
            security_score -= 10
        security_score = max(0, min(100, security_score))

        # --- Maintainability ---
        maintainability = 75
        if files > 3000:
            maintainability -= 10
        if files > 8000:
            maintainability -= 10
        if lines > 500000:
            maintainability -= 10
        if lines > 2000000:
            maintainability -= 10
        if len(todos) > 20:
            maintainability -= 8
        if len(todos) > 50:
            maintainability -= 7
        if has_tests:
            maintainability += 10
        if has_ci:
            maintainability += 5
        # Language diversity slight bonus
        if isinstance(languages, dict) and len(languages) >= 3:
            maintainability += 5
        maintainability = max(0, min(100, maintainability))

        breakdown = {
            "documentation": documentation,
            "testing": testing,
            "security": security_score,
            "maintainability": maintainability,
        }

        score = int(
            breakdown["documentation"] * 0.25
            + breakdown["testing"] * 0.30
            + breakdown["security"] * 0.25
            + breakdown["maintainability"] * 0.20
        )

        return {
            "score": score,
            "grade": self.grade(score),
            "breakdown": breakdown,
            "signals": {
                "has_readme": has_readme,
                "has_tests": has_tests,
                "has_license": has_license,
                "has_ci": has_ci,
                "has_docs": has_docs,
                "has_dockerfile": has_dockerfile,
                "primary_language": profile.get("primary_language"),
                "repo_type": profile.get("repo_type"),
            },
            "repository": {"files": files, "lines": lines},
        }

    def grade(self, score: int) -> str:
        if score >= 90:
            return "A"
        if score >= 75:
            return "B"
        if score >= 60:
            return "C"
        if score >= 40:
            return "D"
        return "F"
