"""
RepoForge Risk Assessment Engine

Evaluates the risk of proposed repository changes
before execution.
"""

from typing import Dict, Any, List


class RiskAssessor:
    """
    Calculates execution risk based on:
    - Files affected
    - Change type
    - Repository size
    - Confidence
    - Severity
    """

    def __init__(self):

        self.risk_weights = {

            "file_count": 0.30,
            "change_type": 0.25,
            "repository_size": 0.20,
            "confidence": 0.15,
            "severity": 0.10

        }


    def assess(
        self,
        action: Dict[str, Any],
        repository: Dict[str, Any],
    ) -> Dict[str, Any]:

        scores = {

            "file_count":
                self._file_risk(action),

            "change_type":
                self._change_risk(action),

            "repository_size":
                self._repository_risk(repository),

            "confidence":
                self._confidence_risk(action),

            "severity":
                self._severity_risk(action)

        }


        risk_score = self._calculate(
            scores
        )


        return {

            "risk_score": risk_score,

            "level":
                self._level(
                    risk_score
                ),

            "safe_to_execute":
                risk_score < 70,

            "requires_backup":
                True,

            "rollback_required":
                risk_score > 40,

            "breakdown":
                scores

        }


    def _file_risk(
        self,
        action
    ):

        files = action.get(
            "files",
            []
        )

        count = len(files)


        if count <= 1:
            return 10

        if count <= 5:
            return 30

        if count <= 20:
            return 60

        return 90



    def _change_risk(
        self,
        action
    ):

        change_type = action.get(
            "type",
            "unknown"
        )


        risks = {

            "documentation": 10,

            "formatting": 15,

            "test": 30,

            "dependency": 60,

            "architecture": 75,

            "security": 80,

            "unknown": 50

        }


        return risks.get(
            change_type,
            50
        )



    def _repository_risk(
        self,
        repository
    ):

        stats = repository.get(
            "statistics",
            {}
        )


        files = stats.get(
            "files",
            0
        )


        if files < 500:
            return 10

        if files < 5000:
            return 40

        return 70



    def _confidence_risk(
        self,
        action
    ):

        confidence = action.get(
            "confidence",
            0.5
        )


        return int(
            (1 - confidence)
            *
            100
        )



    def _severity_risk(
        self,
        action
    ):

        severity = action.get(
            "severity",
            "low"
        )


        values = {

            "low": 10,

            "medium": 40,

            "high": 70,

            "critical": 90

        }


        return values.get(
            severity,
            50
        )



    def _calculate(
        self,
        scores
    ):

        total = 0


        for key, weight in self.risk_weights.items():

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



    def _level(
        self,
        score
    ):

        if score < 30:
            return "LOW"

        if score < 60:
            return "MEDIUM"

        if score < 80:
            return "HIGH"

        return "CRITICAL"