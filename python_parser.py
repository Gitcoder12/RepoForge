"""
RepoForge Python Intelligence Analyzer

Analyzes Python source code using AST.
"""

import ast
from typing import Dict, Any, List

from repoforge.intelligence.analyzer import CodeAnalyzer


class PythonAnalyzer(CodeAnalyzer):
    """
    Understands Python source structure.
    """


    def analyze(self) -> Dict[str, Any]:

        with open(
            self.file_path,
            "r",
            encoding="utf-8"
        ) as file:

            source = file.read()


        tree = ast.parse(
            source
        )


        result = {

            "file": self.file_path,

            "language": "python",

            "classes": [],

            "functions": [],

            "imports": [],

        }


        for node in ast.walk(tree):

            if isinstance(
                node,
                ast.ClassDef
            ):

                result["classes"].append(
                    {
                        "name": node.name,
                        "methods": [
                            m.name
                            for m in node.body
                            if isinstance(
                                m,
                                ast.FunctionDef
                            )
                        ]
                    }
                )


            elif isinstance(
                node,
                ast.FunctionDef
            ):

                result["functions"].append(
                    node.name
                )


            elif isinstance(
                node,
                ast.Import
            ):

                for item in node.names:

                    result["imports"].append(
                        item.name
                    )


            elif isinstance(
                node,
                ast.ImportFrom
            ):

                if node.module:

                    result["imports"].append(
                        node.module
                    )


        return result   