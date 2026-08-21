"""
RepoForge V4 Priority Engine

Calculates a value_score for each issue to determine the most impactful change.
"""

from typing import Any, Dict, List


class PriorityEngine:
    """Ranks issues by ROI (Impact vs Effort)."""

    def rank(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not issues:
            return []

        ranked = []
        for issue in issues:
            severity = float(issue.get("severity_score", 0.0) or 0.0)
            effort = float(issue.get("effort_estimate", 0.5) or 0.5)
            confidence = float(issue.get("confidence", 0.5) or 0.5)

            value_score = (severity * 0.50) + (confidence * 0.30) - (effort * 0.20)
            issue = dict(issue)
            issue["value_score"] = round(value_score, 4)
            issue["rationale"] = (
                f"Priority {issue.get('type')} "
                f"(Sev: {severity:.2f}, Effort: {effort:.2f}, Conf: {confidence:.2f}) "
                f"→ Score: {issue['value_score']:.3f}"
            )
            ranked.append(issue)

        ranked.sort(key=lambda x: x.get("value_score", 0.0), reverse=True)
        return ranked
