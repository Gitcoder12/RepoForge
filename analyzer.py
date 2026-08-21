"""
RepoForge Code Intelligence

Base interface for language analyzers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class CodeAnalyzer(ABC):
    """
    Base class for code analysis engines.
    """


    def __init__(
        self,
        file_path: str,
    ):

        self.file_path = file_path



    @abstractmethod
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze source code.

        Must return structured intelligence.
        """

        pass