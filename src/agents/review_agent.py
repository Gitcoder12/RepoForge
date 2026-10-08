from typing import Dict, Any
from .base_agent import BaseAgent

class ReviewAgent(BaseAgent):
    def __init__(self, provider: str = "openai", **kwargs):
        super().__init__(provider=provider, **kwargs)
        self.name = "ReviewAgent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        suggestions = [
            "Add a CONTRIBUTING.md",
            "Create a PULL_REQUEST_TEMPLATE.md",
            "Add issue templates (bug report, feature request)",
            "Add CODE_OF_CONDUCT.md",
            "Add a CHANGELOG.md"
        ]
        return {"suggestions": suggestions, "confidence": 0.7, "summary": "Community and review improvements"}