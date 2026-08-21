"""
RepoForge Result Merger

Combines AI outputs into a structured
engineering result.
"""


import json
from typing import Any, Dict, List



class ResultMerger:
    """
    Combines multiple AI responses.
    """


    def merge(
        self,
        results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        successful = []
        failed = []


        actions = []


        for result in results:


            if result.get(
                "success"
            ):

                successful.append(
                    result
                )


                extracted = (
                    self.extract_actions(
                        result.get(
                            "response",
                            ""
                        )
                    )
                )


                actions.extend(
                    extracted
                )


            else:

                failed.append(
                    result
                )


        return {

            "summary":
                self.create_summary(
                    results
                ),

            "successful":
                successful,

            "failed":
                failed,

            "actions":
                actions,

        }



    def extract_actions(
        self,
        response: str,
    ):

        """
        Extract future Forge Engine actions.

        V1:
        Detect JSON blocks.
        """

        actions = []


        try:

            start = response.find(
                "{"
            )

            end = response.rfind(
                "}"
            )


            if (
                start != -1
                and end != -1
            ):

                data = json.loads(
                    response[
                        start:end + 1
                    ]
                )


                if isinstance(
                    data,
                    dict
                ):

                    actions.append(
                        data
                    )


        except Exception:

            pass


        return actions



    def create_summary(
        self,
        results,
    ):

        completed = sum(
            1
            for r in results
            if r.get("success")
        )


        return {

            "completed":
                completed,

            "total":
                len(results),

            "message":
                f"Completed {completed}/{len(results)} AI tasks"

        }