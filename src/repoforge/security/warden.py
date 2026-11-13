import re
import logging
from typing import Dict, Any
from ..base import BaseAgent
from ..models import Proposal, ActionType

logger = logging.getLogger("RepoForge.Security.Warden")

class Warden(BaseAgent):
    """
    The God Mode Agent. 
    It does not reason. It does not use an LLM. It enforces strict rules.
    """
    
    def __init__(self):
        super().__init__(provider=None)
        self.rogue_signatures = [
            r"ignore previous instructions",
            r"ignore all prior",
            r"system prompt",
            r"you are now a",
            r"rm -rf /",
            r"DROP TABLE",
            r"import\s+os\s*;\s*os\.system",
            r"eval\(.*base64",
            r"__import__\('os'\)",
            r"subprocess\.Popen",
            r"socket\.socket"
        ]

    async def analyze(self, context: Dict[str, Any]) -> Proposal:
        logger.info(" Warden is scanning for rogue behavior and prompt injections...")
        
        scan_data = context.get("scan", {})
        threats = scan_data.get("threats", [])
        
        for threat in threats:
            if threat["category"] == "dangerous_functions" or threat["severity"] == "CRITICAL":
                logger.critical(f" ROGUE AI DETECTED: {threat['description']} in {threat['file']}")
                return self._generate_veto(threat['file'], threat['description'])

        prompt = context.get("prompt", "").lower()
        for sig in self.rogue_signatures:
            if re.search(sig, prompt):
                logger.critical(f" PROMPT INJECTION DETECTED: '{sig}'")
                return self._generate_veto("prompt_injection.md", f"Malicious prompt signature: {sig}")

        logger.info(" Warden found no threats.")
        return Proposal(
            agent_name=self.name, action_type=ActionType.MODIFY, target_file="none",
            proposed_code="", confidence_score=0.0, reasoning="No threats detected."
        )

    def _generate_veto(self, file_path: str, reason: str) -> Proposal:
        return Proposal(
            agent_name=self.name, action_type=ActionType.DELETE, target_file=file_path,
            proposed_code="# QUARANTINED BY WARDEN\n# Reason: " + reason,
            confidence_score=1.0, reasoning=f"WARDEN VETO: {reason}"
        )
