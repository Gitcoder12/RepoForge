"""
RepoForge V4/V5 Issue Detector

Converts intelligence scores + scan signals into actionable issues.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Issue:
    type: str
    description: str
    recommendation: str
    severity_score: float
    effort_estimate: float
    confidence: float
    location: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IssueDetector:
    THRESHOLDS = {
        "testing": 80,
        "security": 85,
        "maintainability": 80,
        "documentation": 75,
    }

    def detect(
        self,
        scan: Dict[str, Any],
        intelligence: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        issues: List[Issue] = []

        quality = intelligence.get("quality_score") or intelligence.get("score") or {}
        if not isinstance(quality, dict):
            quality = {}
        breakdown = quality.get("breakdown") or intelligence.get("breakdown") or {}
        signals = quality.get("signals") or {}

        metadata = (scan or {}).get("metadata") or {}
        stats = (scan or {}).get("statistics") or {}
        profile = (scan or {}).get("profile") or {}
        files = int(stats.get("files") or stats.get("total_files") or 0)
        lines = int(stats.get("lines") or stats.get("total_lines") or 0)

        # Merge signals from score engine + scan metadata
        has_readme = signals.get("has_readme", metadata.get("has_readme", False))
        has_tests = signals.get("has_tests", metadata.get("has_tests_dir", False))
        has_license = signals.get("has_license", metadata.get("has_license", False))
        has_ci = signals.get("has_ci", metadata.get("has_github_actions") or metadata.get("has_ci_config"))
        has_docs = signals.get("has_docs", metadata.get("has_docs_dir", False))

        def score_of(key: str, default: int = 100) -> int:
            try:
                return int(breakdown.get(key, default))
            except (TypeError, ValueError):
                return default

        # 1. Testing
        test_score = score_of("testing", 100 if has_tests else 30)
        if not has_tests or test_score < self.THRESHOLDS["testing"]:
            issues.append(Issue(
                type="testing",
                description=f"Testing coverage is weak (score: {test_score}, has_tests_dir={bool(has_tests)})",
                recommendation="Add unit tests for core modules and at least one integration test path. Create a tests/ directory if missing.",
                severity_score=0.85 if not has_tests else 0.65,
                effort_estimate=0.55,
                confidence=0.9,
                location="tests/",
                metadata={"current_score": test_score, "has_tests": has_tests},
            ))

        # 2. Documentation
        doc_score = score_of("documentation", 100 if has_readme else 40)
        if not has_readme or doc_score < self.THRESHOLDS["documentation"]:
            issues.append(Issue(
                type="documentation",
                description=f"Documentation is incomplete (score: {doc_score}, has_readme={bool(has_readme)})",
                recommendation="Improve README with install, usage, and architecture sections. Add docs/ for larger projects.",
                severity_score=0.55,
                effort_estimate=0.35,
                confidence=0.95,
                location="README.md",
                metadata={"current_score": doc_score, "has_readme": has_readme, "has_docs": has_docs},
            ))

        # 3. License
        if not has_license:
            issues.append(Issue(
                type="documentation",
                description="No LICENSE file detected",
                recommendation="Add an open-source LICENSE (MIT/Apache-2.0) appropriate for the project.",
                severity_score=0.4,
                effort_estimate=0.1,
                confidence=0.95,
                location="LICENSE",
                metadata={"has_license": False},
            ))

        # 4. Security / CI
        sec_score = score_of("security", 70)
        if sec_score < self.THRESHOLDS["security"] or not has_ci:
            desc = f"Security posture needs attention (score: {sec_score})"
            if not has_ci:
                desc += "; no CI/CD workflow detected"
            issues.append(Issue(
                type="security",
                description=desc,
                recommendation="Add GitHub Actions CI, dependency scanning, and avoid hardcoded secrets. Review auth and input validation paths.",
                severity_score=0.7 if not has_ci else 0.6,
                effort_estimate=0.45,
                confidence=0.8,
                location=".github/workflows/",
                metadata={"current_score": sec_score, "has_ci": has_ci},
            ))

        # 5. Maintainability / size
        maint = score_of("maintainability", 75)
        if maint < self.THRESHOLDS["maintainability"] or files > 5000 or lines > 500000:
            issues.append(Issue(
                type="maintainability",
                description=f"Maintainability risk (score: {maint}, files={files}, lines={lines})",
                recommendation="Split large modules, reduce coupling, document architecture decisions, and keep modules under clear boundaries.",
                severity_score=0.6,
                effort_estimate=0.7,
                confidence=0.75,
                location=".",
                metadata={"current_score": maint, "files": files, "lines": lines},
            ))

        # 6. Architecture signal for large multi-lang repos
        langs = (scan or {}).get("languages") or {}
        if isinstance(langs, dict) and len(langs) >= 4 and files > 200:
            issues.append(Issue(
                type="architecture",
                description=f"Multi-language repository ({len(langs)} languages) may need clearer boundaries",
                recommendation="Document component ownership, define interfaces between languages, and consider monorepo tooling.",
                severity_score=0.5,
                effort_estimate=0.6,
                confidence=0.7,
                location=".",
                metadata={"languages": list(langs.keys())[:12]},
            ))

        # Sort by severity
        issues.sort(key=lambda i: i.severity_score, reverse=True)
        return [asdict(i) for i in issues]
