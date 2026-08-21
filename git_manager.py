"""
RepoForge Git Manager V3

Handles:
- git detection
- checkpoints
- commits
- rollback
"""


from pathlib import Path
import subprocess
from typing import Dict, Any



class GitManager:
    """
    Safe Git operations for RepoForge.
    """



    def __init__(
        self,
        repo_path: str,
    ):

        self.repo_path = Path(
            repo_path
        ).resolve()



    def run_git(
        self,
        *args,
    ) -> Dict[str, Any]:

        try:

            result = subprocess.run(
                [
                    "git",
                    *args,
                ],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )


            return {

                "success":
                    result.returncode == 0,

                "output":
                    result.stdout.strip(),

                "error":
                    result.stderr.strip(),

            }


        except subprocess.TimeoutExpired:

            return {

                "success": False,

                "error":
                    "Git command timed out"

            }


        except Exception as error:

            return {

                "success": False,

                "error":
                    str(error)

            }



    def is_git_repo(self):

        result = self.run_git(
            "rev-parse",
            "--is-inside-work-tree",
        )


        return result["success"]



    def status(self):

        return self.run_git(
            "status",
            "--short",
        )



    def add_all(self):

        return self.run_git(
            "add",
            ".",
        )



    def commit(
        self,
        message: str,
    ):

        return self.run_git(
            "commit",
            "-m",
            message,
        )



    def save_state(
        self,
        message: str = "RepoForge AI improvement",
    ):

        if not self.is_git_repo():

            return {

                "success": False,

                "message":
                    "Not a git repository"

            }



        add_result = self.add_all()


        if not add_result["success"]:

            return {

                "success": False,

                "message":
                    "Git add failed: "
                    +
                    add_result.get(
                        "error",
                        ""
                    )

            }



        commit_result = self.commit(
            message
        )


        if not commit_result["success"]:

            error = commit_result.get(
                "error",
                ""
            )


            if "nothing to commit" in error.lower():

                return {

                    "success": True,

                    "message":
                        "No changes to commit"

                }



            return {

                "success": False,

                "message":
                    error

            }



        return {

            "success": True,

            "message":
                commit_result.get(
                    "output",
                    "Checkpoint created"
                )

        }



    def rollback(self):

        return self.run_git(
            "reset",
            "--hard",
            "HEAD",
        )