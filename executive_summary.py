"""
RepoForge Executive Summary
"""

from typing import Dict, Any


class ExecutiveSummary:

    def generate(
        self,
        repository: Dict[str, Any],
        health: Dict[str, Any],
        risk: Dict[str, Any],
        validation: Dict[str, Any],
        execution: Dict[str, Any],
    ) -> Dict[str, Any]:

        return {

            "repository": repository.get("name", "Unknown"),

            "health_score": health.get("score"),

            "health_grade": health.get("grade"),

            "health_status": health.get("status"),

            "risk": risk.get("level"),

            "risk_score": risk.get("risk_score"),

            "validation": validation.get(
                "status",
                "UNKNOWN"
            ),

            "execution": execution.get(
                "status",
                "UNKNOWN"
            ),

            "tasks_completed":

                len(
                    execution.get(
                        "tasks",
                        []
                    )
                ),

            "summary":

                self._summary(
                    repository,
                    health,
                    risk,
                    validation,
                    execution
                )

        }

    def _summary(
        self,
        repository,
        health,
        risk,
        validation,
        execution
    ):

        return (
            f"{repository.get('name','Repository')} "
            f"Health {health.get('grade')} "
            f"({health.get('score')}/100). "
            f"Risk {risk.get('level')}. "
            f"Execution {execution.get('status')}. "
            f"Validation {validation.get('status','UNKNOWN')}."
        )