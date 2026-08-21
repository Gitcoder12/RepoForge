"""
RepoForge V3 Backup Manager

Protects files before AI modifications.
"""

from pathlib import Path
import shutil
from datetime import datetime



class BackupManager:
    """
    Creates safe backups before patches.
    """


    def __init__(
        self,
        repo_path
    ):

        self.repo_path = Path(
            repo_path
        )

        self.backup_dir = (
            self.repo_path
            /
            ".repoforge"
            /
            "backups"
        )


        self.backup_dir.mkdir(
            parents=True,
            exist_ok=True
        )



    def create_backup(
        self,
        file_path
    ):

        """
        Create timestamped backup.

        Returns:
            backup path or None
        """


        file_path = Path(
            file_path
        )


        if not file_path.exists():

            return None



        timestamp = (
            datetime.now()
            .strftime(
                "%Y%m%d_%H%M%S"
            )
        )


        backup_name = (
            f"{file_path.name}.{timestamp}.bak"
        )


        backup_path = (
            self.backup_dir
            /
            backup_name
        )


        try:

            shutil.copy2(
                file_path,
                backup_path
            )


            if backup_path.exists():

                return backup_path


        except Exception:

            return None



        return None