"""Provider protocol for synchronous and asynchronous model adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class BaseProvider(ABC):
    name = "base"

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "", **kwargs: Any) -> str:
        raise NotImplementedError

    async def stream(
        self, prompt: str, system_prompt: str = "", **kwargs: Any
    ) -> AsyncIterator[str]:
        yield self.generate(prompt, system_prompt, **kwargs)

    def available(self) -> bool:
        return True

    def get_capabilities(self) -> dict[str, Any]:
        return {"name": self.name, "streaming": True}
