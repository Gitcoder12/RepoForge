"""Suggest complementary repository combinations without mutating either repo."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

from repoforge.blacksmith import Blacksmith

# Each relationship is a hypothesis about a useful integration boundary.
SYNERGY: dict[frozenset[str], int] = {
    frozenset({"frontend", "backend"}): 28,
    frozenset({"ai_ml", "data"}): 25,
    frozenset({"ai_ml", "evaluation"}): 25,
    frozenset({"ai_ml", "robotics"}): 25,
    frozenset({"ai_ml", "security"}): 22,
    frozenset({"backend", "data"}): 18,
    frozenset({"backend", "infrastructure"}): 16,
    frozenset({"evaluation", "security"}): 20,
    frozenset({"research", "ai_ml"}): 18,
    frozenset({"robotics", "security"}): 15,
    frozenset({"cli", "backend"}): 12,
    frozenset({"testing", "backend"}): 12,
    frozenset({"testing", "ai_ml"}): 12,
}

INTEGRATION_PATTERNS: dict[frozenset[str], tuple[str, str]] = {
    frozenset({"frontend", "backend"}): (
        "Product interface + service",
        (
            "Expose stable versioned HTTP/JSON contracts; keep UI and service "
            "deployable independently."
        ),
    ),
    frozenset({"ai_ml", "data"}): (
        "Data-to-model pipeline",
        (
            "Connect ingestion, validation and provenance to a versioned "
            "feature/dataset contract before model training or inference."
        ),
    ),
    frozenset({"ai_ml", "evaluation"}): (
        "Model + evaluation harness",
        (
            "Treat model outputs as candidates; run deterministic regression, "
            "adversarial and quality evaluations before release."
        ),
    ),
    frozenset({"ai_ml", "robotics"}): (
        "Perception/planning + robotics runtime",
        (
            "Use a simulator-first adapter boundary with explicit command "
            "schemas, rate limits and independent safety interlocks."
        ),
    ),
    frozenset({"ai_ml", "security"}): (
        "AI system + security controls",
        (
            "Place threat scanning and policy checks at the model/tool boundary; "
            "keep audit logs and human approval for high-impact actions."
        ),
    ),
    frozenset({"backend", "data"}): (
        "API + data platform",
        (
            "Connect through documented APIs or events and define ownership, "
            "schema versions and retry/idempotency rules."
        ),
    ),
    frozenset({"backend", "infrastructure"}): (
        "Service + deployment platform",
        (
            "Package the service with repeatable build and deployment definitions; "
            "add health checks and rollback procedures."
        ),
    ),
    frozenset({"evaluation", "security"}): (
        "Security test platform",
        "Turn security probes into repeatable tests with severity, evidence and regression gates.",
    ),
    frozenset({"research", "ai_ml"}): (
        "Research + model implementation",
        (
            "Bind datasets, experiment configurations, model versions and "
            "reported results to reproducible manifests."
        ),
    ),
    frozenset({"robotics", "security"}): (
        "Robotics + safety assurance",
        (
            "Keep safety monitors independent of the controller and verify "
            "command constraints in simulation before hardware trials."
        ),
    ),
}


class MegazordEngine:
    """Rank plausible repository pairings from local, inspectable signals."""

    def suggest(
        self,
        repo_paths: Iterable[str | Path],
        *,
        top_k: int = 10,
    ) -> dict[str, Any]:
        paths = tuple(Path(item).expanduser().resolve() for item in repo_paths)
        if len(paths) < 2:
            raise ValueError("provide at least two repository paths")
        if len(paths) > 30:
            raise ValueError("at most 30 repositories can be compared in one run")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        if len(set(paths)) != len(paths):
            raise ValueError("duplicate repository paths are not allowed")

        profiles = [Blacksmith(path).inspect() for path in paths]
        pairings = [self._pair(left, right) for left, right in combinations(profiles, 2)]
        pairings.sort(
            key=lambda item: (
                -item["fit_score"],
                item["repositories"][0]["name"].casefold(),
                item["repositories"][1]["name"].casefold(),
            )
        )
        return {
            "mode": "recommend_only",
            "repositories_analyzed": len(profiles),
            "pairings_evaluated": len(pairings),
            "method": (
                "heuristic capability complementarity and shared-language signals; "
                "not proof of technical compatibility"
            ),
            "repositories": [
                {
                    "name": profile["name"],
                    "path": profile["path"],
                    "capabilities": profile["capabilities"],
                    "languages": profile["languages"],
                    "repo_rank": profile["rank"]["score"],
                }
                for profile in profiles
            ],
            "suggestions": pairings[:top_k],
            "notices": [
                "No source files are changed or merged.",
                "Dependency, licence, API and data-contract compatibility still require review.",
                "Capabilities are inferred from names, README text and repository structure.",
            ],
        }

    @staticmethod
    def _pair(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
        left_caps = set(left["capabilities"])
        right_caps = set(right["capabilities"])
        shared = sorted(set(left["languages"]).intersection(right["languages"]))
        matches: list[dict[str, Any]] = []
        for relation, weight in SYNERGY.items():
            capability_a, capability_b = tuple(relation)
            spans_both_repositories = (
                capability_a in left_caps and capability_b in right_caps
            ) or (capability_b in left_caps and capability_a in right_caps)
            if spans_both_repositories:
                matches.append(
                    {
                        "capabilities": sorted(relation),
                        "weight": weight,
                    }
                )

        matches.sort(key=lambda item: (-item["weight"], item["capabilities"]))
        relationship_points = sum(item["weight"] for item in matches[:3])
        language_points = min(15, 5 * len(shared))
        fit_score = min(100, relationship_points + language_points)
        combined = sorted(left_caps | right_caps)
        patterns = []
        for relation, (title, approach) in INTEGRATION_PATTERNS.items():
            capability_a, capability_b = tuple(relation)
            spans_both_repositories = (
                capability_a in left_caps and capability_b in right_caps
            ) or (capability_b in left_caps and capability_a in right_caps)
            if spans_both_repositories:
                patterns.append({"pattern": title, "approach": approach})
        if not patterns:
            patterns.append(
                {
                    "pattern": "Adapter-based integration",
                    "approach": (
                        "Identify one concrete shared workflow, define a versioned interface, "
                        "and integrate through an adapter rather than merging repositories."
                    ),
                }
            )

        risks = [
            "Review dependency versions and runtime requirements before connecting the projects.",
            "Confirm both repositories' licences permit the intended combined distribution.",
            "Define integration ownership, error handling, observability, and rollback.",
        ]
        if len(set(left["languages"]) | set(right["languages"])) > 3:
            risks.append(
                "Several languages are involved; prefer a neutral API or event contract."
            )
        if not left["manifests"] or not right["manifests"]:
            risks.append(
                "A package manifest is missing; runtime dependencies may be undocumented."
            )

        return {
            "repositories": [
                {
                    "name": left["name"],
                    "path": left["path"],
                    "capabilities": sorted(left_caps),
                    "repo_rank": left["rank"]["score"],
                },
                {
                    "name": right["name"],
                    "path": right["path"],
                    "capabilities": sorted(right_caps),
                    "repo_rank": right["rank"]["score"],
                },
            ],
            "fit_score": fit_score,
            "shared_languages": shared,
            "complementarity": matches,
            "combined_capabilities": combined,
            "integration_blueprint": patterns,
            "risks_to_resolve": risks,
        }
