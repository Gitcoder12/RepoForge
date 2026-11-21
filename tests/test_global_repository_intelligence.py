import unittest

from global_repository_intelligence import (
    RepositoryEvidence, explain_rank, rank_repositories,
)


class RankingTests(unittest.TestCase):
    def test_popularity_is_not_size(self):
        rows = [
            {"full_name": "a/popular", "stars": 10000, "forks": 500},
            {"full_name": "b/large", "stars": 10, "forks": 1, "size_kb": 900000},
        ]
        popular = rank_repositories(rows, "popular")
        largest = rank_repositories(rows, "largest")
        self.assertEqual(popular[0]["repository"], "a/popular")
        self.assertEqual(largest[0]["repository"], "b/large")

    def test_missing_values_are_not_zero(self):
        rows = [{"full_name": "a/unknown"}, {"full_name": "b/known", "stars": 3}]
        ranked = rank_repositories(rows, "popular")
        self.assertEqual([row["repository"] for row in ranked], ["b/known"])
        self.assertEqual(ranked[0]["evidence_count"], 1)

    def test_fastest_requires_comparable_benchmark_metadata(self):
        rows = [
            {"full_name": "a/no-proof", "benchmark_score": 99},
            {"full_name": "b/proven", "benchmark_score": 80,
             "benchmark_id": "suite-v1", "benchmark_environment": "linux-x86"},
        ]
        ranked = rank_repositories(rows, "fastest")
        self.assertEqual([row["repository"] for row in ranked], ["b/proven"])

    def test_criticality_uses_dependency_evidence(self):
        rows = [
            {"full_name": "a/core", "dependents": 1000, "dependency_depth": 5},
            {"full_name": "b/isolated", "dependents": 2, "dependency_depth": 1},
        ]
        self.assertEqual(rank_repositories(rows, "critical")[0]["repository"], "a/core")

    def test_validation_and_explanation(self):
        with self.assertRaises(ValueError):
            RepositoryEvidence.from_mapping({"full_name": "x/y", "stars": -1})
        result = rank_repositories([{"full_name": "x/y", "stars": 1}], "popular")[0]
        self.assertIn("x/y ranked #1", explain_rank(result))


if __name__ == "__main__":
    unittest.main()
