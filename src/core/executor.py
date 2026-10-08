"""
RepoForge AI Executor V3

Executes AI tasks safely and returns
machine-readable Forge actions.
"""


from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

import traceback


from repoforge.models import (
    DEFAULT_MODEL,
    MODELS,
)

from repoforge.providers.factory import ProviderFactory
from repoforge.providers.spare import SpareModel



class AIExecutor:


    def __init__(self):

        self.factory = ProviderFactory()

        self.spare_model = SpareModel()




    def _build_prompt(
        self,
        prompt: str,
        context: dict,
    ) -> str:

        return f"""
You are RepoForge, an expert software engineer that improves real repositories safely.

REPOSITORY CONTEXT:
{context}

USER TASK:
{prompt}

OUTPUT RULES (STRICT):
- Respond with ONLY a valid JSON array. No markdown, no explanation, no code fences.
- Each item must be an object with keys: "type", "file", "content" (and optional "reason").
- type is one of: "modify", "create"
- file is a relative path only
- content is the FULL new file content (escape newlines as \n)
- Prefer small, high-value improvements: README clarity, missing LICENSE, basic tests, dependency pins, security hygiene, type hints, error handling.
- Do NOT invent huge rewrites. Do NOT delete working code.
- If nothing safe to change, return exactly: []

Example:
[
  {{"type":"modify","file":"README.md","content":"# Project\n\nClear description...","reason":"Improve docs"}},
  {{"type":"create","file":"LICENSE","content":"MIT License...","reason":"Add license"}}
]

Return ONLY the JSON array.
"""



    def _execute_task(
        self,
        job: dict,
    ):


        task_name = job.get(
            "task",
            "unknown",
        )


        provider_name = job.get(
            "provider",
            "openrouter",
        )


        model_name = job.get(
            "model",
            DEFAULT_MODEL,
        )


        prompt = job.get(
            "prompt",
            "",
        )


        context = job.get(
            "context",
            {},
        )


        try:


            provider = self.factory.create(
                provider_name
            )


            model_id = MODELS.get(
                model_name,
                MODELS[DEFAULT_MODEL],
            )


            response = provider.generate(

                self._build_prompt(
                    prompt,
                    context,
                ),

                model=model_id,

            )


            return {

                "task":
                    task_name,


                "provider":
                    provider_name,


                "model":
                    model_name,


                "success":
                    True,


                "response":
                    response,

            }



        except Exception as error:


            try:


                response = self.spare_model.generate(

                    self._build_prompt(
                        prompt,
                        context,
                    )

                )


                return {

                    "task":
                        task_name,


                    "provider":
                        "spare_model",


                    "model":
                        "spare",


                    "success":
                        True,


                    "response":
                        response,


                    "fallback_reason":
                        str(error),

                }



            except Exception:


                return {

                    "task":
                        task_name,


                    "provider":
                        "none",


                    "model":
                        "failed",


                    "success":
                        False,


                    "response":
                        "[]",


                    "traceback":
                        traceback.format_exc(),

                }



    def execute(
        self,
        jobs,
    ):


        if not jobs:

            return []



        results = []


        workers = min(
            len(jobs),
            5,
        )


        with ThreadPoolExecutor(
            max_workers=workers
        ) as executor:


            futures = [

                executor.submit(
                    self._execute_task,
                    job,
                )

                for job in jobs

            ]


            for future in as_completed(
                futures
            ):

                results.append(
                    future.result()
                )


        return results