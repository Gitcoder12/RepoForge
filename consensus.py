"""
Consensus Engine – Lethal Hybrid Edition.
Combines memory, multi-factor scoring, AST deduplication, and Governor tie-detection.
"""

from typing import List, Dict, Any, Optional
import difflib
import ast
import logging
from dataclasses import dataclass, field
from ..memory.agent_memory import AgentMemory

logger = logging.getLogger(__name__)

AGENT_WEIGHTS = {
    "SecurityAgent": 1.5, "TestingAgent": 1.2, "ArchitectAgent": 1.3,
    "PerformanceAgent": 1.0, "CodeReviewAgent": 0.8, "ReviewAgent": 0.8,
    "DependencyAgent": 0.7, "DocumentationAgent": 0.5, "CICDAgent": 0.6, "LintingAgent": 0.6,
}

@dataclass
class Proposal:
    agent_name: str
    action_type: str
    target_file: str
    proposed_code: str
    confidence_score: float
    reasoning: str
    impact: float = 0.5
    risk: float = 0.5
    feasibility: float = 0.5

@dataclass
class ConsensusResult:
    winning_proposal: Optional[Proposal] = None
    top_actions: List[Dict[str, Any]] = field(default_factory=list)
    consensus_reached: bool = False
    requires_governor: bool = False
    tied_proposals: List[Proposal] = field(default_factory=list)
    dissenters: List[str] = field(default_factory=list)


class ConsensusEngine:
    def __init__(self, similarity_threshold: float = 0.8, memory: AgentMemory = None):
        self.threshold = similarity_threshold
        self.memory = memory or AgentMemory()
        self.proposals: List[Proposal] = []

    def submit_proposal(self, proposal: Proposal) -> None:
        self.proposals.append(proposal)
        logger.info(f"📥 {proposal.agent_name} submitted a proposal for {proposal.target_file}")

    def _is_logically_identical(self, code1: str, code2: str) -> bool:
        """AST-based deduplication fallback to string similarity."""
        try:
            tree1 = ast.dump(ast.parse(code1))
            tree2 = ast.dump(ast.parse(code2))
            return tree1 == tree2
        except SyntaxError:
            matcher = difflib.SequenceMatcher(None, code1, code2)
            return matcher.ratio() > self.threshold

    def _merge_similar(self) -> List[Proposal]:
        """Forms Coalitions if agents submit identical code logic."""
        if not self.proposals: return []

        merged = []
        for prop in self.proposals:
            found_match = False
            for existing in merged:
                if prop.target_file == existing.target_file and self._is_logically_identical(prop.proposed_code, existing.proposed_code):
                    new_name = f"Coalition({existing.agent_name} + {prop.agent_name})"
                    new_confidence = min(1.0, existing.confidence_score + (prop.confidence_score * 0.5))
                    
                    logger.info(f"🤝 COALITION: {existing.agent_name} & {prop.agent_name} agreed. Score: {new_confidence:.2f}")
                    
                    existing.agent_name = new_name
                    existing.confidence_score = new_confidence
                    existing.reasoning += f" | Allied with {prop.agent_name}"
                    found_match = True
                    break
            if not found_match:
                merged.append(prop)
        return merged

    def _calculate_score(self, prop: Proposal) -> float:
        """
        Uses your original multi-factor logic.
        Score = (Base Confidence * Agent Weight) + Impact - Risk + Feasibility
        """
        weight = AGENT_WEIGHTS.get(prop.agent_name, 1.0)
        # If it's a coalition, the weight is the max weight of the components
        if "Coalition" in prop.agent_name:
            weight = 1.4 # Coalitions get a flat high weight

        base_score = weight * prop.confidence_score
        final_score = base_score + (prop.impact * 0.2) - (prop.risk * 0.3) + (prop.feasibility * 0.2)
        return round(final_score, 4)

    def resolve(self, repo_path: str = "") -> ConsensusResult:
        """
        The main execution loop. 
        Integrates memory filtering, coalition merging, and tie detection.
        """
        if not self.proposals:
            return ConsensusResult()

        # 1. Filter out things already tried (Memory)
        if repo_path:
            history = self.memory.get_history(repo_path)
            # Filter out if the exact code or reasoning was already attempted
            self.proposals = [p for p in self.proposals if p.proposed_code not in history and p.reasoning not in history]

        # 2. Deduplicate (Form Coalitions)
        self.proposals = self._merge_similar()

        # 3. Group by file
        file_groups: Dict[str, List[Proposal]] = {}
        for p in self.proposals:
            file_groups.setdefault(p.target_file, []).append(p)

        final_winners = []
        dissenters = []
        requires_governor = False
        tied_proposals = []
        top_actions = []

        # 4. Score and Resolve per file
        for target_file, props in file_groups.items():
            scored_props = []
            for p in props:
                p.confidence_score = self._calculate_score(p) # Overwrite confidence with total score
                scored_props.append(p)
            
            scored_props.sort(key=lambda x: x.confidence_score, reverse=True)
            top = scored_props[0]

            # Deadlock Detection (Scores within 0.05)
            if len(scored_props) > 1:
                if abs(top.confidence_score - scored_props[1].confidence_score) < 0.05:
                    requires_governor = True
                    tied_proposals.extend([top, scored_props[1]])
                    logger.warning(f"⚠️ Deadlock on {target_file}: {top.agent_name} vs {scored_props[1].agent_name}")
                    continue

            final_winners.append(top)
            dissenters.extend([p.agent_name for p in scored_props[1:]])
            
            # Format for your original 'selected_actions' output
            top_actions.append({
                "action": top.proposed_code,
                "agent": top.agent_name,
                "priority": len(top_actions) + 1,
                "score": top.confidence_score,
            })

        return ConsensusResult(
            winning_proposal=final_winners[0] if final_winners else None,
            top_actions=top_actions,
            consensus_reached=not requires_governor,
            requires_governor=requires_governor,
            tied_proposals=tied_proposals,
            dissenters=list(set(dissenters))
        )

    # --- Backwards Compatibility Wrapper ---
    def process(self, coordinated: Dict[str, Any], repo_path: str = "") -> Dict[str, Any]:
        """
        Wraps your original interface so older code doesn't break.
        """
        findings = coordinated.get("findings", [])
        for f in findings:
            self.submit_proposal(Proposal(
                agent_name=f.get("agent", "UnknownAgent"),
                action_type="apply",
                target_file=f.get("file", "unknown.py"),
                proposed_code=f.get("suggestion", ""),
                confidence_score=f.get("confidence", 0.8),
                reasoning=f.get("reasoning", ""),
            ))
        
        result = self.resolve(repo_path)
        return {
            "selected_actions": result.top_actions,
            "ranking": [{"suggestion": a["action"], "score": a["score"]} for a in result.top_actions]
        }
