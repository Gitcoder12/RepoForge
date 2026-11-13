"""
RepoForge Data Models
Defines the strict data structures used across the entire pipeline.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

# --- Enums ---

class ActionType(str, Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"

class AgentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

# --- Core Models ---

@dataclass
class Finding:
    """A specific issue found by an agent (e.g., a security flaw, missing doc)."""
    agent_name: str
    issue_type: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    confidence: float = 0.0

@dataclass
class Action:
    """A concrete change to be applied to the repository."""
    action_type: ActionType
    file_path: str
    content: str
    reasoning: str = ""

@dataclass
class Proposal:
    """A proposed solution (code change) submitted by an agent to the Council."""
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
    """The current state of the repository being scanned."""
    repo_path: str
    languages: Dict[str, int] = field(default_factory=dict)
    total_files: int = 0
    total_lines: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    profile: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConsensusResult:
    """The output of the Consensus Engine."""
    winning_proposal: Optional[Proposal] = None
    top_actions: List[Dict[str, Any]] = field(default_factory=list)
    consensus_reached: bool = False
    requires_governor: bool = False
    tied_proposals: List[Proposal] = field(default_factory=list)
    dissenters: List[str] = field(default_factory=list)

# --- AI Models Map ---

MODELS = {
    "fast": "groq/llama3-70b-8192",
    "coder": "deepseek/deepseek-coder",
    "architect": "anthropic/claude-3.5-sonnet",
    "security": "openai/gpt-4o",
    "default": "openrouter/auto"
}
