"""
Agent Coordinator – runs all agents asynchronously.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from .base import BaseAgent

logger = logging.getLogger(__name__)

class AgentCoordinator:
    def __init__(self, agents: Optional[List[BaseAgent]] = None):
        self.agents = agents or []

    def register(self, agent: BaseAgent) -> None:
        self.agents.append(agent)
        logger.info(f"Registered agent: {agent.name}")

    def register_all(self, agent_list: List[BaseAgent]) -> None:
        self.agents.extend(agent_list)
        logger.info(f"Registered {len(agent_list)} agents.")

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.agents:
            logger.warning("No agents registered.")
            return {"agents_run": [], "findings": [], "confidence": 0.0}

        findings = []
        total_conf = 0.0
        count = 0

        # Execute all agents concurrently
        tasks = [agent.analyze(context) for agent in self.agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for agent, result in zip(self.agents, results):
            if isinstance(result, Exception):
                logger.error(f"Agent {agent.name} failed: {result}")
                continue
                
            if result: # Assuming result is a Proposal object
                findings.append(result)
                total_conf += result.confidence_score
                count += 1

        avg_conf = total_conf / count if count > 0 else 0.0

        return {
            "agents_run": [a.name for a in self.agents],
            "findings": findings,
            "confidence": round(avg_conf, 4),
        }
