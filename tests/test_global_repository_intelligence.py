import pytest

from repoforge.intelligence.global_repository_intelligence import (
    RepositoryEvidence,
    explain_rank,
    rank_repositories,
)


def test_popularity_and_size_are_independent():
    rows = [
        {"full_name": "a/popular", "stars": 10000, "forks": 500, "size_kb": 2},
        {"full_name": "b/large", "stars": 10, "forks": 1, "size_kb": 900000},
    ]
    assert rank_repositories(rows, "popular")[0]["repository"] == "a/popular"
    assert rank_repositories(rows, "largest")[0]["repository"] == "b/large"


def test_missing_metrics_remain_unknown():
    rows = [{"full_name": "a/unknown"}, {"full_name": "b/known", "stars": 3}]
    ranked = rank_repositories(rows, "popular")
    assert [row["repository"] for row in ranked] == ["b/known"]
    assert ranked[0]["evidence_count"] == 1


def test_archived_and_forks_are_excluded_by_default():
    rows = [
        {"full_name": "a/active", "stars": 1},
        {"full_name": "b/archived", "stars": 999, "archived": True},
        {"full_name": "c/fork", "stars": 999, "fork": True},
    ]
    assert [r["repository"] for r in rank_repositories(rows)] == ["a/active"]
    assert len(rank_repositories(rows, include_forks=True)) == 2


def test_fastest_never_mixes_benchmark_cohorts():
    rows = [
        {"full_name": "a/fast", "benchmark_score": 99, "benchmark_id": "suite-a", "benchmark_environment": "linux-x86"},
        {"full_name": "b/slow", "benchmark_score": 20, "benchmark_id": "suite-a", "benchmark_environment": "linux-x86"},
        {"full_name": "c/different", "benchmark_score": 100, "benchmark_id": "suite-b", "benchmark_environment": "mac-arm"},
        {"full_name": "d/unverified", "benchmark_score": 100},
    ]
    ranked = rank_repositories(rows, "fastest")
    assert len(ranked) == 3
    assert ranked[0]["rank"] == 1
    assert ranked[1]["rank"] == 2
    assert ranked[2]["benchmark_id"] == "suite-b"


@pytest.mark.parametrize("record", [
    {"full_name": "x/y", "stars": -1},
    {"full_name": "x/y", "stars": True},
    {"full_name": "x/y", "benchmark_score": float("nan")},
    {"full_name": "x/y", "unexpected": 1},
    {"full_name": "invalid"},
    {"full_name": "owner/repo/extra"},
    {"full_name": " owner/repo"},
    {"full_name": "owner/repo ", "fork": "false"},
])
def test_rejects_invalid_evidence(record):
    with pytest.raises((ValueError, TypeError)):
        RepositoryEvidence.from_mapping(record)


@pytest.mark.parametrize("kwargs", [
    {"stars": True},
    {"benchmark_score": float("inf")},
    {"archived": 1},
    {"full_name": "bad/name/extra"},
])
def test_direct_dataclass_construction_cannot_bypass_validation(kwargs):
    with pytest.raises((ValueError, TypeError)):
        RepositoryEvidence(full_name="owner/repo", **kwargs)


def test_duplicate_names_are_case_insensitive():
    with pytest.raises(ValueError):
        rank_repositories([{"full_name": "A/Repo"}, {"full_name": "a/repo"}])


def test_explanation_contains_score_basis():
    row = rank_repositories([{"full_name": "x/y", "stars": 5}], "popular")[0]
    assert "stars" in explain_rank(row)


def test_explain_fastest_tolerates_partial_untrusted_mapping():
    explanation = explain_rank({"category": "fastest", "repository": "x/y"})
    assert "unknown benchmark" in explanation


def test_include_forks_must_be_boolean():
    with pytest.raises(TypeError):
        rank_repositories([], include_forks=1)
