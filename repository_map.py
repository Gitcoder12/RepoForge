"""
RepoForge Repository Intelligence Map

Builds a structural understanding of repositories.
"""

import os
from typing import Dict, Any, List


class RepositoryMap:
    """
    Creates repository architecture maps.
    """


    def __init__(
        self,
        repo_path: str,
    ):

        self.repo_path = repo_path



    def build(
        self,
    ) -> Dict[str, Any]:

        result = {

            "repository":
                os.path.basename(
                    os.path.abspath(
                        self.repo_path
                    )
                ),

            "files": [],

            "directories": [],

            "languages": {},

        }


        for root, dirs, files in os.walk(
            self.repo_path
        ):

            relative_root = os.path.relpath(
                root,
                self.repo_path
            )


            if relative_root != ".":
                result["directories"].append(
                    relative_root
                )


            for file in files:

                path = os.path.join(
                    root,
                    file
                )


                relative = os.path.relpath(
                    path,
                    self.repo_path
                )


                result["files"].append(
                    relative
                )


                language = self.detect_language(
                    file
                )


                if language:

                    result["languages"].setdefault(
                        language,
                        0
                    )

                    result["languages"][language] += 1


        return result



    def detect_language(
        self,
        filename: str,
    ):

        extension = os.path.splitext(
            filename
        )[1].lower()


        languages = {

            ".py": "Python",

            ".js": "JavaScript",

            ".ts": "TypeScript",

            ".java": "Java",

            ".cpp": "C++",

            ".go": "Go",

            ".rs": "Rust",

            ".html": "HTML",

            ".css": "CSS",

        }


        return languages.get(
            extension
        )