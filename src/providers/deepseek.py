"""
DeepSeek Provider – OpenAI-compatible API.
"""

from __future__ import annotations

import os
from typing import AsyncGenerator, Dict, Any, Optional

from .base import BaseProvider


class DeepSeekProvider(BaseProvider):
    """DeepSeek Chat / Reasoner via official API."""

    def _initialize(self):
        from openai import OpenAI

        key = (
            self.api_key
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        self.client = OpenAI(
            api_key=key or "sk-mock",
            base_url="https://api.deepseek.com",
        )
        self._models = self.config.get(
            "models",
            ["deepseek-chat", "deepseek-reasoner"],
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs,
    ) -> str:
        if not (self.api_key or os.getenv("DEEPSEEK_API_KEY")):
            return (
                "[DeepSeek] No DEEPSEEK_API_KEY set. "
                "Using mock response.\n"
                f"Prompt was: {prompt[:200]}..."
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model = kwargs.pop("model", self._models[0])
        # Remove unsupported kwargs that OpenAI client might not like
        kwargs.pop("api_key", None)

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content or ""

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
            "max_tokens": 8192,
            "context_window": 64000,
        }

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def models(self) -> list:
        return self._models
