import logging
from typing import Dict, Any

from .scanner import scan_repository
from .council import AgentCouncil
from .action_runner import ActionRunner
from .git_manager import GitManager
from .validator import Validator

logger = logging.getLogger("RepoForge.Pipeline")


class RepoForgePipeline:
    """The master orchestrator for RepoForge with explicit mutation approval."""

    def __init__(self, repo_path: str, dry_run: bool = True):
        self.repo_path = repo_path
        self.dry_run = dry_run
        self.council = AgentCouncil()
        self.runner = ActionRunner(repo_path)
        self.git = GitManager(repo_path)
        self.validator = Validator(repo_path)

    async def run(
        self,
        prompt: str = "",
        *,
        approved_paths: set[str] | None = None,
        allow_delete: bool = False,
    ) -> Dict[str, Any]:
        logger.info("Starting RepoForge Pipeline on %s", self.repo_path)

        scan_data = scan_repository(self.repo_path)
        logger.info("Scanned %s files.", scan_data.get("statistics", {}).get("total_files", 0))
        context = {"scan": scan_data, "prompt": prompt, "repo_path": self.repo_path}

        logger.info("Convening the Lethal Senate...")
        decision = await self.council.convene(context)
        if decision["status"] in ["failed", "deadlock", "ROGUE_VETO"]:
            logger.warning("Council halted: %s. No actions taken.", decision["status"])
            return {"status": "halted", "reason": decision.get("reasoning", "No consensus")}

        winning_action = {
            "type": "modify",
            "file": decision["target_file"],
            "content": decision["decision"],
        }

        if not self.dry_run:
            checkpoint = self.git.save_state()
            if not checkpoint.get("success"):
                logger.error("Constitution blocked execution: %s", checkpoint.get("message"))
                return {
                    "status": "blocked",
                    "reason": checkpoint.get("message", "repository baseline could not be verified"),
                    "execution": {"status": "blocked", "executed": [], "errors": []},
                }

        exec_result = self.runner.run(
            [winning_action],
            dry_run=self.dry_run,
            approved_paths=approved_paths,
            allow_delete=allow_delete,
        )

        if not self.dry_run and exec_result.get("status") != "completed":
            logger.error("Constitution blocked or failed the proposed mutation.")
            return {
                "status": "blocked",
                "reason": "action policy or execution validation failed; inspect the policy audit",
                "decision": decision,
                "execution": exec_result,
            }

        if not self.dry_run:
            logger.info("Validating changes...")
            val_result = await self.validator.validate(target_files=[winning_action["file"]])
            if not val_result["passed"]:
                logger.error("Validation failed; preserving the diff for human review.")
                return {
                    "status": "validation_failed",
                    "reason": val_result.get("reason"),
                    "decision": decision,
                    "execution": exec_result,
                    "validation": val_result,
                    "recovery_note": "No automatic hard reset was performed; inspect and revert only the reviewed action paths.",
                }

        logger.info("RepoForge pipeline completed.")
        return {
            "status": "success",
            "decision": decision,
            "execution": exec_result,
        }
