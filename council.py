import asyncio
import logging
import random
from typing import List, Dict, Any

from .coordinator import AgentCoordinator
from .consensus import ConsensusEngine, Proposal, ConsensusResult
from .router import AIRouter
from . import (
    ArchitectAgent, SecurityAgent, TestingAgent,
    PerformanceAgent, ReviewAgent, DocumentationAgent,
    DependencyAgent, CICDAgent, LintingAgent,
)

logger = logging.getLogger("RepoForge.Council")

class AgentCouncil:
    def __init__(self, max_concurrent_agents: int = 5):
        self.coordinator = AgentCoordinator()
        self.consensus = ConsensusEngine()
        self.router = AIRouter()
        self.agents: List[Any] = []
        self.semaphore = asyncio.Semaphore(max_concurrent_agents)
        self._initialize_council()

    def _initialize_council(self):
        agent_classes = [
            ArchitectAgent, SecurityAgent, TestingAgent, PerformanceAgent,
            ReviewAgent, DocumentationAgent, DependencyAgent, CICDAgent, LintingAgent
        ]
        for agent_cls in agent_classes:
            agent_name = agent_cls.__name__
            task_category = self._map_agent_to_task(agent_name)
            provider_name, _ = self.router.select(prompt=task_category)
            llm = self.router.instantiate(provider_name)
            
            logger.info(f" {agent_name} armed with {provider_name.upper()}")
            self.agents.append(agent_cls(provider=llm))

    def _map_agent_to_task(self, agent_name: str) -> str:
        mapping = {
            "ArchitectAgent": "architecture", "SecurityAgent": "security",
            "TestingAgent": "coding", "PerformanceAgent": "coding",
            "ReviewAgent": "analysis", "DocumentationAgent": "docs",
            "DependencyAgent": "analysis", "CICDAgent": "coding",
            "LintingAgent": "fast",
        }
        return mapping.get(agent_name, "default")

    async def _consult_agent_with_retry(self, agent: Any, context: Dict[str, Any], max_retries: int = 3) -> None:
        agent_name = agent.__class__.__name__
        async with self.semaphore:
            for attempt in range(max_retries):
                try:
                    proposal = await agent.analyze(context)
                    if proposal:
                        self.consensus.submit_proposal(proposal)
                    return 
                except Exception as e:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f" {agent_name} failed: {e}. Retrying in {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
            logger.error(f" {agent_name} failed after {max_retries} attempts.")

    async def _summon_governor(self, tied_proposals: List[Proposal]) -> Proposal:
        """The Governor (Super-Model) breaks the deadlock."""
        logger.critical(" DEADLOCK. Summoning the Governor.")
        governor_llm = self.router.instantiate("anthropic") # Or OpenAI GPT-4o
        
        # In a real implementation, you'd prompt the LLM here:
        # prompt = f"Review these tied proposals and pick the best:\n{...}"
        
        await asyncio.sleep(1) # Simulating heavy reasoning
        
        # Ruthless logic: Governor sides with Security, then Architecture
        winner = next((p for p in tied_proposals if "Security" in p.agent_name), tied_proposals[0])
        winner.reasoning += " [GOVERNOR OVERRIDE]"
        return winner

    async def convene(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f" CONVENING SENATE ({len(self.agents)} agents)...")
        
        # 1. Deploy agents
        tasks = [self._consult_agent_with_retry(agent, context) for agent in self.agents]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 2. Calculate Consensus (using the separated engine)
        result: ConsensusResult = self.consensus.resolve()

        if not result.total_votes:
            return {"status": "failed", "decision": None}

        # 3. Handle Security Veto (Tribunal check)
        veto = next((p for p in self.consensus.proposals if "SecurityAgent" in p.agent_name and p.confidence_score > 0.90), None)
        if veto:
            has_second = any(p.agent_name in ["ArchitectAgent", "TestingAgent", "ReviewAgent"] for p in self.consensus.proposals if p.target_file == veto.target_file)
            if has_second:
                logger.critical(" SECURITY VETO SECONDED! Code blocked.")
                return self._format_winner(veto, status="SECURITY_VETO")

        # 4. Governor Intervention
        if result.requires_governor and result.tied_proposals:
            winning_proposal = await self._summon_governor(result.tied_proposals)
            return self._format_winner(winning_proposal, status="GOVERNOR_OVERRIDE")

        # 5. Standard Consensus
        if result.winning_proposal:
            return self._format_winner(result.winning_proposal, status="CONSENSUS", dissenters=result.dissenters)
        
        return {"status": "deadlock", "decision": None}

    def _format_winner(self, proposal: Proposal, status: str, dissenters: List[str] = None) -> Dict[str, Any]:
        return {
            "status": status,
            "decision": proposal.proposed_code,
            "target_file": proposal.target_file,
            "winning_agent": proposal.agent_name,
            "confidence": proposal.confidence_score,
            "reasoning": proposal.reasoning,
            "dissenters": dissenters or []
        }
