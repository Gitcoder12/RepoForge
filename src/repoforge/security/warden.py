"""Rule-based safety checks for agent proposals and prompts."""

import logging
import re
from typing import Any

from repoforge.base import BaseAgent
from repoforge.models import ActionType, Proposal

logger = logging.getLogger("RepoForge.Security.Warden")


class Warden(BaseAgent):
    """Deterministic veto layer for known dangerous patterns."""

    def __init__(self) -> None:
        super().__init__(provider=None)
        self.rogue_signatures = (
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
            r"socket\.socket",
        )

    async def analyze(self, context: dict[str, Any]) -> Proposal:
        scan_data = context.get("scan", {})
        for threat in scan_data.get("threats", []):
            if (
                threat.get("category") == "dangerous_functions"
                or threat.get("severity") == "CRITICAL"
            ):
                return self._generate_veto(
                    str(threat.get("file", "unknown")),
                    str(threat.get("description", "Critical threat")),
                )

        prompt = str(context.get("prompt", "")).lower()
        for signature in self.rogue_signatures:
            if re.search(signature, prompt):
                return self._generate_veto(
                    "prompt_injection.md", f"Malicious prompt signature: {signature}"
                )

        return Proposal(
            agent_name=self.name,
            action_type=ActionType.MODIFY,
            target_file="none",
            proposed_code="",
            confidence_score=0.0,
            reasoning="No known threat signature detected.",
        )

    def _generate_veto(self, file_path: str, reason: str) -> Proposal:
        logger.warning("Warden veto: %s", reason)
        return Proposal(
            agent_name=self.name,
            action_type=ActionType.DELETE,
            target_file=file_path,
            proposed_code=f"# QUARANTINED BY WARDEN\n# Reason: {reason}",
            confidence_score=1.0,
            reasoning=f"WARDEN VETO: {reason}",
        )
