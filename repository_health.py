"""
RepoForge Repository Health Engine

Analyzes repository quality across:
- Documentation
- Testing
- Security
- Maintainability
- Dependencies
- CI/CD
"""

from typing import Dict, Any


class RepositoryHealth:


    def __init__(self):

        self.weights = {

            "documentation": 0.15,
            "testing": 0.20,
            "security": 0.20,
            "maintainability": 0.20,
            "dependencies": 0.15,
            "ci": 0.10

        }


    def analyze(
        self,
        scan: Dict[str, Any],
        metadata: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:


        metadata = metadata or {}

        scores = {

            "documentation":
                self._documentation(metadata),

            "testing":
                self._testing(metadata),

            "security":
                self._security(scan, metadata),

            "maintainability":
                self._maintainability(scan),

            "dependencies":
                self._dependencies(metadata),

            "ci":
                self._ci(metadata)

        }


        overall = self._calculate(
            scores
        )


        return {

            "score": overall,

            "grade":
                self._grade(overall),

            "breakdown":
                scores,

            "status":
                self._status(overall)

        }



    def _documentation(self, metadata):

        score = 0


        if metadata.get(
            "readme",
            False
        ):
            score += 50


        if metadata.get(
            "docs",
            False
        ):
            score += 30


        if metadata.get(
            "license",
            False
        ):
            score += 20


        return min(
            score,
            100
        )



    def _testing(self, metadata):

        if metadata.get(
            "tests",
            False
        ):
            return 100


        return 30



    def _security(
        self,
        scan,
        metadata
    ):

        score = 100


        if metadata.get(
            "docker",
            False
        ):
            score -= 5


        if scan.get(
            "statistics",
            {}
        ).get(
            "files",
            0
        ) > 10000:

            score -= 10


        return max(
            score,
            0
        )



    def _maintainability(
        self,
        scan
    ):

        files = scan.get(
            "statistics",
            {}
        ).get(
            "files",
            0
        )


        lines = scan.get(
            "statistics",
            {}
        ).get(
            "lines",
            0
        )


        score = 100


        if files > 5000:
            score -= 10


        if lines > 500000:
            score -= 10


        return max(
            score,
            0
        )



    def _dependencies(
        self,
        metadata
    ):

        if metadata.get(
            "package_manager",
            None
        ):

            return 90


        return 50



    def _ci(self, metadata):

        if metadata.get(
            "ci",
            False
        ):

            return 100


        return 40



    def _calculate(
        self,
        scores
    ):

        total = 0


        for key, weight in self.weights.items():

            total += (
                scores.get(
                    key,
                    0
                )
                *
                weight
            )


        return round(
            total
        )



    def _grade(
        self,
        score
    ):

        if score >= 90:
            return "A"


        if score >= 80:
            return "B"


        if score >= 70:
            return "C"


        if score >= 60:
            return "D"


        return "F"



    def _status(
        self,
        score
    ):

        if score >= 85:
            return "Healthy"


        if score >= 70:
            return "Needs Improvement"


        return "Critical"