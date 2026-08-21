"""
RepoForge V3 Rollback Manager

Restores files when AI changes fail validation.
"""


from pathlib import Path
import shutil



class RollbackManager:
    """
    Safely restores original files.
    """



    def restore(
        self,
        backup_path,
        target_path
    ):
        """
        Restore original file from backup.
        """


        if not backup_path:

            return {

                "success": False,

                "message":
                    "No backup available"

            }



        backup = Path(
            backup_path
        )


        target = Path(
            target_path
        )



        if not backup.exists():

            return {

                "success": False,

                "message":
                    "Backup not found"

            }



        try:

            target.parent.mkdir(
                parents=True,
                exist_ok=True
            )


            shutil.copy2(
                backup,
                target
            )


            return {

                "success": True,

                "message":
                    "Rollback completed"

            }



        except Exception as error:


            return {

                "success": False,

                "message":
                    f"Rollback failed: {error}"

            }