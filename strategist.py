"""
RepoForge AI Strategy Engine V3

Decides the best workflow
for repository improvement.

Now supports:
- Repository context
- Difficulty awareness
- Adaptive execution plans
"""


from dataclasses import dataclass
from typing import List, Dict, Any



@dataclass
class ExecutionPlan:
    """
    Strategy produced before execution.
    """

    mode: str

    roles: List[str]

    discussion_rounds: int

    review: bool

    parallel: bool



class AIStrategist:
    """
    Decides HOW RepoForge solves a problem.
    """



    def create_plan(
        self,
        prompt: str,
        context: Dict[str, Any] | None = None,
        difficulty: Dict[str, Any] | None = None,
    ) -> ExecutionPlan:


        text = prompt.lower()


        difficulty_level = "Normal"


        if difficulty:

            difficulty_level = difficulty.get(
                "level",
                "Normal"
            )



        # ---------------------------------------
        # Repository improvement mode
        # ---------------------------------------

        if context:


            roles = []


            issues = context.get(
                "issues",
                []
            )


            security = context.get(
                "security",
                []
            )



            if security:

                roles.append(
                    "security"
                )



            if issues:

                roles.append(
                    "analysis"
                )



            roles.extend(
                [
                    "testing",
                    "refactoring",
                    "documentation",
                ]
            )



            discussion_rounds = 1

            parallel = True



            # Extreme repositories
            # Example: LangChain

            if difficulty_level == "Extreme":


                roles.extend(
                    [
                        "architecture",
                        "security_review",
                    ]
                )


                discussion_rounds = 2

                parallel = False



            # Hard repositories

            elif difficulty_level == "Hard":


                roles.append(
                    "architecture"
                )


                discussion_rounds = 1

                parallel = True



            return ExecutionPlan(


                mode="repository_improvement",


                roles=list(
                    dict.fromkeys(
                        roles
                    )
                ),


                discussion_rounds=discussion_rounds,


                review=True,


                parallel=parallel,

            )



        # ---------------------------------------
        # Research
        # ---------------------------------------

        if any(

            word in text

            for word in

            [
                "research",
                "paper",
                "study",
                "analysis",
            ]

        ):


            return ExecutionPlan(


                mode="research",


                roles=[

                    "research",

                    "review",

                    "documentation",

                ],


                discussion_rounds=1,


                review=True,


                parallel=True,

            )



        # ---------------------------------------
        # Coding task
        # ---------------------------------------

        if any(

            word in text

            for word in

            [
                "code",
                "python",
                "java",
                "api",
                "algorithm",
            ]

        ):


            return ExecutionPlan(


                mode="coding",


                roles=[

                    "coding",

                    "testing",

                ],


                discussion_rounds=0,


                review=True,


                parallel=False,

            )



        # ---------------------------------------
        # General
        # ---------------------------------------

        return ExecutionPlan(


            mode="general",


            roles=[

                "general",

            ],


            discussion_rounds=0,


            review=False,


            parallel=False,

        )