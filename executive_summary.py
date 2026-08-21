"""
Executive Summary Reporter for RepoForge.
Generates a high-level text summary from the scan report.
"""

from typing import Dict, Any, List
from datetime import datetime


class ExecutiveSummary:
    """
    Generates a concise executive summary suitable for team leads
    or CI/CD pipeline logs.
    """

    def __init__(self, report_data: Dict[str, Any]):
        """
        Args:
            report_data: The aggregated report dict from the scanner/workflow.
                         Expected keys: total_repos, healthy, stale, critical,
                         generated_at, repos (list).
        """
        self.data = report_data
        self.repos = report_data.get("repos", [])
        self.total = report_data.get("total_repos", len(self.repos))
        self.healthy = report_data.get("healthy", 0)
        self.stale = report_data.get("stale", 0)
        self.critical = report_data.get("critical", 0)
        self.generated = report_data.get("generated_at", datetime.now().isoformat())

    def generate_text(self) -> str:
        """Returns a human-readable text summary."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"  REPOFORGE EXECUTIVE SUMMARY")
        lines.append(f"  Generated: {self.generated}")
        lines.append("=" * 60)
        lines.append(f"  Total Repositories : {self.total}")
        lines.append(f"  🟢 Healthy          : {self.healthy}")
        lines.append(f"  🟡 Stale/Warning    : {self.stale}")
        lines.append(f"  🔴 Critical         : {self.critical}")
        lines.append("=" * 60)

        # Critical list (if any)
        critical_repos = [r for r in self.repos if r.get("health_score", 100) < 50]
        if critical_repos:
            lines.append("\n⚠️  CRITICAL REPOS (Needs Immediate Attention):")
            for r in critical_repos[:5]:  # Limit to top 5
                lines.append(f"   - {r.get('name', 'Unknown')} (Score: {r.get('health_score', 0)})")
            if len(critical_repos) > 5:
                lines.append(f"   ... and {len(critical_repos) - 5} more.")

        # Stale list (if any)
        stale_repos = [r for r in self.repos if 50 <= r.get("health_score", 0) < 80]
        if stale_repos:
            lines.append("\n📌  STALE REPOS (Needs Review):")
            for r in stale_repos[:3]:
                lines.append(f"   - {r.get('name', 'Unknown')} ({r.get('status_message', 'Idle')})")

        if self.total == 0:
            lines.append("\n📭  No repositories analyzed.")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def generate_markdown(self) -> str:
        """Returns a markdown summary for READMEs or PR comments."""
        md = []
        md.append("# 📊 RepoForge Executive Summary")
        md.append(f"**Generated:** {self.generated}")
        md.append("")
        md.append("| Status | Count |")
        md.append("|--------|-------|")
        md.append(f"| 🟢 Healthy | {self.healthy} |")
        md.append(f"| 🟡 Stale | {self.stale} |")
        md.append(f"| 🔴 Critical | {self.critical} |")
        md.append(f"| **Total** | **{self.total}** |")
        md.append("")

        critical_repos = [r for r in self.repos if r.get("health_score", 100) < 50]
        if critical_repos:
            md.append("## ⚠️ Critical Repositories")
            for r in critical_repos:
                md.append(f"- **{r.get('name')}**: Score {r.get('health_score')} – {r.get('status_message', 'Unstable')}")
            md.append("")

        return "\n".join(md)

    def to_dict(self) -> Dict[str, Any]:
        """Returns the summary as a lightweight dict."""
        return {
            "generated": self.generated,
            "total": self.total,
            "healthy": self.healthy,
            "stale": self.stale,
            "critical": self.critical,
            "critical_repos": [
                {"name": r.get("name"), "score": r.get("health_score")}
                for r in self.repos if r.get("health_score", 100) < 50
            ],
        }