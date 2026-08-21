"""
RepoForge AI Provider Base Interface
"""

from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, Dict, Any


class BaseProvider(ABC):
    """
    Standard interface for all AI providers.
    """


    def __init__(
        self,
        api_key: Optional[str] = None,
        **kwargs
    ):

        self.api_key = api_key

        self.config = kwargs

        self.client = None

        self._initialize()



    @abstractmethod
    def _initialize(self):
        """
        Setup provider client.
        """
        pass



    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs
    ) -> str:
        """
        Generate AI response.
        """
        pass



    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI output.
        """
        pass



    @abstractmethod
    def get_capabilities(
        self
    ) -> Dict[str, Any]:
        """
        Provider information.
        """
        pass



    def available(self) -> bool:
        """
        Check provider availability.
        """

        return True



    @property
    @abstractmethod
    def name(self) -> str:
        pass



    @property
    @abstractmethod
    def models(self) -> list:
        pass