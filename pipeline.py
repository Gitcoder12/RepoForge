import asyncio
import logging
from typing import Dict, Any
from .scanner import scan_repository
from .council import AgentCouncil
from .action_runner import ActionRunner
from .git_manager import GitManager
from .validator import Validator

logger = logging.getLogger("RepoForge.Pipeline")

class RepoForgePipeline:
    """The master orchestrator for RepoForge."""
    
    def __init__(self, repo_path: str, dry_run: bool = True):
        self.repo_path = repo_path
        self.dry_run = dry_run
        self.council = AgentCouncil()
        self.runner = ActionRunner(repo_path)
        self.git = GitManager(repo_path)
        self.validator = Validator(repo_path)

    async def run(self, prompt: str = "") -> Dict[str, Any]:
        logger.info(f"Starting RepoForge Pipeline on {self.repo_path}")
        
        # 1. Scan the repository (Night Vision)
        scan_data = scan_repository(self.repo_path)
        logger.info(f"Scanned {scan_data.get('statistics', {}).get('total_files', 0)} files.")
        
        # 2. Prepare context for the Council
        context = {"scan": scan_data, "prompt": prompt, "repo_path": self.repo_path}

        # 3. Convene the Council
        logger.info("Convening the Lethal Senate...")
        decision = await self.council.convene(context)
        
        if decision["status"] in ["failed", "deadlock", "ROGUE_VETO"]:
            logger.warning(f"Council halted: {decision['status']}. No actions taken.")
            return {"status": "halted", "reason": decision.get("reasoning", "No consensus")}

        # 4. Save Git Checkpoint
        logger.info("Creating Git checkpoint before applying changes...")
        if not self.git.save_state()["success"]:
            logger.warning("Could not create Git checkpoint. Proceeding with caution.")

        # 5. Execute the winning proposal
        # Map the winning proposal to the dict format your ActionRunner expects
        winning_action = {
            "type": "modify",
            "file": decision["target_file"],
            "content": decision["decision"]
        }

        logger.info(f"Executing action on {winning_action['file']}...")
        exec_result = self.runner.run([winning_action], dry_run=self.dry_run)

        # 6. Validate (The Shield)
        if not self.dry_run:
            logger.info("Validating changes...")
            val_result = await self.validator.validate(target_files=[winning_action["file"]])
            if not val_result["passed"]:
                logger.critical("Validation failed! Rolling back.")
                self.git.rollback()
                return {"status": "rollback", "error": val_result.get("reason")}

        logger.info("Pipeline completed successfully.")
        return {
            "status": "success", 
            "decision": decision,
            "execution": exec_result
        }
