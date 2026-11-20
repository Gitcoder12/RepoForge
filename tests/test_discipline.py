import pytest

from repoforge.discipline import (
    EngineeringViolation, EnforcementLevel, RunDiscipline, RunEvidence,
)


def ev(run="r1", event="e1", violation=EngineeringViolation.REPEATED_VALIDATION_FAILURE,
       severity=3, confidence=0.99):
    return RunEvidence(event, violation, "observed in controlled run", confidence,
                       severity, run)


def test_repeated_validation_failure_removes_write_permission():
    policy = RunDiscipline("r1").record(ev())
    assert policy.level == EnforcementLevel.READ_ONLY
    assert not policy.writable


def test_critical_git_event_requires_isolated_owner_review():
    policy = RunDiscipline("r1").record(
        ev(violation=EngineeringViolation.DESTRUCTIVE_GIT, severity=5)
    )
    assert policy.level == EnforcementLevel.ISOLATED_REVIEW
    assert policy.requires_owner_review
    assert not policy.may_run_tests


def test_drift_or_low_confidence_does_not_punish():
    engine = RunDiscipline("r1")
    weak = engine.record(ev(confidence=0.2))
    assert weak.level == EnforcementLevel.CLEAR
    drift = engine.record(ev(event="e2", violation=EngineeringViolation.DRIFT_SIGNAL,
                             severity=5))
    assert drift.level == EnforcementLevel.CLEAR
    assert drift.requires_owner_review


def test_evidence_cannot_cross_runs():
    with pytest.raises(ValueError):
        RunDiscipline("r1").record(ev(run="r2"))


def test_duplicate_event_does_not_escalate():
    engine = RunDiscipline("r1")
    engine.record(ev(event="same", severity=3))
    policy = engine.record(ev(event="same", severity=5))
    assert policy.level == EnforcementLevel.READ_ONLY


def test_owner_halt_is_irreversible_for_current_run():
    engine = RunDiscipline("r1")
    policy = engine.halt(authenticated_owner=True, reason="stop requested")
    assert policy.level == EnforcementLevel.HALTED
    assert not policy.writable
    assert not policy.may_run_tests
    with pytest.raises(PermissionError):
        engine.halt(authenticated_owner=False, reason="agent says resume")
