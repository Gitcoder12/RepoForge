"""
RepoForge V3 Patch Engine

Autonomous code improvement pipeline.

Flow:

Issue
 ↓
AI Fix Generator
 ↓
Backup
 ↓
Apply Patch
 ↓
Validate
 ↓
Rollback if failed
"""


from pathlib import Path

from repoforge.backup_manager import BackupManager
from repoforge.fix_generator import FixGenerator
from repoforge.validator import Validator
from repoforge.rollback_manager import RollbackManager



class PatchEngine:
    """
    Safely applies AI generated changes.
    """


    def __init__(
        self,
        repo_path
    ):

        self.repo_path = Path(
            repo_path
        )

        self.backup = BackupManager(
            repo_path
        )

        self.generator = FixGenerator()

        self.validator = Validator(
            repo_path
        )

        self.rollback = RollbackManager()



    def apply_fix(
        self,
        file_path,
        issue
    ):

        target = (
            self.repo_path
            /
            file_path
        )


        if not target.exists():

            return {

                "success": False,

                "message":
                    "File not found"

            }



        with open(
            target,
            "r",
            encoding="utf-8"
        ) as file:

            content = file.read()



        print(
            "🤖 Generating AI fix..."
        )


        new_content = self.generator.generate_fix(
            file_path,
            content,
            issue
        )


        if not new_content:

            return {

                "success": False,

                "message":
                    "AI returned empty output"

            }



        return self.apply_patch(
            file_path,
            new_content
        )



    def apply_patch(
        self,
        file_path,
        new_content
    ):


        target = (
            self.repo_path
            /
            file_path
        )


        print(
            "💾 Creating backup..."
        )


        backup = self.backup.create_backup(
            target
        )


        try:


            with open(
                target,
                "w",
                encoding="utf-8"
            ) as file:

                file.write(
                    new_content
                )



            print(
                "🧪 Validating..."
            )


            validation = self.validator.validate_file(
                file_path
            )



            if not validation["passed"]:


                print(
                    "❌ Validation failed. Rolling back..."
                )


                self.rollback.restore(
                    backup,
                    target
                )


                return {

                    "success": False,

                    "message":
                        "Patch rolled back"

                }



            print(
                "✅ Validation passed"
            )


            return {

                "success": True,

                "file":
                    str(target),

                "backup":
                    str(backup),

                "message":
                    "Patch applied and validated"

            }



        except Exception as error:


            self.rollback.restore(
                backup,
                target
            )


            return {

                "success": False,

                "message":
                    f"Patch failed: {error}"

            }