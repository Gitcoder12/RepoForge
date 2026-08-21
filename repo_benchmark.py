"""
RepoForge Repository Benchmark V3

Measures repository improvement before and after Forge execution.
"""


from typing import Dict, Any



class RepoBenchmark:
    """
    Compares repository state before and after AI changes.
    """



    def calculate(
        self,
        intelligence: Dict[str, Any],
    ):

        quality = intelligence.get(
            "quality_score",
            {}
        )


        if isinstance(
            quality,
            dict
        ):

            score = quality.get(
                "score",
                0
            )

        else:

            score = 0



        return {

            "quality_score":
                score,


            "grade":
                self.grade(
                    score
                )

        }



    def compare(
        self,
        before,
        after
    ):


        improvement = (

            after["quality_score"]

            -

            before["quality_score"]

        )


        return {

            "before":
                before,


            "after":
                after,


            "improvement":
                improvement,


            "status":
                self.status(
                    improvement
                )

        }



    def status(
        self,
        value
    ):


        if value > 20:

            return "Major improvement 🚀"


        if value > 0:

            return "Improved ✅"


        if value == 0:

            return "No change ⚠️"


        return "Regression ❌"



    def grade(
        self,
        score
    ):


        if score >= 90:
            return "A"


        if score >= 75:
            return "B"


        if score >= 60:
            return "C"


        if score >= 40:
            return "D"


        return "F"