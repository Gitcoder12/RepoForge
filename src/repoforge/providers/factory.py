"""Environment-driven provider construction and model discovery."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from repoforge.base import BaseProvider
from repoforge.providers.anthropic import AnthropicProvider
from repoforge.providers.openai_compatible import OpenAICompatibleProvider

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def create_provider(
    provider: str = "openrouter",
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: float = 90.0,
    max_retries: int = 2,
) -> BaseProvider:
    """Create a provider using explicit arguments first, then environment settings.

    OpenRouter exposes a broad model catalog through one OpenAI-compatible endpoint.
    Other OpenAI-compatible gateways can be configured with a base URL.
    """
    load_dotenv()
    name = provider.strip().lower()

    if name == "openrouter":
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        selected_model = model or os.getenv("OPENROUTER_MODEL", "openrouter/auto")
        if not key:
            raise ValueError("Set OPENROUTER_API_KEY or pass api_key")
        headers: dict[str, str] = {}
        referer = os.getenv("OPENROUTER_HTTP_REFERER")
        title = os.getenv("OPENROUTER_APP_TITLE", "RepoForge")
        if referer:
            headers["HTTP-Referer"] = referer
        if title:
            headers["X-Title"] = title
        return OpenAICompatibleProvider(
            api_key=key,
            model=selected_model,
            base_url=base_url or os.getenv("OPENROUTER_BASE_URL", OPENROUTER_BASE_URL),
            provider_name="openrouter",
            default_headers=headers,
            timeout=timeout,
            max_retries=max_retries,
        )

    if name == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY")
        selected_model = model or os.getenv("OPENAI_MODEL")
        if not key:
            raise ValueError("Set OPENAI_API_KEY or pass api_key")
        if not selected_model:
            raise ValueError("Set OPENAI_MODEL or pass --model")
        return OpenAICompatibleProvider(
            api_key=key,
            model=selected_model,
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
            provider_name="openai",
            timeout=timeout,
            max_retries=max_retries,
        )

    if name == "anthropic":
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        selected_model = model or os.getenv("ANTHROPIC_MODEL")
        if not key:
            raise ValueError("Set ANTHROPIC_API_KEY or pass api_key")
        if not selected_model:
            raise ValueError("Set ANTHROPIC_MODEL or pass --model")
        return AnthropicProvider(
            api_key=key,
            model=selected_model,
            timeout=timeout,
            max_retries=max_retries,
        )

    if name in {"openai-compatible", "compatible"}:
        key = api_key or os.getenv("REPOFORGE_API_KEY") or "local-no-key"
        selected_model = model or os.getenv("REPOFORGE_MODEL")
        endpoint = base_url or os.getenv("REPOFORGE_BASE_URL")
        if not endpoint:
            raise ValueError("Set REPOFORGE_BASE_URL or pass --base-url")
        if not selected_model:
            raise ValueError("Set REPOFORGE_MODEL or pass --model")
        return OpenAICompatibleProvider(
            api_key=key,
            model=selected_model,
            base_url=endpoint,
            provider_name="openai-compatible",
            timeout=timeout,
            max_retries=max_retries,
        )

    raise ValueError(
        "Unsupported provider. Choose openrouter, openai, anthropic, or openai-compatible."
    )


def provider_status() -> list[dict[str, Any]]:
    """Return configuration status without exposing API keys or secret values."""
    load_dotenv()
    return [
        {
            "provider": "openrouter",
            "configured": bool(os.getenv("OPENROUTER_API_KEY")),
            "model": os.getenv("OPENROUTER_MODEL", "openrouter/auto"),
        },
        {
            "provider": "openai",
            "configured": bool(os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_MODEL")),
            "model": os.getenv("OPENAI_MODEL") or "(set OPENAI_MODEL)",
        },
        {
            "provider": "anthropic",
            "configured": bool(os.getenv("ANTHROPIC_API_KEY") and os.getenv("ANTHROPIC_MODEL")),
            "model": os.getenv("ANTHROPIC_MODEL") or "(set ANTHROPIC_MODEL)",
        },
        {
            "provider": "openai-compatible",
            "configured": bool(os.getenv("REPOFORGE_BASE_URL") and os.getenv("REPOFORGE_MODEL")),
            "model": os.getenv("REPOFORGE_MODEL") or "(set REPOFORGE_MODEL)",
        },
    ]
