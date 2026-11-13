"""Native Anthropic Messages API provider."""

from __future__ import annotations

from typing import Any, AsyncGenerator

from repoforge.base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Provider adapter for Anthropic Claude models."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float = 90.0,
        max_retries: int = 2,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("ANTHROPIC_API_KEY is required")
        if not model or not model.strip():
            raise ValueError("An Anthropic model identifier is required")
        self.model = model.strip()
        self.timeout = timeout
        self.max_retries = max_retries
        super().__init__(api_key=api_key)

    def _initialize(self) -> None:
        try:
            from anthropic import AsyncAnthropic, Anthropic
        except ImportError as exc:
            raise RuntimeError(
                "Anthropic support requires the optional 'anthropic' dependency. "
                "Install with: pip install -e '.[providers]'"
            ) from exc
        options: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }
        self.client = Anthropic(**options)
        self.async_client = AsyncAnthropic(**options)

    def generate(self, prompt: str, system_prompt: str = "", **kwargs: Any) -> str:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=kwargs.pop("max_tokens", 4096),
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.pop("temperature", 0.1),
            **kwargs,
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        if not text.strip():
            raise RuntimeError("Anthropic returned an empty or non-text response")
        return text.strip()

    async def stream(
        self, prompt: str, system_prompt: str = "", **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        async with self.async_client.messages.stream(
            model=self.model,
            max_tokens=kwargs.pop("max_tokens", 4096),
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.pop("temperature", 0.1),
            **kwargs,
        ) as stream:
            async for text in stream.text_stream:
                if text:
                    yield text

    def get_capabilities(self) -> dict[str, Any]:
        return {"name": self.name, "model": self.model, "streaming": True}

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def models(self) -> list[str]:
        return [self.model]
