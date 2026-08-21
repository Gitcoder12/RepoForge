from typing import AsyncGenerator, Dict, Any

from repoforge.providers.base import BaseProvider


class MockProvider(BaseProvider):
    def _initialize(self):
        pass

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        return (
            "🤖 Mock Provider\n"
            "====================\n"
            f"Prompt: {prompt}\n"
            "\nRepoForge orchestration is working!"
        )

    async def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        yield self.generate(prompt, system_prompt, **kwargs)

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "chat": True,
            "stream": True,
            "vision": False,
            "tools": False,
        }

    @property
    def name(self) -> str:
        return "Mock Provider"

    @property
    def models(self) -> list:
        return ["mock-v1"]