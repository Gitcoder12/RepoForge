"""Deterministic, evidence-backed repository upgrade recommendations.

UpgradeForge proposes options; it does not invent project-specific code or apply
high-risk changes. Rank points describe available hygiene signals, not quality
improvement guarantees.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class UpgradeOption:
    id: str
    profile: str
    title: str
    why: str
    evidence: str
    impact: str
    effort: str
    risk: str
    rank_points_available: int
    implementation: str
    verification: str
    automation: str = "human_approved"
    priority_score: float = 0.0


class UpgradePlanner:
    """Turn detected RepoRank gaps into selectable, ranked upgrade paths."""

    PROFILES = ("all", "foundation", "security", "quality", "delivery", "maintainability")

    def build(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("signals"), dict):
            raise ValueError("snapshot must contain repository signals")
        signals = snapshot["signals"]
        rank = snapshot.get("rank", {})
        dimensions = rank.get("dimensions", {})
        options: list[UpgradeOption] = []

        def add(*, id: str, profile: str, title: str, why: str, evidence: str,
                impact: str, effort: str, risk: str, points: int,
                implementation: str, verification: str, automation: str = "human_approved") -> None:
            impact_weight = {"high": 3, "medium": 2, "low": 1}[impact]
            effort_weight = {"low": 1, "medium": 2, "high": 3}[effort]
            risk_weight = {"low": 0, "medium": 1, "high": 2}[risk]
            priority = round((impact_weight * 2 + points / 10) / effort_weight - risk_weight * 0.5, 2)  # noqa: E501
            options.append(UpgradeOption(id, profile, title, why, evidence, impact,
                                         effort, risk, points, implementation, verification,
                                         automation, priority))

        if not signals.get("readme", False):
            add(id="docs-readme", profile="foundation", title="Create a project-specific README",
                why="The repository has no root README, so users lack a reliable entry point.",
                evidence="No root-level README file was detected.", impact="high", effort="medium",
                risk="low", points=12,
                implementation="Draft purpose, installation, quick start, configuration, examples, limitations and support from verified project files; require maintainer review.",  # noqa: E501
                verification="Follow the instructions in a clean environment and check every command and feature claim.")  # noqa: E501
        if not signals.get("tests", False):
            add(id="tests-real", profile="quality", title="Add behavior-based tests",
                why="No recognisable test suite was detected.",
                evidence="No conventional test directory or test filename was found.",
                impact="high", effort="high", risk="medium", points=20,
                implementation="Identify critical user workflows and write tests against real behavior. Do not generate placeholder tests that merely pass.",  # noqa: E501
                verification="Run the suite in a clean environment; include failure-path and regression cases.")  # noqa: E501
        if not signals.get("ci", False):
            add(id="ci-pipeline", profile="delivery", title="Add continuous integration",
                why="Changes are not visibly checked by an automated CI workflow.",
                evidence="No supported CI workflow file was detected.",
                impact="high", effort="medium", risk="medium", points=20,
                implementation="Choose commands from the actual manifest and language stack; add lint, tests and build checks with pinned/runtime-supported versions.",  # noqa: E501
                verification="Run the workflow on a branch and confirm clean-install, test and lint jobs.")  # noqa: E501
        if not dimensions.get("project_configuration", 0):
            add(id="project-manifest", profile="foundation", title="Add a project manifest",
                why="No supported dependency/build manifest was detected.",
                evidence="No recognised project manifest was found.",
                impact="high", effort="medium", risk="medium", points=15,
                implementation="Identify the actual runtime and package manager, then add the matching manifest with explicit dependencies and supported versions.",  # noqa: E501
                verification="Install/build from a clean checkout without relying on undeclared global packages.")  # noqa: E501
        if not signals.get("license", False):
            add(id="license-choice", profile="foundation", title="Choose and add a license",
                why="Reuse and contribution permissions are unclear without a license.",
                evidence="No root-level LICENSE or COPYING file was detected.",
                impact="medium", effort="low", risk="high", points=10,
                implementation="Ask the maintainer to choose a license after considering ownership and third-party assets; never select one automatically.",  # noqa: E501
                verification="Confirm the license matches the owner's intent and dependency/asset obligations.")  # noqa: E501
        if not signals.get("gitignore", False):
            add(id="gitignore", profile="maintainability", title="Add baseline ignore rules",
                why="Local environments, caches and generated files may be committed accidentally.",
                evidence="No root .gitignore was detected.", impact="medium", effort="low",
                risk="low", points=5,
                implementation="Preview the conservative language-aware ignore rules; preserve existing files and custom patterns.",  # noqa: E501
                verification="Review ignored paths with git status --ignored and confirm no required source files are hidden.",  # noqa: E501
                automation="safe_create_only_available")
        if not signals.get("security_process", False):
            add(id="security-baseline", profile="security", title="Establish a security maintenance baseline",  # noqa: E501
                why="No recognised security policy or dependency-update configuration was detected.",  # noqa: E501
                evidence="No SECURITY.md, Dependabot configuration or CodeQL configuration was detected.",  # noqa: E501
                impact="high", effort="medium", risk="medium", points=10,
                implementation="Add a vulnerability reporting policy and configure dependency/code scanning appropriate to the repository's supported ecosystems.",  # noqa: E501
                verification="Validate workflow syntax, permissions, alert routing and a sample dependency update.")  # noqa: E501
        if not signals.get("quality_tooling", False):
            add(id="quality-tooling", profile="quality", title="Add consistent quality tooling",
                why="No recognised formatter, linter or editor configuration was detected.",
                evidence="No supported quality-tool configuration was found.",
                impact="medium", effort="low", risk="low", points=5,
                implementation="Select tools supported by the detected languages; add non-destructive baseline configuration and document commands.",  # noqa: E501
                verification="Run tools on a clean checkout and review all proposed formatting/lint changes.")  # noqa: E501

        options.sort(key=lambda item: (-item.priority_score, -item.rank_points_available, item.id))
        total_available = sum(item.rank_points_available for item in options)
        return {
            "engine": "UpgradeForge",
            "repository": snapshot.get("name", "unknown"),
            "current_rank": rank,
            "scan_complete": not bool(snapshot.get("scan_incomplete", True)),
            "profiles": list(self.PROFILES),
            "options": [asdict(item) for item in options],
            "summary": {
                "options_available": len(options),
                "rank_points_available": total_available,
                "points_note": "Maximum hygiene points associated with currently missing signals; not a predicted quality gain.",  # noqa: E501
                "automatic_changes": 0,
                "human_approval_required": sum(item.automation == "human_approved" for item in options),  # noqa: E501
            },
            "safety": {
                "default": "recommend_only",
                "no_target_code_execution": True,
                "no_overwrite_or_delete": True,
                "no_placeholder_tests": True,
                "no_automatic_license_choice": True,
            },
        }

    def select(self, report: dict[str, Any], *, profile: str = "all",
               option_ids: list[str] | None = None) -> dict[str, Any]:
        if profile not in self.PROFILES:
            raise ValueError(f"profile must be one of: {', '.join(self.PROFILES)}")
        available = report.get("options", [])
        known_ids = {item["id"] for item in available}
        if option_ids is not None:
            unknown = sorted(set(option_ids) - known_ids)
            if unknown:
                raise ValueError(f"unknown upgrade option(s): {', '.join(unknown)}")
            selected = [item for item in available if item["id"] in set(option_ids)]
        elif profile == "all":
            selected = list(available)
        else:
            selected = [item for item in available if item["profile"] == profile]
        result = dict(report)
        result["selected_profile"] = profile
        result["selected_options"] = selected
        result["selection_mode"] = "explicit_ids" if option_ids is not None else "profile"
        return result
