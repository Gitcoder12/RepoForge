"""OpenAI / ChatGPT Provider"""

from __future__ import annotations

import os
from typing import AsyncGenerator, Dict, Any, Optional

from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI GPT provider"""

    def _initialize(self):
        from openai import OpenAI

        key = self.api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=key or "sk-mock")
        self._models = self.config.get(
            "models",
            ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs,
    ) -> str:
        if not (self.api_key or os.getenv("OPENAI_API_KEY")):
            return (
                "[OpenAI] No OPENAI_API_KEY set. Using mock response.\n"
                f"Prompt was: {prompt[:200]}..."
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model = kwargs.pop("model", self._models[0])
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
        if not (self.api_key or os.getenv("OPENAI_API_KEY")):
            yield self.generate(prompt, system_prompt, **kwargs)
            return

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model = kwargs.pop("model", self._models[0])
        kwargs.pop("api_key", None)

        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            **kwargs,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "models": self.models,
            "streaming": True,
            "max_tokens": 16384,
            "context_window": 128000,
        }

    @property
    def name(self) -> str:
        return "openai"

    @property
    def models(self) -> list:
        return self._models
