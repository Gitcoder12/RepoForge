"""
RepoForge Difficulty Engine V3

Calculates repository complexity.
"""


from typing import Dict, Any



class DifficultyEngine:


    def calculate(
        self,
        scan: Dict[str, Any]
    ):


        stats = scan.get(
            "statistics",
            {}
        )


        files = stats.get(
            "files",
            0
        )


        lines = stats.get(
            "lines",
            0
        )


        languages = len(
            scan.get(
                "languages",
                {}
            )
        )


        score = 0


        # Repository size

        if files > 100:
            score += 20

        if files > 1000:
            score += 20


        # Codebase size

        if lines > 100000:
            score += 20

        if lines > 500000:
            score += 20


        # Multiple technologies

        if languages > 3:
            score += 10



        if score >= 80:

            level = "Extreme"

        elif score >= 60:

            level = "Hard"

        elif score >= 30:

            level = "Medium"

        else:

            level = "Easy"



        return {

            "level":
                level,


            "score":
                min(
                    score,
                    100
                ),


            "metrics":
            {

                "files":
                    files,

                "lines":
                    lines,

                "languages":
                    languages

            }

        }