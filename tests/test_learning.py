"""Tests for RepoForge's human-centered developer learning paths."""

import pytest

from repoforge.learning import (
    LearningMode,
    build_learning_path,
    record_progress,
)


@pytest.mark.parametrize("mode", list(LearningMode))
def test_each_mode_has_a_verified_learning_path(mode):
    path = build_learning_path(mode)
    assert path.steps
    assert path.steps[-1].id == "reflect"


def test_guided_path_requires_sequential_verified_evidence():
    path = build_learning_path("guided")
    with pytest.raises(ValueError, match="evidence verified"):
        record_progress(path, ("understand",))
    progress = record_progress(
        path,
        ("understand", "inspect"),
        verified_step_ids=("understand", "inspect"),
    )
    assert progress.completion_percent == 40
    assert progress.next_step_id == "predict"
    assert not progress.is_complete


def test_out_of_order_progress_is_rejected():
    path = build_learning_path()
    with pytest.raises(ValueError, match="in order"):
        record_progress(
            path,
            ("inspect",),
            verified_step_ids=("inspect",),
        )


def test_completed_path_is_one_hundred_percent():
    path = build_learning_path("manual")
    ids = tuple(step.id for step in path.steps)
    progress = record_progress(path, ids, verified_step_ids=ids)
    assert progress.is_complete
    assert progress.completion_percent == 100
    assert progress.next_step_id is None


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError, match="unsupported learning mode"):
        build_learning_path("telepathic")
