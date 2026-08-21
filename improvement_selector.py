"""
RepoForge V4 Improvement Selector

Picks the best improvement(s) to execute from ranked issues.
"""

from typing import Any, Dict, List, Optional


class ImprovementSelector:
    """Selects top-ranked improvements. Returns None if repo looks healthy."""

    def select(
        self,
        ranked_issues: List[Dict[str, Any]],
        min_score: float = 0.15,
    ) -> Optional[Dict[str, Any]]:
        if not ranked_issues:
            return None

        top = ranked_issues[0]
        if float(top.get("value_score", 0.0) or 0.0) < min_score:
            return None

        return top

    def select_many(
        self,
        ranked_issues: List[Dict[str, Any]],
        limit: int = 5,
        min_score: float = 0.15,
    ) -> List[Dict[str, Any]]:
        selected = []
        for issue in ranked_issues:
            if float(issue.get("value_score", 0.0) or 0.0) < min_score:
                continue
            selected.append(issue)
            if len(selected) >= limit:
                break
        return selected
