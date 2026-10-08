from typing import Dict, Any
from .base_agent import BaseAgent

class DocumentationAgent(BaseAgent):
    def __init__(self, provider: str = "openai", **kwargs):
        super().__init__(provider=provider, **kwargs)
        self.name = "DocumentationAgent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        metadata = context.get("scan", {}).get("metadata", {})
        suggestions = []
        if not metadata.get("has_readme"):
            suggestions.append("Create a README.md with project overview, setup, and usage")
        if not metadata.get("has_license"):
            suggestions.append("Add a LICENSE file (MIT recommended)")
        if not metadata.get("has_docs_dir"):
            suggestions.append("Create a docs/ folder for detailed documentation")
        if not metadata.get("has_ci_config"):
            suggestions.append("Add CI badge and documentation workflow")
        if not suggestions:
            suggestions = ["Add API documentation", "Include code examples", "Add contribution guidelines"]
        return {"suggestions": suggestions, "confidence": 0.9, "summary": "Documentation gaps identified"}