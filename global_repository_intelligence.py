"""Evidence-aware repository ranking primitives for RepoForge.

This module ranks supplied GitHub metadata. It does not scrape GitHub or claim
that popularity is engineering quality. Missing evidence stays missing.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import log1p
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class RepositoryEvidence:
    full_name: str
    stars: int | None = None
    forks: int | None = None
    size_kb: int | None = None
    dependents: int | None = None
    dependency_depth: int | None = None
    open_security_alerts: int | None = None
    open_issues: int | None = None
    commits_30d: int | None = None
    contributors_90d: int | None = None
    benchmark_score: float | None = None
    benchmark_id: str | None = None
    benchmark_environment: str | None = None
    archived: bool = False
    fork: bool = False

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RepositoryEvidence":
        allowed = cls.__dataclass_fields__
        values = {key: data[key] for key in allowed if key in data}
        if not values.get("full_name"):
            raise ValueError("full_name is required")
        for key in ("stars", "forks", "size_kb", "dependents",
                    "dependency_depth", "open_security_alerts", "open_issues",
                    "commits_30d", "contributors_90d"):
            value = values.get(key)
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValueError(f"{key} must be a non-negative integer or None")
        score = values.get("benchmark_score")
        if score is not None and not 0 <= float(score) <= 100:
            raise ValueError("benchmark_score must be between 0 and 100")
        return cls(**values)


def _percentile_scores(items: list[RepositoryEvidence], field: str) -> dict[str, float]:
    present = [(getattr(item, field), item.full_name) for item in items
               if getattr(item, field) is not None]
    if not present:
        return {}
    values = [log1p(value) for value, _ in present]
    low, high = min(values), max(values)
    if high == low:
        return {name: 50.0 for _, name in present}
    return {name: round((log1p(value) - low) / (high - low) * 100, 2)
            for value, name in present}


def rank_repositories(records: Iterable[RepositoryEvidence | Mapping[str, Any]],
                      category: str = "popular") -> list[dict[str, Any]]:
    """Rank a batch by one evidence-backed category.

    Categories: popular, largest, trending, critical, fastest.
    Each result includes score provenance and an explicit evidence count.
    """
    items = [r if isinstance(r, RepositoryEvidence)
             else RepositoryEvidence.from_mapping(r) for r in records]
    if len({r.full_name for r in items}) != len(items):
        raise ValueError("repository full_name values must be unique")
    fields = {
        "popular": ("stars", "forks"),
        "largest": ("size_kb",),
        "trending": ("commits_30d", "contributors_90d"),
        "critical": ("dependents", "dependency_depth"),
    }
    if category == "fastest":
        eligible = [r for r in items if r.benchmark_score is not None
                    and r.benchmark_id and r.benchmark_environment]
        return [dict(repository=r.full_name, category=category,
                     score=round(float(r.benchmark_score), 2),
                     evidence_count=1, evidence=["benchmark_score"],
                     benchmark_id=r.benchmark_id,
                     benchmark_environment=r.benchmark_environment,
                     caveat="Comparable only within the same benchmark and environment.")
                for r in sorted(eligible, key=lambda x: x.benchmark_score, reverse=True)]
    if category not in fields:
        raise ValueError(f"unsupported category: {category}")
    score_maps = [_percentile_scores(items, field) for field in fields[category]]
    results = []
    for item in items:
        components = [(field, scores[item.full_name])
                      for field, scores in zip(fields[category], score_maps)
                      if item.full_name in scores]
        if not components:
            continue
        score = round(sum(value for _, value in components) / len(components), 2)
        results.append({
            "repository": item.full_name, "category": category, "score": score,
            "evidence_count": len(components),
            "evidence": [field for field, _ in components],
            "components": dict(components),
            "excluded_from_score": item.archived,
            "fork": item.fork,
            "caveat": "Relative score within this supplied batch; not a universal GitHub rank.",
        })
    results.sort(key=lambda row: (row["score"], row["repository"]), reverse=True)
    for position, row in enumerate(results, 1):
        row["rank"] = position
    return results


def explain_rank(result: Mapping[str, Any]) -> str:
    """Produce a compact human-readable explanation for a ranking row."""
    evidence = ", ".join(result.get("evidence", [])) or "no evidence"
    return (f"{result.get('repository', 'Unknown')} ranked "
            f"#{result.get('rank', '—')} in {result.get('category', 'unknown')}; "
            f"score {result.get('score', 'N/A')} from {evidence}. "
            f"{result.get('caveat', '')}").strip()


__all__ = ["RepositoryEvidence", "rank_repositories", "explain_rank"]
