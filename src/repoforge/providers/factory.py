"""Explicit provider registry for the installable RepoForge package."""

from __future__ import annotations

import os
from typing import Any

from .compatible import OpenAICompatibleProvider
from .errors import ProviderConfigurationError


PROVIDER_DEFINITIONS: dict[str, dict[str, Any]] = {
    "deepseek": {
        "env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-flash",
        "kind": "remote",
    },
    "openai": {
        "env": "OPENAI_API_KEY",
        "base_url": None,
        "model": "gpt-4o-mini",
        "kind": "remote",
    },
    "openrouter": {
        "env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openrouter/auto",
        "kind": "remote",
    },
    "groq": {
        "env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-120b",
        "kind": "remote",
    },
    "ollama": {
        "env": None,
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
        "kind": "local",
    },
}


class ProviderFactory:
    """Build only the provider explicitly requested by the caller.

    A missing key, exhausted quota, auth failure, or connection error is never
    converted into mock output or an implicit paid-provider switch.
    """

    def list_status(self) -> list[dict[str, Any]]:
        """Return provider readiness without revealing credential values."""
        status = []
        for name, definition in PROVIDER_DEFINITIONS.items():
            env_name = definition["env"]
            configured = bool(os.getenv(env_name, "").strip()) if env_name else True
            status.append(
                {
                    "name": name,
                    "configured": configured,
                    "kind": definition["kind"],
                    "credential_variable": env_name,
                }
            )
        return status

    def get(
        self,
        provider_name: str,
        *,
        model: str | None = None,
        timeout: float = 45.0,
    ) -> OpenAICompatibleProvider:
        """Construct the named provider or fail with an actionable error."""
        name = provider_name.strip().lower() if isinstance(provider_name, str) else ""
        definition = PROVIDER_DEFINITIONS.get(name)
        if definition is None:
            supported = ", ".join(PROVIDER_DEFINITIONS)
            raise ProviderConfigurationError(
                f"Unknown provider '{provider_name}'. Supported providers: {supported}."
            )

        env_name = definition["env"]
        if env_name:
            api_key = os.getenv(env_name, "").strip()
            if not api_key:
                raise ProviderConfigurationError(
                    f"{name} is not configured. Set {env_name}; no mock response will be used."
                )
        else:
            # OpenAI-compatible local servers require a non-empty SDK token,
            # but Ollama does not use it for authentication.
            api_key = "ollama-local"

        return OpenAICompatibleProvider(
            provider_name=name,
            api_key=api_key,
            base_url=definition["base_url"],
            model=model or definition["model"],
            timeout=timeout,
        )
