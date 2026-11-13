"""Offline-first orchestrator with explicit provider registration."""

from __future__ import annotations

from typing import Any

from repoforge.providers.base import BaseProvider


class ProviderManager:
    def __init__(self, providers: dict[str, BaseProvider]):
        self.providers = providers
        self.enabled: set[str] = set()

    def enable(self, name: str) -> None:
        if name not in self.providers:
            raise KeyError(f"Unknown provider: {name}")
        self.enabled.add(name)

    def disable(self, name: str) -> None:
        self.enabled.discard(name)


class AIOrchestrator:
    """Coordinates explicitly registered providers; never calls a provider implicitly."""

    def __init__(self):
        self.providers: dict[str, BaseProvider] = {}
        self.pm = ProviderManager(self.providers)

    def register(self, name: str, provider: BaseProvider) -> None:
        if not name or not isinstance(provider, BaseProvider):
            raise ValueError("A non-empty provider name and BaseProvider instance are required")
        self.providers[name] = provider

    def generate(self, prompt: str, provider: str | None = None, **kwargs: Any) -> str:
        selected = provider
        if selected is None:
            selected = next(iter(self.pm.enabled), None)
        if selected is None or selected not in self.providers:
            raise RuntimeError("No provider is enabled; register and enable a provider first")
        return self.providers[selected].generate(prompt, **kwargs)
