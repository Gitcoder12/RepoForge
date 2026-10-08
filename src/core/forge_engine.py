"""
RepoForge Forge Engine

Responsible for safely applying
AI generated repository improvements.
"""

from pathlib import Path
import shutil
from datetime import datetime
from typing import Dict, Any


class ForgeEngine:
    """
    Safely modifies repositories.
    """


    def __init__(
        self,
        repo_path: str,
    ):

        self.repo_path = Path(
            repo_path
        ).resolve()

        self.backup_dir = (
            self.repo_path /
            ".repoforge_backup"
        )


    # ==========================================
    # Backup
    # ==========================================

    def backup_file(
        self,
        file_path: Path,
    ):

        if not file_path.exists():
            return None


        self.backup_dir.mkdir(
            exist_ok=True
        )


        timestamp = (
            datetime.now()
            .strftime("%Y%m%d_%H%M%S")
        )


        backup = (
            self.backup_dir /
            f"{file_path.name}.{timestamp}.bak"
        )


        shutil.copy2(
            file_path,
            backup,
        )


        return backup



    # ==========================================
    # Read
    # ==========================================

    def read_file(
        self,
        relative_path: str,
    ) -> str:


        path = (
            self.repo_path /
            relative_path
        )


        if not path.exists():

            raise FileNotFoundError(
                relative_path
            )


        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )



    # ==========================================
    # Modify existing file
    # ==========================================

    def modify_file(
        self,
        relative_path: str,
        content: str,
    ) -> Dict[str, Any]:


        path = (
            self.repo_path /
            relative_path
        )


        self.backup_file(
            path
        )


        path.write_text(
            content,
            encoding="utf-8",
        )


        return {

            "action":
                "modified",

            "file":
                relative_path,

            "success":
                True,

        }



    # ==========================================
    # Create new file
    # ==========================================

    def create_file(
        self,
        relative_path: str,
        content: str,
    ) -> Dict[str, Any]:


        path = (
            self.repo_path /
            relative_path
        )


        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )


        if path.exists():

            return {

                "action":
                    "skipped",

                "reason":
                    "File already exists",

            }


        path.write_text(
            content,
            encoding="utf-8",
        )


        return {

            "action":
                "created",

            "file":
                relative_path,

            "success":
                True,

        }



    # ==========================================
    # Apply AI action
    # ==========================================

    def apply_action(
        self,
        action: Dict[str, Any],
    ):

        action_type = action.get(
            "type"
        )


        if action_type == "modify":

            return self.modify_file(
                action["file"],
                action["content"],
            )


        if action_type == "create":

            return self.create_file(
                action["file"],
                action["content"],
            )


        return {

            "success":
                False,

            "error":
                "Unknown action type",

        }