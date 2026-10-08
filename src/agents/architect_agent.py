from typing import Dict, Any
from .base_agent import BaseAgent

class ArchitectAgent(BaseAgent):
    def __init__(self, provider: str = "openai", **kwargs):
        super().__init__(provider=provider, **kwargs)
        self.name = "ArchitectAgent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        scan = context.get("scan", {})
        health = context.get("health", {})
        prompt = f"Analyze the repository structure and suggest architectural improvements.\nFiles: {scan.get('statistics', {}).get('total_files', 0)}\nLanguages: {list(scan.get('languages', {}).keys())}\nHealth score: {health.get('health_score', 0)}\nSuggest 3-5 concrete architectural improvements."
        system = "You are a software architect. Provide specific, actionable suggestions."
        try:
            response = self._call_llm(prompt, system)
            suggestions = [s.strip() for s in response.split('\n') if s.strip()]
        except:
            suggestions = ["Consider modularizing the codebase", "Add interface abstractions", "Separate business logic from I/O"]
        return {"suggestions": suggestions, "confidence": 0.7, "summary": "Architectural suggestions generated"}