"""Shared role-agent implementation."""

from __future__ import annotations

import json
from typing import Any

from repoforge.base import BaseProvider


class RoleAgent:
    def __init__(self, name: str, system_prompt: str, provider: BaseProvider) -> None:
        if not name.strip():
            raise ValueError("Agent name must not be empty")
        if not isinstance(provider, BaseProvider):
            raise TypeError("A BaseProvider instance is required")
        self.name = name
        self.system_prompt = system_prompt.strip()
        self.provider = provider

    def run(self, task: str, context: dict[str, Any] | None = None) -> str:
        if not task.strip():
            raise ValueError("Task must not be empty")
        sections = [task.strip()]
        if context:
            sections.append("Structured context:")
            sections.append(json.dumps(context, ensure_ascii=False, sort_keys=True, default=str))
        return self.provider.generate(
            "\n\n".join(sections),
            system_prompt=self.system_prompt,
        )
