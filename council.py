"""
Agent Council – runs all agents, collects opinions, and selects the best action.
"""

from typing import List, Dict, Any
from .coordinator import AgentCoordinator
from .consensus import ConsensusEngine
from . import (
    ArchitectAgent,
    SecurityAgent,
    TestingAgent,
    PerformanceAgent,
    ReviewAgent,
    DocumentationAgent,
    DependencyAgent,
    CICDAgent,
    LintingAgent,
)


class AgentCouncil:
    """
    The council runs all agents, uses consensus to rank, and returns a decision.
    """

    def __init__(self):
        self.coordinator = AgentCoordinator()
        self.consensus = ConsensusEngine()
        self._register_all_agents()

    def _register_all_agents(self):
        self.coordinator.register_all([
            ArchitectAgent(),
            SecurityAgent(),
            TestingAgent(),
            PerformanceAgent(),
            ReviewAgent(),
            DocumentationAgent(),
            DependencyAgent(),
            CICDAgent(),
            LintingAgent(),
        ])

    def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the full council process.
        Returns:
        {
            "decision": str,
            "agents": list,
            "confidence": float,
            "priority": int,
            "all_suggestions": list,
            "ranking": list
        }
        """
        # Run all agents
        coordinated = self.coordinator.run(context)

        # Consensus ranking
        consensus_result = self.consensus.process(coordinated)

        # Extract top action
        selected_actions = consensus_result.get("selected_actions", [])
        if selected_actions:
            top = selected_actions[0]
            decision = top["action"]
            agents = top["agent"]
            confidence = top["score"]
            priority = top["priority"]
        else:
            decision = None
            agents = []
            confidence = 0.0
            priority = 0

        return {
            "decision": decision,
            "agents": agents,
            "confidence": confidence,
            "priority": priority,
            "all_suggestions": coordinated.get("findings", []),
            "ranking": consensus_result.get("ranking", []),
        }