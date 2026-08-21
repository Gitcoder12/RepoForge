"""
Generic OpenAI-compatible provider.
Works with any service that speaks the OpenAI chat completions API.
"""

from __future__ import annotations

import os
from typing import Any, AsyncGenerator, Dict, List, Optional

from .base import BaseProvider


class CompatibleProvider(BaseProvider):
    """
    OpenAI-compatible endpoint.
    Used for: Groq, xAI, Mistral, Gemini (via proxy), Together, Fireworks,
    Azure, DeepSeek, OpenRouter, local vLLM, etc.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        models: Optional[List[str]] = None,
        name: str = "compatible",
        **kwargs,
    ):
        self._name = name
        self._default_models = models or ["default"]
        self._base_url = base_url
        super().__init__(api_key=api_key, **kwargs)

    def _initialize(self):
        from openai import OpenAI

        key = self.api_key or "sk-mock"
        kwargs = {"api_key": key}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        self.client = OpenAI(**kwargs)
        self._models = self.config.get("models", self._default_models)

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs,
    ) -> str:
        if not self.api_key and self._name != "ollama":
            return (
                f"[{self._name}] No API key set. Using mock response.\n"
                f"Prompt was: {prompt[:180]}..."
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model = kwargs.pop("model", self._models[0])
        kwargs.pop("api_key", None)

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[{self._name}] Error: {e}"

    async def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        yield self.generate(prompt, system_prompt, **kwargs)

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "models": self.models,
            "streaming": True,
            "compatible": True,
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def models(self) -> list:
        return self._models
