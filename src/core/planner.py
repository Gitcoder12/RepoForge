from __future__ import annotations

import time

from dataclasses import dataclass
from typing import List, Dict, Any

from repoforge.metrics import metrics


try:
    from repoforge.logger import logger
except Exception:
    logger = None



@dataclass
class Task:
    """
    Single executable RepoForge action.
    """

    title: str

    task_type: str

    priority: int = 1



class TaskPlanner:
    """
    Converts repository analysis
    into actionable improvement tasks.
    """


    def plan(
        self,
        prompt: str,
        execution_plan,
        context: Dict[str, Any] | None = None,
    ) -> List[Task]:

        start = time.perf_counter()


        if not prompt.strip():

            raise ValueError(
                "Prompt cannot be empty."
            )


        tasks = []


        try:

            # ---------------------------------
            # Repository improvement mode
            # ---------------------------------

            if context:

                issues = context.get(
                    "issues",
                    []
                )


                security = context.get(
                    "security",
                    []
                )


                todos = context.get(
                    "todos",
                    []
                )


                for issue in issues:

                    severity = issue.get(
                        "severity",
                        "medium"
                    )


                    priority = {

                        "high": 10,

                        "medium": 5,

                        "low": 2

                    }.get(
                        severity,
                        3
                    )


                    tasks.append(

                        Task(

                            title=
                            f"Fix {issue.get('message')}",

                            task_type=
                            issue.get(
                                "type",
                                "refactor"
                            ),

                            priority=
                            priority,

                        )

                    )


                if security:

                    tasks.append(

                        Task(

                            title=
                            "Review and remove security vulnerabilities",

                            task_type=
                            "security",

                            priority=
                            10,

                        )

                    )


                if todos:

                    tasks.append(

                        Task(

                            title=
                            "Resolve TODO and unfinished code",

                            task_type=
                            "maintenance",

                            priority=
                            4,

                        )

                    )


            # ---------------------------------
            # Generic AI building mode
            # ---------------------------------

            else:

                for role in execution_plan.roles:

                    tasks.append(

                        Task(

                            title=prompt,

                            task_type=role,

                            priority=1,

                        )

                    )


            duration = (
                time.perf_counter()
                - start
            )


            metrics.record_task(
                name="planner",
                duration=duration,
                success=True,
            )


            if logger:

                logger.info(
                    "planner",
                    f"Created {len(tasks)} tasks.",
                )


            return sorted(
                tasks,
                key=lambda x: x.priority,
                reverse=True,
            )


        except Exception:

            duration = (
                time.perf_counter()
                - start
            )


            metrics.record_task(
                name="planner",
                duration=duration,
                success=False,
            )

            raise