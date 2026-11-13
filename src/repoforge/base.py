"""Base interfaces for RepoForge providers and agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

logger = logging.getLogger("RepoForge.Base")


class BaseProvider(ABC):
    def __init__(self, api_key: str | None = None, **kwargs: Any) -> None:
        self.api_key = api_key
        self.config = kwargs
        self.client: Any = None
        self._initialize()

    @abstractmethod
    def _initialize(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "", **kwargs: Any) -> str:
        raise NotImplementedError

    @abstractmethod
    async def stream(
        self, prompt: str, system_prompt: str = "", **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError

    @abstractmethod
    def get_capabilities(self) -> dict[str, Any]:
        raise NotImplementedError

    def available(self) -> bool:
        return self.client is not None

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def models(self) -> list[str]:
        raise NotImplementedError


class BaseAgent(ABC):
    def __init__(self, provider: BaseProvider | None = None) -> None:
        self.provider = provider
        self.name = self.__class__.__name__

    @abstractmethod
    async def analyze(self, context: dict[str, Any]) -> Any:
        """Analyze repository context and return a proposal."""
        raise NotImplementedError
