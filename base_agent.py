"""Base agent with provider support."""
from typing import Dict, Any, Optional
from ..providers import get_provider

class BaseAgent:
    """All agents inherit from this."""

    def __init__(self, provider: str = "openai", **kwargs):
        self.provider = get_provider(provider, **kwargs)
        self.name = self.__class__.__name__

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement run()")

    def _call_llm(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        return self.provider.generate(prompt, system_prompt, **kwargs)