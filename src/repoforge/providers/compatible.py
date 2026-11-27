"""Explicit OpenAI-compatible provider adapter with bounded request behavior."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

from repoforge.base import BaseProvider
from repoforge.providers.errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTimeoutError,
)


class OpenAICompatibleProvider(BaseProvider):
    """A no-hidden-fallback adapter for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        *,
        provider_name: str,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout: float = 45.0,
        client: Any = None,
    ) -> None:
        if not provider_name.strip():
            raise ValueError("provider_name must not be empty")
        if not api_key.strip():
            raise ProviderConfigurationError(
                f"{provider_name} credentials are missing; configure its API key first."
            )
        if not model.strip():
            raise ValueError("model must not be empty")
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not 1 <= timeout <= 180
        ):
            raise ValueError("timeout must be between 1 and 180 seconds")

        self.provider_name = provider_name
        self._model = model
        self._injected_client = client
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=float(timeout),
        )

    def _initialize(self) -> None:
        """Create a client with SDK retries disabled to avoid surprise repeat charges."""
        if self._injected_client is not None:
            self.client = self._injected_client
            return

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderConfigurationError(
                'Install the provider SDK with: pip install -e ".[providers]"'
            ) from exc

        options: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": self.config["timeout"],
            "max_retries": 0,
        }
        if self.config.get("base_url"):
            options["base_url"] = self.config["base_url"]
        self.client = OpenAI(**options)

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs: Any,
    ) -> str:
        """Make one request and surface quota/auth/network failures explicitly."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if not isinstance(system_prompt, str):
            raise ValueError("system_prompt must be a string")

        model = kwargs.pop("model", self._model)
        max_tokens = kwargs.pop("max_tokens", 2048)
        temperature = kwargs.pop("temperature", 0.2)
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be a non-empty string")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1:
            raise ValueError("max_tokens must be a positive integer")

        messages: list[dict[str, str]] = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # GPT-6.2 Astra/Sol use the newer completion-token field and reject
        # sampling controls on Chat Completions. Match OpenRouter-prefixed IDs too.
        model_id = model.rsplit("/", 1)[-1]
        request_options: dict[str, Any] = {
            "model": model,
            "messages": messages,
            **kwargs,
        }
        request_options.pop("max_tokens", None)
        token_field = (
            "max_completion_tokens"
            if model_id in {"gpt-6.2-astra", "gpt-6.2-sol"}
            else "max_tokens"
        )
        request_options[token_field] = max_tokens
        if model_id not in {"gpt-6.2-astra", "gpt-6.2-sol"}:
            request_options["temperature"] = temperature

        try:
            response = self.client.chat.completions.create(**request_options)
        except Exception as exc:
            error_name = type(exc).__name__
            status_code = getattr(exc, "status_code", None)
            if error_name == "RateLimitError" or status_code in (402, 429):
                raise ProviderRateLimitError(
                    f"{self.provider_name} rate limit or quota exhausted. "
                    "No automatic provider switch or retry was attempted."
                ) from exc
            if error_name == "AuthenticationError" or status_code in (401, 403):
                raise ProviderAuthenticationError(
                    f"{self.provider_name} rejected its credentials."
                ) from exc
            if error_name in ("APITimeoutError", "TimeoutError"):
                raise ProviderTimeoutError(
                    f"{self.provider_name} did not respond within "
                    f"{self.config['timeout']:.0f} seconds."
                ) from exc
            if error_name in ("APIConnectionError", "ConnectionError"):
                raise ProviderConnectionError(
                    f"Could not connect to the configured {self.provider_name} endpoint."
                ) from exc
            if status_code is not None:
                raise ProviderRequestError(
                    f"{self.provider_name} returned HTTP {status_code}."
                ) from exc
            raise ProviderRequestError(
                f"{self.provider_name} request failed ({error_name})."
            ) from exc

        choices = getattr(response, "choices", None)
        if not choices:
            raise ProviderResponseError(f"{self.provider_name} returned no completion choices.")
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise ProviderResponseError(f"{self.provider_name} returned an empty completion.")
        return content

    async def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Run the blocking SDK request off-loop; true token streaming is not advertised."""
        response = await asyncio.to_thread(self.generate, prompt, system_prompt, **kwargs)
        yield response

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "models": self.models,
            "streaming": False,
            "timeout_seconds": self.config["timeout"],
            "automatic_retries": 0,
            "automatic_fallback": False,
        }

    def available(self) -> bool:
        return self.client is not None

    @property
    def name(self) -> str:
        return self.provider_name

    @property
    def models(self) -> list[str]:
        return [self._model]
