"""Deterministic provider for tests and offline demonstrations."""

from __future__ import annotations

from typing import Any, AsyncGenerator

from repoforge.base import BaseProvider


class MockProvider(BaseProvider):
    def __init__(self, response: str = "RepoForge mock response") -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []
        super().__init__(api_key=None)

    def _initialize(self) -> None:
        self.client = self

    def generate(self, prompt: str, system_prompt: str = "", **kwargs: Any) -> str:
        self.calls.append(
            {"prompt": prompt, "system_prompt": system_prompt, "kwargs": kwargs}
        )
        return self.response

    async def stream(
        self, prompt: str, system_prompt: str = "", **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        yield self.generate(prompt, system_prompt, **kwargs)

    def get_capabilities(self) -> dict[str, Any]:
        return {"name": self.name, "streaming": True, "offline": True}

    def available(self) -> bool:
        return True

    @property
    def name(self) -> str:
        return "mock"

    @property
    def models(self) -> list[str]:
        return ["mock"]
