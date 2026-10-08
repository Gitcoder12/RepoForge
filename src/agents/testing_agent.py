from typing import Dict, Any
from .base_agent import BaseAgent

class TestingAgent(BaseAgent):
    def __init__(self, provider: str = "openai", **kwargs):
        super().__init__(provider=provider, **kwargs)
        self.name = "TestingAgent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        scan = context.get("scan", {})
        metadata = scan.get("metadata", {})
        has_tests = metadata.get("has_tests_dir", False)
        if has_tests:
            suggestions = ["Improve test coverage", "Add integration tests", "Add property-based testing"]
        else:
            suggestions = ["Add a tests/ directory", "Write unit tests", "Setup pytest or unittest", "Add test runner to CI"]
        return {"suggestions": suggestions, "confidence": 0.9, "summary": "Testing improvements proposed"}