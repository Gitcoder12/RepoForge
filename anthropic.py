"""Anthropic Claude provider."""

from __future__ import annotations

import os
from typing import AsyncGenerator, Dict, Any, List, Optional

from .base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider."""

    def _initialize(self):
        try:
            from anthropic import Anthropic
            key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
            self.client = Anthropic(api_key=key or "sk-mock")
            self._models = self.config.get(
                "models",
                ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022"],
            )
        except Exception:
            self.client = None
            self._models = ["claude-3-5-sonnet-20241022"]

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs,
    ) -> str:
        if not self.client or not (self.api_key or os.getenv("ANTHROPIC_API_KEY")):
            return (
                "[Anthropic] No ANTHROPIC_API_KEY set. Using mock response.\n"
                f"Prompt was: {prompt[:200]}..."
            )

        model = kwargs.pop("model", self._models[0])
        kwargs.pop("api_key", None)

        response = self.client.messages.create(
            model=model,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
        )
        return response.content[0].text

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
            "streaming": False,
            "max_tokens": 8192,
            "context_window": 200000,
        }

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def models(self) -> list:
        return self._models
