"""
Agent Coordinator – runs all agents, normalizes outputs, returns combined analysis.
"""

from typing import Dict, Any, List, Optional
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """
    Executes all registered agents on the same context and aggregates their results.
    """

    def __init__(self, agents: Optional[List[BaseAgent]] = None):
        self.agents = agents or []

    def register(self, agent: BaseAgent) -> None:
        self.agents.append(agent)

    def register_all(self, agent_list: List[BaseAgent]) -> None:
        self.agents.extend(agent_list)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns:
        {
            "agents_run": list of agent names,
            "findings": list of dicts with agent, suggestion, confidence,
            "suggestions": list of strings (for backward compatibility),
            "confidence": average confidence across all suggestions
        }
        """
        if not self.agents:
            logger.warning("No agents registered.")
            return {"agents_run": [], "findings": [], "suggestions": [], "confidence": 0.0}

        findings = []
        total_conf = 0.0
        count = 0

        for agent in self.agents:
            try:
                result = agent.run(context)
                suggestions = result.get("suggestions", [])
                confidence = result.get("confidence", 0.5)
                for suggestion in suggestions:
                    findings.append({
                        "agent": agent.name,
                        "suggestion": suggestion,
                        "confidence": confidence,
                        "summary": result.get("summary", "")
                    })
                    total_conf += confidence
                    count += 1
            except Exception as e:
                logger.error(f"Agent {agent.name} failed: {e}")

        avg_conf = total_conf / count if count > 0 else 0.0
        suggestions_list = [f["suggestion"] for f in findings]

        return {
            "agents_run": [a.name for a in self.agents],
            "findings": findings,
            "suggestions": suggestions_list,
            "confidence": round(avg_conf, 4),
        }