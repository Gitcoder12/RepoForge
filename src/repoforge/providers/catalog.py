"""Optional live model catalog discovery for supported gateways."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from repoforge.providers.factory import OPENROUTER_BASE_URL


def list_models(
    provider: str = "openrouter",
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: float = 20.0,
) -> list[dict[str, Any]]:
    """Fetch model IDs from an enabled OpenAI-compatible /models endpoint.

    Results are provider-supplied metadata, not a guarantee that each model is
    enabled for the account or supports chat completions.
    """
    load_dotenv()
    name = provider.strip().lower()
    if name == "openrouter":
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        endpoint = base_url or os.getenv("OPENROUTER_BASE_URL", OPENROUTER_BASE_URL)
    elif name == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY")
        endpoint = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    elif name in {"openai-compatible", "compatible"}:
        key = api_key or os.getenv("REPOFORGE_API_KEY") or "local-no-key"
        endpoint = base_url or os.getenv("REPOFORGE_BASE_URL")
        if not endpoint:
            raise ValueError("Set REPOFORGE_BASE_URL or pass --base-url")
    else:
        raise ValueError("Model catalog is supported for openrouter, openai, or openai-compatible")

    if not key:
        raise ValueError(f"No API key configured for {name}")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Live model discovery requires the optional 'openai' dependency. "
            "Install with: pip install -e '.[providers]'"
        ) from exc

    client = OpenAI(
        api_key=key,
        base_url=endpoint,
        timeout=timeout,
        max_retries=1,
    )
    try:
        response = client.models.list()
    except Exception as exc:
        raise RuntimeError(f"Could not fetch the {name} model catalog: {exc}") from exc

    catalog: list[dict[str, Any]] = []
    for model in response.data:
        model_id = getattr(model, "id", None)
        if not isinstance(model_id, str) or not model_id.strip():
            continue
        catalog.append(
            {
                "id": model_id,
                "created": getattr(model, "created", None),
                "owned_by": getattr(model, "owned_by", None),
            }
        )
    return sorted(catalog, key=lambda item: item["id"].lower())
