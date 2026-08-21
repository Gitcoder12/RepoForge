"""
Consensus Engine – upgraded with memory and refined scoring.
"""

from typing import List, Dict, Any
import difflib
import logging
from collections import defaultdict
from ..memory.agent_memory import AgentMemory

logger = logging.getLogger(__name__)

# Agent expertise weights
AGENT_WEIGHTS = {
    "SecurityAgent": 1.0,
    "TestingAgent": 0.9,
    "ArchitectAgent": 0.9,
    "PerformanceAgent": 0.8,
    "CodeReviewAgent": 0.7,
    "DependencyAgent": 0.7,
    "DocumentationAgent": 0.5,
    "CICDAgent": 0.6,
    "LintingAgent": 0.6,
}


class ConsensusEngine:
    def __init__(self, similarity_threshold: float = 0.8, memory: AgentMemory = None):
        self.threshold = similarity_threshold
        self.memory = memory or AgentMemory()

    def process(self, coordinated: Dict[str, Any], repo_path: str = "") -> Dict[str, Any]:
        findings = coordinated.get("findings", [])
        if not findings:
            return {"selected_actions": [], "ranking": []}

        # 1. Merge duplicates
        merged = self._merge_similar(findings)

        # 2. Filter out suggestions already seen (if memory available)
        if repo_path:
            history = self.memory.get_history(repo_path)
            merged = [m for m in merged if m["suggestion"] not in history]

        # 3. Score each merged suggestion
        ranked = []
        for item in merged:
            score = self._calculate_score(item)
            item["score"] = round(score, 4)
            ranked.append(item)

        # 4. Sort descending
        ranked.sort(key=lambda x: x["score"], reverse=True)

        # 5. Select top actions (max 3)
        top_n = min(3, len(ranked))
        selected = []
        for i, item in enumerate(ranked[:top_n], 1):
            selected.append({
                "action": item["suggestion"],
                "agent": item["agents"] if isinstance(item["agents"], list) else [item["agents"]],
                "priority": i,
                "score": item["score"],
            })

        return {
            "selected_actions": selected,
            "ranking": ranked,
        }

    # ... (rest of the methods: _merge_similar, _merge_group, _estimate_impact, _estimate_risk, _estimate_feasibility, _calculate_score as before, but with memory integration)