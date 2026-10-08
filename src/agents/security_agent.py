from typing import Dict, Any
from .base_agent import BaseAgent

class SecurityAgent(BaseAgent):
    def __init__(self, provider: str = "openai", **kwargs):
        super().__init__(provider=provider, **kwargs)
        self.name = "SecurityAgent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        scan = context.get("scan", {})
        prompt = f"Identify security issues in this repository.\nFiles: {scan.get('statistics', {}).get('total_files', 0)}\nLanguages: {list(scan.get('languages', {}).keys())}\nProvide specific security recommendations."
        system = "You are a security expert. Suggest concrete security improvements."
        try:
            response = self._call_llm(prompt, system)
            suggestions = [s.strip() for s in response.split('\n') if s.strip()]
        except:
            suggestions = ["Use environment variables for secrets", "Add input validation", "Implement rate limiting", "Add authentication middleware"]
        return {"suggestions": suggestions, "confidence": 0.8, "summary": "Security recommendations generated"}