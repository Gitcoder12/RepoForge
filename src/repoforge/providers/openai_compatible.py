"""OpenAI-compatible chat provider for OpenRouter and compatible gateways."""

from __future__ import annotations

from typing import Any, AsyncGenerator

from repoforge.base import BaseProvider


class OpenAICompatibleProvider(BaseProvider):
    """Connect to OpenAI-compatible APIs without assuming a fixed model catalog.

    OpenRouter, OpenAI, DeepSeek, Groq, LM Studio, and vLLM can be used when
    their endpoint implements the OpenAI chat-completions interface.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        provider_name: str = "openai-compatible",
        default_headers: dict[str, str] | None = None,
        timeout: float = 90.0,
        max_retries: int = 2,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("An API key is required for this provider")
        if not model or not model.strip():
            raise ValueError("A model identifier is required")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")

        self.model = model.strip()
        self.base_url = base_url.strip() if base_url else None
        self.provider_name = provider_name.strip().lower()
        self.default_headers = dict(default_headers or {})
        self.timeout = timeout
        self.max_retries = max_retries
        super().__init__(api_key=api_key)

    def _initialize(self) -> None:
        try:
            from openai import AsyncOpenAI, OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI-compatible providers require the optional 'openai' dependency. "
                "Install with: pip install -e '.[providers]'"
            ) from exc

        options: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }
        if self.base_url:
            options["base_url"] = self.base_url
        if self.default_headers:
            options["default_headers"] = self.default_headers
        self.client = OpenAI(**options)
        self.async_client = AsyncOpenAI(**options)

    def generate(self, prompt: str, system_prompt: str = "", **kwargs: Any) -> str:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.pop("temperature", 0.1),
            max_tokens=kwargs.pop("max_tokens", 4096),
            **kwargs,
        )
        if not response.choices:
            raise RuntimeError("The model returned no completion choices")
        message = response.choices[0].message
        content = message.content
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("The model returned an empty or non-text response")
        return content.strip()

    async def stream(
        self, prompt: str, system_prompt: str = "", **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        stream = await self.async_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.pop("temperature", 0.1),
            max_tokens=kwargs.pop("max_tokens", 4096),
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            text = chunk.choices[0].delta.content
            if isinstance(text, str) and text:
                yield text

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "streaming": True,
            "openai_compatible": True,
        }

    @property
    def name(self) -> str:
        return self.provider_name

    @property
    def models(self) -> list[str]:
        return [self.model]
