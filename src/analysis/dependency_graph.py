"""
RepoForge Dependency Graph

Analyzes relationships between source files.
"""

import os
import ast
from typing import Dict, Any, List


class DependencyGraph:
    """
    Builds repository dependency relationships.
    """


    def __init__(
        self,
        repo_path: str,
    ):

        self.repo_path = repo_path



    def build(self) -> Dict[str, Any]:

        graph = {

            "nodes": [],

            "edges": []

        }


        for root, _, files in os.walk(
            self.repo_path
        ):

            for file in files:

                if not file.endswith(
                    ".py"
                ):
                    continue


                path = os.path.join(
                    root,
                    file
                )


                relative = os.path.relpath(
                    path,
                    self.repo_path
                )


                graph["nodes"].append(
                    relative
                )


                dependencies = self.extract_imports(
                    path
                )


                for dependency in dependencies:

                    graph["edges"].append(

                        {

                            "source":
                                relative,

                            "target":
                                dependency

                        }

                    )


        return graph



    def extract_imports(
        self,
        file_path: str,
    ) -> List[str]:

        imports = []


        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                tree = ast.parse(
                    file.read()
                )


            for node in ast.walk(tree):

                if isinstance(
                    node,
                    ast.Import
                ):

                    for item in node.names:

                        imports.append(
                            item.name
                        )


                elif isinstance(
                    node,
                    ast.ImportFrom
                ):

                    if node.module:

                        imports.append(
                            node.module
                        )


        except Exception:

            pass


        return imports