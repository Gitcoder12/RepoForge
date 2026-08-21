"""
RepoForge Reporter V3

Generates final execution reports.
"""


import json

from pathlib import Path
from datetime import datetime



class Reporter:


    def __init__(
        self,
        repo_path: str
    ):

        self.repo_path = Path(
            repo_path
        )


        self.report_path = (

            self.repo_path
            /
            ".repoforge"
            /
            "reports"

        )


        self.report_path.mkdir(

            parents=True,

            exist_ok=True

        )



    def generate(
        self,
        result: dict
    ):


        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )


        report = {

            "repository":
                str(self.repo_path),

            "timestamp":
                timestamp,

            "prompt":
                result.get(
                    "prompt",
                    ""
                ),

            "stages":
                result.get(
                    "stages",
                    {}
                )

        }



        file = (

            self.report_path
            /
            f"report_{timestamp}.json"

        )


        with open(

            file,

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                report,

                f,

                indent=4,

                default=str

            )



        return {

            "success":
                True,

            "report":
                str(file)

        }   