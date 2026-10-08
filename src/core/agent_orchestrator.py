"""
Agent Orchestrator – runs agents and collects results.
"""

from typing import List, Dict, Any, Optional
import logging
from .blackboard import Blackboard
from .agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Runs a set of agents and aggregates their outputs."""

    def __init__(self, agents: Optional[List[BaseAgent]] = None):
        self.agents = agents or []
        self.blackboard = Blackboard()

    def register(self, agent: BaseAgent):
        """Add an agent to the orchestrator."""
        self.agents.append(agent)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all registered agents with the given context.
        Returns:
            - agent_results: list of agent outputs
            - combined_suggestions: list of all suggestions
            - average_confidence: float
        """
        if not self.agents:
            logger.info("No agents registered. Skipping orchestration.")
            return {"agent_results": [], "combined_suggestions": [], "average_confidence": 0.0}

        # Initialize blackboard with context
        self.blackboard.update(context)

        agent_results = []
        combined_suggestions = []
        total_confidence = 0.0

        for agent in self.agents:
            logger.info(f"Running agent: {agent.name}")
            try:
                result = agent.run(context)
                agent_results.append(result)
                suggestions = result.get("suggestions", [])
                combined_suggestions.extend(suggestions)
                total_confidence += result.get("confidence", 0.0)

                # Write back to blackboard
                self.blackboard.set(f"agent_{agent.name}", result)

            except Exception as e:
                logger.error(f"Agent {agent.name} failed: {e}")
                agent_results.append({"agent": agent.name, "error": str(e), "suggestions": []})

        avg_conf = total_confidence / len(self.agents) if self.agents else 0.0

        return {
            "agent_results": agent_results,
            "combined_suggestions": combined_suggestions,
            "average_confidence": avg_conf,
            "blackboard": self.blackboard.all()
        }