"""Evidence-aware repository ranking primitives for RepoForge."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log1p
from typing import Any, Iterable, Mapping, Sequence

CATEGORIES = ("popular", "largest", "trending", "critical", "fastest")
_METRICS = {
    "popular": ("stars", "forks"),
    "largest": ("size_kb",),
    "trending": ("commits_30d", "contributors_90d"),
    "critical": ("dependents", "dependency_depth"),
}
_INTEGER_FIELDS = (
    "stars", "forks", "size_kb", "dependents", "dependency_depth",
    "open_security_alerts", "open_issues", "commits_30d", "contributors_90d",
)


@dataclass(frozen=True, slots=True)
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
    measured_at: str | None = None

    def __post_init__(self) -> None:
        # Validate at construction so typed callers cannot bypass the mapping API.
        if (not isinstance(self.full_name, str) or self.full_name != self.full_name.strip()
                or self.full_name.count("/") != 1
                or any(not part or part in {".", ".."} or any(ch.isspace() for ch in part)
                       for part in self.full_name.split("/"))):
            raise ValueError("full_name must be a valid non-empty owner/repository identifier")
        for field in _INTEGER_FIELDS:
            value = getattr(self, field)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise ValueError(f"{field} must be a non-negative integer or None")
        score = self.benchmark_score
        if score is not None and (
            isinstance(score, bool) or not isinstance(score, (int, float))
            or not isfinite(score) or not 0 <= score <= 100
        ):
            raise ValueError("benchmark_score must be a finite number between 0 and 100")
        for field in ("benchmark_id", "benchmark_environment", "measured_at"):
            value = getattr(self, field)
            if value is not None and (
                not isinstance(value, str) or not value.strip() or value != value.strip()
            ):
                raise ValueError(f"{field} must be a non-empty trimmed string or None")
        for field in ("archived", "fork"):
            if not isinstance(getattr(self, field), bool):
                raise ValueError(f"{field} must be boolean")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RepositoryEvidence":
        if not isinstance(data, Mapping):
            raise TypeError("each record must be a mapping or RepositoryEvidence")
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"unknown evidence fields: {', '.join(sorted(unknown))}")
        return cls(**dict(data))


def _normalise(items: Sequence[RepositoryEvidence], field: str) -> dict[str, float]:
    present = [
        (log1p(getattr(item, field)), item.full_name)
        for item in items if getattr(item, field) is not None
    ]
    if not present:
        return {}
    low, high = min(value for value, _ in present), max(value for value, _ in present)
    if high == low:
        return {name: 50.0 for _, name in present}
    return {
        name: round((value - low) * 100 / (high - low), 2)
        for value, name in present
    }


def _rank_cohort(items: Sequence[RepositoryEvidence], category: str) -> list[dict[str, Any]]:
    metrics = _METRICS[category]
    normalised = [_normalise(items, field) for field in metrics]
    rows = []
    for item in items:
        parts = {
            field: scores[item.full_name]
            for field, scores in zip(metrics, normalised)
            if item.full_name in scores
        }
        if not parts:
            continue
        rows.append({
            "repository": item.full_name,
            "category": category,
            "score": round(sum(parts.values()) / len(parts), 2),
            "evidence_count": len(parts),
            "components": parts,
            "measured_at": item.measured_at,
            "method": "log1p_min_max_normalisation_within_supplied_cohort",
            "caveat": "Relative score within this supplied cohort; not a universal quality score.",
        })
    rows.sort(key=lambda row: (-row["score"], row["repository"].casefold()))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    return rows


def rank_repositories(
    records: Iterable[RepositoryEvidence | Mapping[str, Any]],
    category: str = "popular",
    *,
    include_forks: bool = False,
) -> list[dict[str, Any]]:
    """Rank evidence; fastest results are isolated by benchmark and environment."""
    if category not in CATEGORIES:
        raise ValueError(f"unsupported category {category!r}; choose from {', '.join(CATEGORIES)}")
    if not isinstance(include_forks, bool):
        raise TypeError("include_forks must be a boolean")
    items = [
        record if isinstance(record, RepositoryEvidence)
        else RepositoryEvidence.from_mapping(record)
        for record in records
    ]
    names = [item.full_name.casefold() for item in items]
    if len(names) != len(set(names)):
        raise ValueError("repository full_name values must be unique (case-insensitive)")
    items = [
        item for item in items
        if not item.archived and (include_forks or not item.fork)
    ]
    if category != "fastest":
        return _rank_cohort(items, category)

    cohorts: dict[tuple[str, str], list[RepositoryEvidence]] = {}
    for item in items:
        if item.benchmark_score is None or not item.benchmark_id or not item.benchmark_environment:
            continue
        cohorts.setdefault((item.benchmark_id, item.benchmark_environment), []).append(item)
    output = []
    for (benchmark_id, environment), cohort in sorted(cohorts.items()):
        ordered = sorted(
            cohort,
            key=lambda item: (-float(item.benchmark_score), item.full_name.casefold()),
        )
        for rank, item in enumerate(ordered, 1):
            output.append({
                "repository": item.full_name,
                "category": "fastest",
                "rank": rank,
                "score": round(float(item.benchmark_score), 2),
                "evidence_count": 1,
                "benchmark_id": benchmark_id,
                "benchmark_environment": environment,
                "measured_at": item.measured_at,
                "caveat": "Comparable only within this exact benchmark and environment cohort.",
            })
    return sorted(
        output,
        key=lambda row: (row["benchmark_id"], row["benchmark_environment"], row["rank"]),
    )


def explain_rank(result: Mapping[str, Any]) -> str:
    """Explain a rank without assuming optional fields are present."""
    if not isinstance(result, Mapping):
        raise TypeError("result must be a mapping")
    category = result.get("category", "unknown")
    if category == "fastest":
        benchmark_id = result.get("benchmark_id", "unknown benchmark")
        environment = result.get("benchmark_environment", "unknown environment")
        basis = f"benchmark {benchmark_id} on {environment}"
    else:
        components = result.get("components", {})
        basis = ", ".join(components.keys()) if isinstance(components, Mapping) else "unknown"
        basis = basis or "no available metrics"
    return (
        f"{result.get('repository', 'Unknown')} ranked #{result.get('rank', '—')} "
        f"in {category} with score {result.get('score', 'N/A')}; "
        f"basis: {basis}. {result.get('caveat', '')}"
    ).strip()


__all__ = ["CATEGORIES", "RepositoryEvidence", "rank_repositories", "explain_rank"]
