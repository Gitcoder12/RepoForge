"""Typed data models shared by RepoForge agents and safety components."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


class AgentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class Finding:
    agent_name: str
    issue_type: str
    description: str
    file_path: str
    line_number: int | None = None
    confidence: float = 0.0


@dataclass
class Action:
    action_type: ActionType
    file_path: str
    content: str
    reasoning: str = ""


@dataclass
class Proposal:
    agent_name: str
    action_type: ActionType
    target_file: str
    proposed_code: str
    confidence_score: float
    reasoning: str
    impact: float = 0.5
    risk: float = 0.5
    feasibility: float = 0.5
    rebuttal: str = ""


@dataclass
class RepoState:
    repo_path: str
    languages: dict[str, int] = field(default_factory=dict)
    total_files: int = 0
    total_lines: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    profile: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusResult:
    winning_proposal: Proposal | None = None
    top_actions: list[dict[str, Any]] = field(default_factory=list)
    consensus_reached: bool = False
    requires_governor: bool = False
    tied_proposals: list[Proposal] = field(default_factory=list)
    dissenters: list[str] = field(default_factory=list)


MODELS = {
    "fast": "groq/llama3-70b-8192",
    "coder": "deepseek/deepseek-coder",
    "architect": "anthropic/claude-3.5-sonnet",
    "security": "openai/gpt-4o",
    "default": "openrouter/auto",
}
