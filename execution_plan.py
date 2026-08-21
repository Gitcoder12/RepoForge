"""
RepoForge Execution Plan

Creates a safe, structured execution blueprint
before applying repository changes.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List


@dataclass
class ExecutionTask:
    name: str
    description: str
    priority: int
    risk: str
    files: List[str]
    reversible: bool = True


class ExecutionPlan:

    def __init__(self):
        self.tasks = []


    def create(
        self,
        action: Dict[str, Any],
        risk: Dict[str, Any],
        repository: Dict[str, Any],
    ) -> Dict[str, Any]:

        task = ExecutionTask(

            name=action.get(
                "title",
                "Repository improvement"
            ),

            description=action.get(
                "description",
                ""
            ),

            priority=action.get(
                "priority",
                1
            ),

            risk=risk.get(
                "level",
                "UNKNOWN"
            ),

            files=action.get(
                "files",
                []
            ),

            reversible=risk.get(
                "rollback_required",
                True
            )

        )


        self.tasks.append(task)


        return {

            "status": "READY",

            "repository":

                self._repository_name(
                    repository
                ),

            "risk":

                risk,

            "tasks":

                [
                    asdict(t)
                    for t in self.tasks
                ],

            "approval_required":

                self._approval_required(
                    risk
                ),

            "execution_order":

                self._order()

        }


    def _repository_name(
        self,
        repository
    ):

        return repository.get(
            "name",
            "unknown"
        )


    def _approval_required(
        self,
        risk
    ):

        level = risk.get(
            "level",
            "LOW"
        )


        return level in {
            "HIGH",
            "CRITICAL"
        }


    def _order(self):

        ordered = sorted(
            self.tasks,
            key=lambda x: x.priority
        )


        return [
            task.name
            for task in ordered
        ]


    def clear(self):

        self.tasks = []