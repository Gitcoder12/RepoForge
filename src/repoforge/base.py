"""
RepoForge Base Interfaces
Defines the abstract classes for all Providers and Agents.
"""

from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, Dict, Any
import logging

logger = logging.getLogger("RepoForge.Base")

class BaseProvider(ABC):
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.config = kwargs
        self.client = None
        self._initialize()

    @abstractmethod
    def _initialize(self):
        pass

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        pass

    @abstractmethod
    async def stream(
        self, prompt: str, system_prompt: str = "", **kwargs
    ) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        pass

    def available(self) -> bool:
        return self.client is not None

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def models(self) -> list:
        pass


class BaseAgent(ABC):
    def __init__(self, provider: Optional[BaseProvider] = None):
        self.provider = provider
        self.name = self.__class__.__name__

    @abstractmethod
    async def analyze(self, context: Dict[str, Any]) -> Any:
        """
        Asynchronously analyze the repo context and return a Proposal.
        Must be implemented by all agents.
        """
        pass
