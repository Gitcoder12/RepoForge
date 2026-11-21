"""Human-centered developer learning paths for RepoForge.

The lab turns a repository task into small, verifiable learning steps. It does
not modify source files or call an AI provider; execution remains in the normal
policy-controlled RepoForge pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LearningMode(str, Enum):
    AUTOMATIC = "automatic"
    GUIDED = "guided"
    MANUAL = "manual"


@dataclass(frozen=True)
class LearningStep:
    id: str
    title: str
    instruction: str
    evidence_to_check: str


@dataclass(frozen=True)
class LearningPath:
    mode: LearningMode
    steps: tuple[LearningStep, ...]


@dataclass(frozen=True)
class LearningProgress:
    completed_step_ids: tuple[str, ...]
    next_step_id: str | None
    is_complete: bool
    completion_percent: int


COMMON_STEPS = (
    LearningStep(
        "understand",
        "Understand the change",
        "State what the code is supposed to do and identify the relevant files.",
        "A concise description of expected behavior and affected files.",
    ),
    LearningStep(
        "inspect",
        "Inspect before editing",
        "Read the implementation, tests, configuration, and recent change history.",
        "A concrete explanation of current behavior and the suspected failure.",
    ),
    LearningStep(
        "predict",
        "Predict the result",
        "Write down the expected test result before running the test.",
        "A falsifiable prediction tied to a specific test or command.",
    ),
    LearningStep(
        "verify",
        "Verify the repair",
        "Run the narrow regression test, then the relevant lint and full test checks.",
        "Recorded command output with exit status and no hidden skipped checks.",
    ),
    LearningStep(
        "reflect",
        "Explain the lesson",
        "Explain the root cause, why the repair works, and what could regress.",
        "A short root-cause explanation and one regression-prevention idea.",
    ),
)


def build_learning_path(mode: LearningMode | str = LearningMode.GUIDED) -> LearningPath:
    """Create a learning path; all modes retain the same verification gates."""
    try:
        selected_mode = LearningMode(mode)
    except ValueError as exc:
        raise ValueError(f"unsupported learning mode: {mode}") from exc

    if selected_mode is LearningMode.AUTOMATIC:
        steps = (
            COMMON_STEPS[0],
            COMMON_STEPS[1],
            LearningStep(
                "review",
                "Review the proposed repair",
                "Inspect the diff and approve or reject each proposed change.",
                "Explicit human approval of the reviewed diff.",
            ),
            COMMON_STEPS[3],
            COMMON_STEPS[4],
        )
    elif selected_mode is LearningMode.MANUAL:
        steps = (
            LearningStep(
                "diagnose",
                "Diagnose independently",
                "Find the cause and propose a minimal repair without generated patches.",
                "A reproducible diagnosis and a patch authored by the learner.",
            ),
            COMMON_STEPS[2],
            COMMON_STEPS[3],
            COMMON_STEPS[4],
        )
    else:
        steps = COMMON_STEPS
    return LearningPath(mode=selected_mode, steps=steps)


def record_progress(
    path: LearningPath,
    completed_step_ids: tuple[str, ...] = (),
    *,
    verified_step_ids: tuple[str, ...] = (),
) -> LearningProgress:
    """Accept only sequentially completed steps with their evidence gate met."""
    known = tuple(step.id for step in path.steps)
    if len(set(completed_step_ids)) != len(completed_step_ids):
        raise ValueError("completed step IDs must be unique")
    if any(step_id not in known for step_id in completed_step_ids):
        raise ValueError("completed step ID is not part of this learning path")
    if any(step_id not in verified_step_ids for step_id in completed_step_ids):
        raise ValueError("each completed step must have its evidence verified")

    expected = known[: len(completed_step_ids)]
    if completed_step_ids != expected:
        raise ValueError("learning steps must be completed in order")

    total = len(known)
    completed = len(completed_step_ids)
    return LearningProgress(
        completed_step_ids=completed_step_ids,
        next_step_id=known[completed] if completed < total else None,
        is_complete=completed == total,
        completion_percent=round(completed * 100 / total),
    )
