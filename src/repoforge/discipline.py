"""Run-scoped discipline decisions for RepoForge engineering agents.

The module returns permissions and review requirements; adapters enforce them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from time import time


class EnforcementLevel(IntEnum):
    CLEAR = 0
    NOTICE = 1
    READ_ONLY = 2
    ISOLATED_REVIEW = 3
    HALTED = 4


class EngineeringViolation(StrEnum):
    UNAPPROVED_WRITE = "unapproved_write"
    PROTECTED_PATH_CHANGE = "protected_path_change"
    DESTRUCTIVE_GIT = "destructive_git"
    REPEATED_VALIDATION_FAILURE = "repeated_validation_failure"
    REQUIREMENT_DEVIATION = "requirement_deviation"
    UNSAFE_DEPENDENCY = "unsafe_dependency"
    DRIFT_SIGNAL = "drift_signal"


@dataclass(frozen=True)
class RunEvidence:
    event_id: str
    violation: EngineeringViolation
    detail: str
    confidence: float
    severity: int
    run_id: str
    observed_at: float = field(default_factory=time)
    source: str = "validator"

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.run_id.strip() or not self.detail.strip():
            raise ValueError("event_id, run_id, and detail are required")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.severity not in range(1, 6):
            raise ValueError("severity must be from 1 to 5")


@dataclass(frozen=True)
class RunPolicy:
    level: EnforcementLevel
    writable: bool
    may_run_tests: bool
    may_install_dependencies: bool
    requires_owner_review: bool
    explanation: str
    evidence_ids: tuple[str, ...]


class RunDiscipline:
    """A per-run monotonic restriction policy; a new run starts with fresh state."""

    def __init__(self, run_id: str, *, confidence_floor: float = 0.9) -> None:
        if not run_id.strip():
            raise ValueError("run_id is required")
        if not 0.5 <= confidence_floor <= 1:
            raise ValueError("confidence_floor must be between 0.5 and 1")
        self.run_id = run_id
        self.confidence_floor = confidence_floor
        self._level = EnforcementLevel.CLEAR
        self._events: list[RunEvidence] = []
        self._seen: set[str] = set()
        self._halted = False

    @property
    def level(self) -> EnforcementLevel:
        return self._level

    @property
    def evidence(self) -> tuple[RunEvidence, ...]:
        return tuple(self._events)

    def record(self, evidence: RunEvidence) -> RunPolicy:
        if evidence.run_id != self.run_id:
            raise ValueError("evidence belongs to a different run")
        if evidence.event_id in self._seen:
            return self._policy("duplicate event ignored", review=False)
        self._seen.add(evidence.event_id)
        self._events.append(evidence)

        if self._halted:
            return self._policy("run is halted; start a new reviewed run", review=True)
        if evidence.confidence < self.confidence_floor or evidence.violation == EngineeringViolation.DRIFT_SIGNAL:
            return self._policy("weak/drift-only signal: request review, do not sanction", review=True)

        severe = evidence.severity >= 5 or (
            evidence.violation in {
                EngineeringViolation.DESTRUCTIVE_GIT,
                EngineeringViolation.UNAPPROVED_WRITE,
                EngineeringViolation.PROTECTED_PATH_CHANGE,
            } and evidence.severity >= 4
        )
        repeats = sum(e.violation == evidence.violation and e.confidence >= self.confidence_floor
                      for e in self._events) >= 2

        if severe:
            self._level = max(self._level, EnforcementLevel.ISOLATED_REVIEW)
            reason = "high-confidence destructive or critical engineering event"
        elif repeats and evidence.violation == EngineeringViolation.REPEATED_VALIDATION_FAILURE:
            self._level = max(self._level, EnforcementLevel.READ_ONLY)
            reason = "repeated validation failures: reset plan and remove write capability"
        elif evidence.severity >= 3:
            self._level = max(self._level, EnforcementLevel.READ_ONLY)
            reason = "engineering policy violation: read-only mode"
        else:
            self._level = max(self._level, EnforcementLevel.NOTICE)
            reason = "low-severity issue recorded"

        return self._policy(reason, review=self._level >= EnforcementLevel.ISOLATED_REVIEW)

    def halt(self, *, authenticated_owner: bool, reason: str) -> RunPolicy:
        if not authenticated_owner or not reason.strip():
            raise PermissionError("authenticated owner and reason are required")
        self._level = EnforcementLevel.HALTED
        self._halted = True
        return self._policy("owner halted this run", review=False)

    def _policy(self, explanation: str, *, review: bool) -> RunPolicy:
        writable = self._level < EnforcementLevel.READ_ONLY
        active = self._level < EnforcementLevel.HALTED
        return RunPolicy(
            level=self._level,
            writable=writable and active,
            may_run_tests=active and self._level < EnforcementLevel.ISOLATED_REVIEW,
            may_install_dependencies=active and self._level == EnforcementLevel.CLEAR,
            requires_owner_review=review,
            explanation=explanation,
            evidence_ids=tuple(e.event_id for e in self._events[-5:]),
        )
