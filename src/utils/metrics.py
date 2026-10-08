"""
RepoForge Metrics Engine

Calculates repository quality scores.
"""

from typing import Dict, Any


class MetricsEngine:
    """
    Calculates software quality metrics.
    """


    def __init__(
        self,
        intelligence: Dict[str, Any],
    ):

        self.intelligence = intelligence



    def calculate(self) -> Dict[str, Any]:

        return {

            "health_score":
                self.health_score(),

            "metrics": {

                "documentation":
                    self.documentation_score(),

                "testing":
                    self.testing_score(),

                "security":
                    self.security_score(),

                "maintainability":
                    self.maintainability_score(),

            }

        }



    def health_score(self):

        metrics = self.calculate_raw()

        return sum(
            metrics.values()
        )



    def calculate_raw(self):

        return {

            "documentation":
                self.documentation_score(),

            "testing":
                self.testing_score(),

            "security":
                self.security_score(),

            "maintainability":
                self.maintainability_score(),

        }



    def documentation_score(self):

        score = 25


        if self.intelligence.get(
            "missing_readme",
            False
        ):

            score -= 10


        return max(
            score,
            0
        )



    def testing_score(self):

        if self.intelligence.get(
            "has_tests",
            False
        ):

            return 25


        return 10



    def security_score(self):

        issues = self.intelligence.get(
            "security",
            []
        )


        return max(
            25 - len(issues) * 5,
            0
        )



    def maintainability_score(self):

        issues = self.intelligence.get(
            "issues",
            []
        )


        return max(
            25 - len(issues) * 2,
            0
        )