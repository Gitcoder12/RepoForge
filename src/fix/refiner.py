from pathlib import Path
from typing import Dict, Any, List
from .scanner import scan_repository
from .agents.coordinator import AgentCoordinator
from .agents.architect_agent import ArchitectAgent
from .agents.security_agent import SecurityAgent
from .agents.testing_agent import TestingAgent
from .agents.documentation_agent import DocumentationAgent
from .agents.dependency_agent import DependencyAgent
from .agents.performance_agent import PerformanceAgent
from .agents.linting_agent import LintingAgent
from .agents.ci_cd_agent import CICDAgent
from .agents.review_agent import ReviewAgent
from .execution.action_runner import ActionRunner

class Refiner:
    def __init__(self, repo_path: str, provider: str = "openai"):
        self.repo_path = Path(repo_path)
        self.provider = provider

    def refine(self, initial_actions: List[str]) -> Dict[str, Any]:
        print("🔧 Running refinement pass...")
        scan_data = scan_repository(str(self.repo_path))
        coordinator = AgentCoordinator()
        for agent_cls in [ArchitectAgent, SecurityAgent, TestingAgent, DocumentationAgent,
                          DependencyAgent, PerformanceAgent, LintingAgent, CICDAgent, ReviewAgent]:
            try:
                agent = agent_cls(provider=self.provider)
                coordinator.register(agent)
            except:
                pass
        context = {"scan": scan_data, "health": {}, "risk": {}}
        agent_output = coordinator.run(context)
        new_suggestions = agent_output.get("suggestions", [])
        remaining = [s for s in new_suggestions if s not in initial_actions]
        if not remaining:
            return {"status": "no_more_improvements", "executed": []}
        print(f"  🔄 Found {len(remaining)} additional improvements")
        runner = ActionRunner(str(self.repo_path))
        result = runner.run(remaining, dry_run=False)
        return {"status": "refined", "executed": result.get("executed", []), "errors": result.get("errors", [])}