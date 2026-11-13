"""Deterministic provider for tests and offline demonstrations."""

from typing import Any

from repoforge.providers.base import BaseProvider


class MockProvider(BaseProvider):
    name = "mock"

    def __init__(self, response: str = "RepoForge mock response"):
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def generate(self, prompt: str, system_prompt: str = "", **kwargs: Any) -> str:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "kwargs": kwargs})
        return self.response
