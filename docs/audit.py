"""
RepoForge Audit — First commercial product

Produces:
- Architecture summary
- Security signals
- Quality score + breakdown
- Prioritized improvement plan

Does NOT modify the repository (read-only).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from repoforge.scanner import RepoScanner
from repoforge.intelligence.intelligence_engine import IntelligenceEngine
from repoforge.issue_detector import IssueDetector
from repoforge.priority_engine import PriorityEngine


class RepoAuditor:
    def __init__(self, repo_path: str):
        self.repo_path = str(Path(repo_path).resolve())
        self.scanner = RepoScanner(self.repo_path)
        self.intelligence = IntelligenceEngine(self.repo_path)
        self.detector = IssueDetector()
        self.priority = PriorityEngine()

    def _normalize_scan(self, scan) -> Dict[str, Any]:
        if hasattr(scan, "to_dict"):
            scan = scan.to_dict()
        if not isinstance(scan, dict):
            return {"statistics": {"files": 0, "lines": 0}, "languages": {}, "metadata": {}}
        stats = scan.get("statistics") or {}
        if "files" not in stats and "total_files" in stats:
            stats["files"] = stats["total_files"]
        if "lines" not in stats and "total_lines" in stats:
            stats["lines"] = stats["total_lines"]
        scan["statistics"] = stats
        return scan

    def run(self) -> Dict[str, Any]:
        raw = self.scanner.scan()
        scan = self._normalize_scan(raw)
        intelligence = self.intelligence.analyze(scan) or {}

        # Normalize quality_score shape
        if "quality_score" not in intelligence:
            score = intelligence.get("score") or {}
            quality = intelligence.get("quality") or {}
            intelligence["quality_score"] = {
                "score": score.get("score", quality.get("score", 0)),
                "grade": score.get("grade", quality.get("grade", "N/A")),
                "breakdown": score.get("breakdown") or quality.get("breakdown") or {},
                "signals": score.get("signals") or {},
            }

        issues = self.detector.detect(scan, intelligence)
        try:
            ranked = self.priority.rank(issues)
        except Exception:
            ranked = issues

        quality = intelligence.get("quality_score") or {}
        stats = scan.get("statistics") or {}
        metadata = scan.get("metadata") or {}
        profile = scan.get("profile") or {}
        languages = scan.get("languages") or {}

        # Architecture summary
        architecture = {
            "primary_language": profile.get("primary_language") or (
                next(iter(languages.keys()), "unknown") if isinstance(languages, dict) else "unknown"
            ),
            "repo_type": profile.get("repo_type") or "unknown",
            "languages": languages if isinstance(languages, dict) else {},
            "files": stats.get("files", 0),
            "lines": stats.get("lines", 0),
            "has_dockerfile": bool(metadata.get("has_dockerfile")),
            "has_ci": bool(metadata.get("has_github_actions") or metadata.get("has_ci_config")),
            "has_tests": bool(metadata.get("has_tests_dir")),
            "has_docs": bool(metadata.get("has_docs_dir")),
            "has_readme": bool(metadata.get("has_readme")),
            "has_license": bool(metadata.get("has_license")),
        }

        # Security report (signals-based for v1)
        security = {
            "score": (quality.get("breakdown") or {}).get("security", 0),
            "findings": [],
        }
        if not architecture["has_ci"]:
            security["findings"].append({
                "severity": "medium",
                "title": "No CI/CD detected",
                "detail": "Add automated checks (lint, test, dependency scan) via GitHub Actions or equivalent.",
            })
        if not architecture["has_license"]:
            security["findings"].append({
                "severity": "low",
                "title": "Missing LICENSE",
                "detail": "Add a clear open-source license file.",
            })
        if not architecture["has_tests"]:
            security["findings"].append({
                "severity": "medium",
                "title": "No tests directory",
                "detail": "Lack of automated tests increases regression and security risk.",
            })

        plan = []
        for i, issue in enumerate(ranked[:10], 1):
            plan.append({
                "priority": i,
                "type": issue.get("type"),
                "description": issue.get("description"),
                "recommendation": issue.get("recommendation"),
                "severity": issue.get("severity_score"),
                "effort": issue.get("effort_estimate"),
                "location": issue.get("location"),
            })

        report = {
            "product": "RepoForge Audit",
            "version": "0.5.1",
            "repository": self.repo_path,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "quality": {
                "score": quality.get("score", 0),
                "grade": quality.get("grade", "N/A"),
                "breakdown": quality.get("breakdown") or {},
            },
            "architecture": architecture,
            "security": security,
            "issues_found": len(ranked),
            "improvement_plan": plan,
        }
        return report

    def save(self, report: Dict[str, Any]) -> Path:
        out_dir = Path(self.repo_path) / ".repoforge" / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"audit_{ts}.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return path


def print_audit(report: Dict[str, Any]) -> None:
    q = report["quality"]
    arch = report["architecture"]
    sec = report["security"]
    plan = report["improvement_plan"]

    print("")
    print("=" * 60)
    print("📋 RepoForge Audit")
    print("=" * 60)
    print(f"📂 Repository : {report['repository']}")
    print(f"⭐ Quality    : {q.get('score')}/100  Grade {q.get('grade')}")
    print("")
    print("── Architecture ──")
    print(f"  Language    : {arch.get('primary_language')}")
    print(f"  Type        : {arch.get('repo_type')}")
    print(f"  Files/Lines : {arch.get('files')} / {arch.get('lines')}")
    print(f"  README      : {'yes' if arch.get('has_readme') else 'no'}")
    print(f"  Tests       : {'yes' if arch.get('has_tests') else 'no'}")
    print(f"  CI          : {'yes' if arch.get('has_ci') else 'no'}")
    print(f"  License     : {'yes' if arch.get('has_license') else 'no'}")
    print("")
    print("── Quality Breakdown ──")
    for k, v in (q.get("breakdown") or {}).items():
        print(f"  {k.capitalize():16}: {v}")
    print("")
    print("── Security Signals ──")
    if not sec.get("findings"):
        print("  No major signal-based findings.")
    else:
        for f in sec["findings"]:
            print(f"  [{f['severity']}] {f['title']}: {f['detail']}")
    print("")
    print(f"── Improvement Plan ({report['issues_found']} issues) ──")
    if not plan:
        print("  No prioritized issues. Repository looks healthy on current signals.")
    else:
        for item in plan:
            print(f"  {item['priority']}. [{item['type']}] {item['description']}")
            print(f"     → {item['recommendation']}")
    print("")
    print("=" * 60)
