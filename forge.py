from pathlib import Path
from typing import Dict, Any, List
from collections import Counter
import os
import re


class RepoScanner:
    """
    Core RepoForge repository intelligence engine.
    """

    IGNORE_DIRS = {
        ".git",
        ".idea",
        ".vscode",
        "__pycache__",
        "node_modules",
        "venv",
        ".venv",
        "dist",
        "build",
        "target",
        "coverage",
    }


    LANGUAGE_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "React",
        ".ts": "TypeScript",
        ".tsx": "React TypeScript",
        ".java": "Java",
        ".cpp": "C++",
        ".c": "C",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".cs": "C#",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".md": "Markdown",
        ".html": "HTML",
        ".css": "CSS",
    }


    SECRET_PATTERNS = [
        r"api[_-]?key\s*=",
        r"password\s*=",
        r"secret\s*=",
        r"token\s*=",
        r"private[_-]?key",
    ]


    def __init__(self, repo_path: str):

        self.repo_path = Path(
            repo_path
        ).resolve()


    def analyze(self) -> Dict[str, Any]:
        """
        Full repository analysis.
        """

        return {
            "project": self.repo_path.name,

            "structure":
                self.get_structure(),

            "languages":
                self.detect_languages(),

            "statistics":
                self.get_stats(),

            "todos":
                self.find_todos(),

            "security":
                self.security_scan(),

            "issues":
                self.detect_issues(),
        }


    def iter_files(self):

        for root, dirs, files in os.walk(
            self.repo_path
        ):

            dirs[:] = [
                d for d in dirs
                if d not in self.IGNORE_DIRS
            ]

            for file in files:

                path = Path(root) / file

                if not file.startswith("."):

                    yield path



    def get_structure(self):

        """
        Generate repository tree.
        """

        tree = {}

        for file in self.iter_files():

            relative = file.relative_to(
                self.repo_path
            )

            current = tree

            for part in relative.parts[:-1]:

                current = current.setdefault(
                    part,
                    {}
                )

            current[relative.parts[-1]] = True

        return tree



    def detect_languages(self):

        """
        Detect languages and file counts.
        """

        counter = Counter()


        for file in self.iter_files():

            language = self.LANGUAGE_MAP.get(
                file.suffix.lower()
            )

            if language:
                counter[language] += 1


        total = sum(counter.values()) or 1


        return {

            lang: {
                "files": count,
                "percentage": round(
                    count / total * 100,
                    2
                )
            }

            for lang, count in counter.items()

        }



    def get_stats(self):

        files = list(
            self.iter_files()
        )

        lines = 0
        extensions = Counter()


        for file in files:

            extensions[
                file.suffix.lower() or "none"
            ] += 1

            try:

                with open(
                    file,
                    encoding="utf-8",
                    errors="ignore"
                ) as f:

                    lines += sum(
                        1 for _ in f
                    )

            except Exception:
                pass


        return {

            "files":
                len(files),

            "lines":
                lines,

            "directories":
                len(
                    {
                        f.parent
                        for f in files
                    }
                ),

            "extensions":
                dict(extensions)

        }



    def find_todos(self):

        results = []

        keywords = [
            "TODO",
            "FIXME",
            "BUG",
            "HACK",
        ]


        for file in self.iter_files():

            try:

                text = file.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )


                for number, line in enumerate(
                    text.splitlines(),
                    1
                ):

                    for word in keywords:

                        if word in line.upper():

                            results.append({

                                "file":
                                    str(
                                        file.relative_to(
                                            self.repo_path
                                        )
                                    ),

                                "line":
                                    number,

                                "keyword":
                                    word,

                                "text":
                                    line.strip()

                            })

            except Exception:
                pass


        return results



    def security_scan(self):

        findings = []


        for file in self.iter_files():

            try:

                text = file.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )


                for pattern in self.SECRET_PATTERNS:

                    if re.search(
                        pattern,
                        text,
                        re.IGNORECASE
                    ):

                        findings.append({

                            "file":
                                str(
                                    file.relative_to(
                                        self.repo_path
                                    )
                                ),

                            "issue":
                                "Possible secret detected"

                        })

                        break


            except Exception:
                pass


        return findings



    def detect_issues(self):

        issues = []


        if not (
            self.repo_path /
            "README.md"
        ).exists():

            issues.append({

                "severity":
                    "high",

                "type":
                    "documentation",

                "message":
                    "Missing README.md"

            })


        if not (
            self.repo_path /
            "LICENSE"
        ).exists():

            issues.append({

                "severity":
                    "medium",

                "type":
                    "legal",

                "message":
                    "Missing LICENSE"

            })


        if not (
            self.repo_path /
            "tests"
        ).exists():

            issues.append({

                "severity":
                    "medium",

                "type":
                    "quality",

                "message":
                    "No test directory"

            })


        return issues