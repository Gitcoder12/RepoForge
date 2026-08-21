"""
Timeline Report Generator for RepoForge.
Tracks repository changes over time and generates a chronological summary.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json


class TimelineReport:
    """
    Generates a timeline of repository events (commits, status changes, fixes applied).
    Useful for understanding the evolution of a repository over time.
    """

    def __init__(self, report_data: Dict[str, Any], history_file: Optional[str] = None):
        """
        Args:
            report_data: Current scan report dict.
            history_file: Optional path to a JSON file containing previous scan data.
                         If provided, generates diff/timeline.
        """
        self.current = report_data
        self.repos = report_data.get("repos", [])
        self.generated = report_data.get("generated_at", datetime.now().isoformat())
        self.history = self._load_history(history_file) if history_file else {}

    def _load_history(self, path: str) -> Dict:
        """Load previous scan data from JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def generate(self) -> str:
        """Generate a human-readable timeline summary."""
        lines = []
        lines.append("=" * 60)
        lines.append("  REPOFORGE TIMELINE REPORT")
        lines.append(f"  Current Snapshot: {self.generated}")
        lines.append("=" * 60)
        lines.append("")

        # If we have history, show changes
        if self.history:
            prev_repos = self.history.get("repos", [])
            prev_map = {r.get("name"): r for r in prev_repos}
            curr_map = {r.get("name"): r for r in self.repos}

            all_names = set(prev_map.keys()) | set(curr_map.keys())

            lines.append("## 📈 Summary of Changes")
            lines.append("")

            improved = []
            declined = []
            new = []
            removed = []

            for name in all_names:
                prev = prev_map.get(name)
                curr = curr_map.get(name)

                if not prev and curr:
                    new.append(name)
                elif prev and not curr:
                    removed.append(name)
                elif prev and curr:
                    prev_score = prev.get("health_score", 0)
                    curr_score = curr.get("health_score", 0)
                    diff = curr_score - prev_score
                    if diff > 5:
                        improved.append((name, diff))
                    elif diff < -5:
                        declined.append((name, diff))

            if new:
                lines.append(f"🆕 **New Repos:** {', '.join(new)}")
            if removed:
                lines.append(f"🗑️ **Removed Repos:** {', '.join(removed)}")
            if improved:
                lines.append(f"📈 **Improved:**")
                for name, diff in improved[:5]:
                    lines.append(f"   - {name}: +{diff} points")
            if declined:
                lines.append(f"📉 **Declined:**")
                for name, diff in declined[:5]:
                    lines.append(f"   - {name}: {diff} points")

            if not (new or removed or improved or declined):
                lines.append("   No significant changes detected.")
            lines.append("")

        # Show recent commit activity from current repos
        lines.append("## 📝 Recent Commit Activity")
        lines.append("")
        lines.append("| Repo | Branch | Last Commit | Days Ago |")
        lines.append("|------|--------|-------------|----------|")

        for r in sorted(self.repos, key=lambda x: x.get("commit_date", ""), reverse=True)[:10]:
            name = r.get("name", "Unknown")
            branch = r.get("branch", "N/A")
            commit_msg = r.get("last_commit_msg", "N/A")[:25]
            commit_date = r.get("commit_date")
            if commit_date:
                try:
                    dt = datetime.fromisoformat(commit_date)
                    days_ago = (datetime.now() - dt).days
                except:
                    days_ago = "N/A"
            else:
                days_ago = "N/A"
            lines.append(f"| {name} | {branch} | {commit_msg} | {days_ago} |")

        lines.append("")

        # Health trend summary (if history available)
        if self.history:
            total_prev = self.history.get("total_repos", 0)
            total_curr = self.total_repos()
            healthy_prev = self.history.get("healthy", 0)
            healthy_curr = self.current.get("healthy", 0)

            lines.append("## 📊 Health Trend")
            lines.append("")
            lines.append(f"Total Repos: {total_prev} → {total_curr}")
            lines.append(f"Healthy:     {healthy_prev} → {healthy_curr}")

            if healthy_curr > healthy_prev:
                lines.append("✅ Overall health is improving.")
            elif healthy_curr < healthy_prev:
                lines.append("⚠️ Overall health is declining. Review critical repos.")
            else:
                lines.append("➖ Overall health is stable.")

            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def total_repos(self) -> int:
        return len(self.repos)

    def save(self, filepath: str) -> None:
        """Save timeline report to file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate())

    def to_dict(self) -> Dict[str, Any]:
        """Export timeline data as dict for JSON storage."""
        return {
            "generated": self.generated,
            "total_repos": len(self.repos),
            "repos": self.repos,
            "healthy": self.current.get("healthy", 0),
            "stale": self.current.get("stale", 0),
            "critical": self.current.get("critical", 0),
        }