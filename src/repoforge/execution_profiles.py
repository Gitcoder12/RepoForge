"""User-controlled RepoForge execution speed, evolution depth and stop points.

This module resolves an execution contract. It does not execute target-repository code
or silently grant permission to apply changes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


STAGES = ("inspect", "plan", "patch", "validate", "iterate", "release_ready")
EVOLUTION_LEVELS = ("E0", "E1", "E2", "E3", "E4")


@dataclass(frozen=True)
class ExecutionProfile:
    name: str
    description: str
    max_minutes: int
    max_iterations: int
    stages: tuple[str, ...]


PROFILES = {
    "quick": ExecutionProfile(
        "quick", "Fast, focused repository pass.", 3, 0,
        ("inspect", "plan", "patch", "validate"),
    ),
    "standard": ExecutionProfile(
        "standard", "Balanced improvement with a bounded iteration.", 15, 1,
        ("inspect", "plan", "patch", "validate", "iterate"),
    ),
    "deep": ExecutionProfile(
        "deep", "Thorough, multi-stage repository evolution.", 45, 3, STAGES,
    ),
}


class ExecutionProfilePlanner:
    """Resolve profile settings into an explicit, inspectable execution contract."""

    def resolve(
        self,
        *,
        profile: str = "standard",
        stop_after: str | None = None,
        evolution: str = "E2",
        max_minutes: int | None = None,
        max_iterations: int | None = None,
    ) -> dict[str, Any]:
        if profile not in PROFILES:
            raise ValueError(f"profile must be one of: {', '.join(PROFILES)}")
        if evolution not in EVOLUTION_LEVELS:
            raise ValueError(f"evolution must be one of: {', '.join(EVOLUTION_LEVELS)}")

        selected = PROFILES[profile]
        stop = stop_after or selected.stages[-1]
        if stop not in selected.stages:
            raise ValueError(
                f"stop_after must be one of this profile's stages: {', '.join(selected.stages)}"
            )
        if max_minutes is not None and (
            isinstance(max_minutes, bool) or not isinstance(max_minutes, int) or max_minutes < 1
        ):
            raise ValueError("max_minutes must be a positive integer")
        if max_iterations is not None and (
            isinstance(max_iterations, bool)
            or not isinstance(max_iterations, int)
            or max_iterations < 0
        ):
            raise ValueError("max_iterations must be a non-negative integer")

        minute_budget = min(max_minutes, selected.max_minutes) if max_minutes else selected.max_minutes
        iteration_budget = (
            min(max_iterations, selected.max_iterations)
            if max_iterations is not None
            else selected.max_iterations
        )
        stop_index = selected.stages.index(stop)
        stages = list(selected.stages[: stop_index + 1])
        if "iterate" not in stages:
            iteration_budget = 0

        return {
            "engine": "RepoForge Execution Profiles",
            "profile": asdict(selected),
            "speed_mode": profile,
            "evolution_level": evolution,
            "stop_after": stop,
            "stages": stages,
            "budgets": {
                "max_minutes": minute_budget,
                "max_iterations": iteration_budget,
            },
            "controls": {
                "user_selected": True,
                "stop_point_enforced_by_plan": True,
                "target_code_execution": "not_authorized_by_profile",
                "changes_require_existing_approval_policy": True,
                "overwrite_delete_permission": False,
            },
            "notes": [
                "Speed mode controls execution budget, not quality guarantees.",
                "Evolution level is a requested scope, not a quality score.",
                "The profile does not override repository policy or approval gates.",
                "A stop point ends the planned workflow after the named stage.",
            ],
        }

    @staticmethod
    def should_stop(plan: dict[str, Any], completed_stage: str) -> bool:
        """Return True at or beyond the configured stop stage."""
        stages = plan.get("stages", [])
        stop_after = plan.get("stop_after")
        if completed_stage not in stages:
            raise ValueError(f"stage is not part of this plan: {completed_stage}")
        return stages.index(completed_stage) >= stages.index(stop_after)

    @staticmethod
    def remaining_stages(plan: dict[str, Any], completed_stage: str) -> list[str]:
        stages = plan.get("stages", [])
        if completed_stage not in stages:
            raise ValueError(f"stage is not part of this plan: {completed_stage}")
        return stages[stages.index(completed_stage) + 1 :]
