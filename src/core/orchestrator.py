"""
RepoForge AI Orchestrator

Coordinates AI strategy, planning,
routing, execution, and merging.
"""


from repoforge.executor import AIExecutor
from repoforge.merger import ResultMerger
from repoforge.planner import TaskPlanner
from repoforge.router import AIRouter
from repoforge.strategist import AIStrategist



class AIOrchestrator:
    """
    Main RepoForge AI coordination engine.

    Flow:

    Prompt
      ↓
    Strategy
      ↓
    Planning
      ↓
    Model Routing
      ↓
    Execution
      ↓
    Merge Results
    """


    def __init__(self):

        self.strategist = AIStrategist()

        self.planner = TaskPlanner()

        self.router = AIRouter()

        self.executor = AIExecutor()

        self.merger = ResultMerger()



    def execute(
        self,
        prompt: str,
        model: str | None = None,
        context: dict | None = None,
    ):


        execution_plan = (
            self.strategist
            .create_plan(
                prompt
            )
        )



        tasks = (
            self.planner
            .plan(
                prompt,
                execution_plan,
            )
        )



        jobs = []



        for task in tasks:


            route = (
                self.router
                .choose(
                    task.task_type
                )
            )


            selected_model = (

                model

                if model

                else route["free"][0]

            )


            jobs.append(
                {

                    "task":
                        task.task_type,


                    "prompt":
                        task.title,


                    "context":
                        context,


                    "provider":
                        "openrouter",


                    "model":
                        selected_model,

                }
            )



        results = (
            self.executor
            .execute(
                jobs
            )
        )



        merged = (
            self.merger
            .merge(
                results
            )
        )



        response_parts = []


        for result in results:

            if isinstance(
                result,
                dict
            ):

                response_parts.append(
                    result.get(
                        "response",
                        ""
                    )
                )



        return {

            "response":

                "\n".join(
                    response_parts
                ),


            "results":

                results,


            "merged":

                merged,

        }