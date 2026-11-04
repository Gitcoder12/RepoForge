from pathlib import Path
import shutil
import logging

logger = logging.getLogger("RepoForge.Rollback")

class RollbackManager:
    def restore(self, backup_path: str, target_path: str) -> dict:
        if not backup_path:
            return {"success": False, "message": "No backup available"}

        backup = Path(backup_path)
        target = Path(target_path)

        if not backup.exists():
            logger.error(f"Backup not found: {backup}")
            return {"success": False, "message": "Backup not found"}

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            logger.info(f"⏪ Restored {target} from {backup}")
            return {"success": True, "message": "Rollback completed"}
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {"success": False, "message": f"Rollback failed: {e}"}
