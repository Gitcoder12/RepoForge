from __future__ import annotations

import pytest

from repoforge.execution_profiles import ExecutionProfilePlanner


def test_quick_profile_is_bounded_and_stops_after_validation():
    plan = ExecutionProfilePlanner().resolve(profile="quick")
    assert plan["stages"] == ["inspect", "plan", "patch", "validate"]
    assert plan["budgets"] == {"max_minutes": 3, "max_iterations": 0}
    assert plan["stop_after"] == "validate"


def test_speed_mode_and_evolution_depth_are_independent():
    planner = ExecutionProfilePlanner()
    quick = planner.resolve(profile="quick", evolution="E4")
    deep = planner.resolve(profile="deep", evolution="E1")
    assert quick["speed_mode"] == "quick"
    assert quick["evolution_level"] == "E4"
    assert deep["speed_mode"] == "deep"
    assert deep["evolution_level"] == "E1"


def test_user_can_stop_after_any_supported_stage():
    plan = ExecutionProfilePlanner().resolve(profile="deep", stop_after="plan")
    assert plan["stages"] == ["inspect", "plan"]
    assert ExecutionProfilePlanner.should_stop(plan, "plan")
    assert ExecutionProfilePlanner.remaining_stages(plan, "inspect") == ["plan"]


def test_profile_budgets_can_be_reduced_but_not_increased():
    plan = ExecutionProfilePlanner().resolve(
        profile="quick", max_minutes=100, max_iterations=10
    )
    assert plan["budgets"] == {"max_minutes": 3, "max_iterations": 0}


@pytest.mark.parametrize("kwargs", [
    {"profile": "turbo"}, {"evolution": "E9"},
    {"profile": "quick", "stop_after": "release_ready"},
    {"max_minutes": 0}, {"max_iterations": -1},
])
def test_invalid_profile_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        ExecutionProfilePlanner().resolve(**kwargs)


def test_stop_detection_rejects_unknown_stage():
    plan = ExecutionProfilePlanner().resolve(profile="standard")
    with pytest.raises(ValueError):
        ExecutionProfilePlanner.should_stop(plan, "release_ready")


def test_profile_does_not_authorize_execution_or_overwrites():
    plan = ExecutionProfilePlanner().resolve(profile="deep")
    assert plan["controls"]["target_code_execution"] == "not_authorized_by_profile"
    assert plan["controls"]["overwrite_delete_permission"] is False
