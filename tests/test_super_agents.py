import pytest

from repoforge.agents import CodingSuperAgent, ResearchSuperAgent, SuperAgentOrchestrator
from repoforge.base import BaseProvider
from repoforge.providers.mock import MockProvider


class SequenceProvider(BaseProvider):
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, str]] = []
        super().__init__()

    def _initialize(self) -> None:
        self.client = self

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
        if not self.responses:
            raise AssertionError("Unexpected provider call")
        return self.responses.pop(0)

    async def stream(self, prompt: str, system_prompt: str = "", **kwargs):
        yield self.generate(prompt, system_prompt, **kwargs)

    def get_capabilities(self):
        return {"name": self.name, "offline": True}

    @property
    def name(self) -> str:
        return "sequence"

    @property
    def models(self) -> list[str]:
        return ["sequence"]


def test_coding_agent_runs_architect_coder_and_reviewer() -> None:
    provider = SequenceProvider(
        [
            "Plan: add input validation.",
            "def validate(value):\n    if not value:\n        raise ValueError()",
            '{"status":"PASS","findings":[],"required_tests":["empty input"]}',
        ]
    )
    result = CodingSuperAgent(provider).build_feature("Add validation")

    assert result["review_passed"] is True
    assert result["execution_verified"] is False
    assert result["review_attempts"] == 1
    assert len(provider.calls) == 3


def test_coding_agent_revises_after_failed_review() -> None:
    provider = SequenceProvider(
        [
            "Plan",
            "unsafe implementation",
            '{"status":"FAIL","findings":["Missing validation"],"required_tests":[]}',
            "revised implementation",
            '{"status":"PASS","findings":[],"required_tests":[]}',
        ]
    )
    result = CodingSuperAgent(provider).build_feature("Implement safe parsing", max_revisions=1)

    assert result["code"] == "revised implementation"
    assert result["review_passed"] is True
    assert result["review_attempts"] == 2


def test_coding_agent_fails_closed_on_invalid_review_json() -> None:
    provider = SequenceProvider(["Plan", "Code", "not json"])
    result = CodingSuperAgent(provider).build_feature("Implement feature", max_revisions=0)

    assert result["review_passed"] is False
    assert result["review"]["status"] == "FAIL"


def test_coding_agent_rejects_excessive_revisions() -> None:
    provider = MockProvider()
    with pytest.raises(ValueError, match="max_revisions"):
        CodingSuperAgent(provider).build_feature("Task", max_revisions=6)


def test_research_agent_requires_cited_source_records() -> None:
    provider = MockProvider()
    agent = ResearchSuperAgent(provider)
    with pytest.raises(ValueError, match="source_id, text, and citation"):
        agent.generate_paper([{"source_id": "S1", "text": "Evidence"}], "Topic")


def test_research_agent_withholds_latex_when_audit_fails() -> None:
    provider = SequenceProvider(
        [
            "Extracted evidence",
            "Draft with an unsupported claim",
            '{"status":"FAIL","unsupported_claims":["Claim X"],"invalid_citations":[]}',
        ]
    )
    result = ResearchSuperAgent(provider).generate_paper(
        [{"source_id": "S1", "text": "Observed result", "citation": "Author (2025)"}],
        "A research topic",
    )

    assert result["citation_audit_passed"] is False
    assert result["latex"] is None
    assert len(provider.calls) == 3


def test_research_agent_formats_only_after_audit_passes() -> None:
    provider = SequenceProvider(
        [
            "Extracted evidence",
            "Evidence-grounded draft",
            '{"status":"PASS","unsupported_claims":[],"invalid_citations":[]}',
            "\\documentclass{article}\\begin{document}Draft\\end{document}",
        ]
    )
    result = ResearchSuperAgent(provider).generate_paper(
        [{"source_id": "S1", "text": "Observed result", "citation": "Author (2025)"}],
        "A research topic",
    )

    assert result["citation_audit_passed"] is True
    assert result["latex"].startswith("\\documentclass")
    assert result["publication_verified"] is False


def test_super_agent_orchestrator_routes_by_task_type() -> None:
    provider = MockProvider('{"status":"PASS","findings":[],"required_tests":[]}')
    orchestrator = SuperAgentOrchestrator(provider)

    result = orchestrator.run("coding", task_description="Add a feature")

    assert result["review_passed"] is True
    with pytest.raises(ValueError, match="task_type"):
        orchestrator.run("unknown")



def test_coding_agent_rejects_pass_with_blocking_findings() -> None:
    provider = SequenceProvider(
        [
            "Plan",
            "Code",
            '{"status":"PASS","findings":["Critical security issue"],"required_tests":[]}',
        ]
    )
    result = CodingSuperAgent(provider).build_feature("Implement feature", max_revisions=0)

    assert result["review_passed"] is False
    assert result["review"]["status"] == "FAIL"


def test_research_agent_rejects_pass_with_invalid_citations() -> None:
    provider = SequenceProvider(
        [
            "Extracted evidence",
            "Draft",
            '{"status":"PASS","unsupported_claims":[],"invalid_citations":["UNKNOWN"]}',
        ]
    )
    result = ResearchSuperAgent(provider).generate_paper(
        [{"source_id": "S1", "text": "Observed result", "citation": "Author (2025)"}],
        "A research topic",
    )

    assert result["citation_audit_passed"] is False
    assert result["latex"] is None
