"""Role-aware entry point for RepoForge super agents."""

from __future__ import annotations

from typing import Any

from repoforge.agents.coding import CodingSuperAgent
from repoforge.agents.research import ResearchSuperAgent
from repoforge.base import BaseProvider


class SuperAgentOrchestrator:
    def __init__(
        self,
        default_provider: BaseProvider,
        role_providers: dict[str, BaseProvider] | None = None,
    ) -> None:
        self.default_provider = default_provider
        self.role_providers = role_providers or {}

    def _provider(self, role: str) -> BaseProvider:
        return self.role_providers.get(role, self.default_provider)

    def coding_agent(self) -> CodingSuperAgent:
        return CodingSuperAgent(
            architect_provider=self._provider("architect"),
            coder_provider=self._provider("coder"),
            reviewer_provider=self._provider("reviewer"),
        )

    def research_agent(self) -> ResearchSuperAgent:
        return ResearchSuperAgent(
            extractor_provider=self._provider("extractor"),
            synthesizer_provider=self._provider("synthesizer"),
            auditor_provider=self._provider("auditor"),
            formatter_provider=self._provider("formatter"),
        )

    def run(self, task_type: str, **kwargs: Any) -> dict[str, Any]:
        if task_type == "coding":
            return self.coding_agent().build_feature(**kwargs)
        if task_type == "research":
            return self.research_agent().generate_paper(**kwargs)
        raise ValueError("task_type must be 'coding' or 'research'")
