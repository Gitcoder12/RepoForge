"""
RepoForge Provider Factory – maximum API key support.

Supported providers and their env keys:

  openai          OPENAI_API_KEY
  deepseek        DEEPSEEK_API_KEY
  anthropic       ANTHROPIC_API_KEY
  openrouter      OPENROUTER_API_KEY
  groq            GROQ_API_KEY
  xai / grok      XAI_API_KEY  or  GROK_API_KEY
  mistral         MISTRAL_API_KEY
  gemini          GEMINI_API_KEY  or  GOOGLE_API_KEY
  together        TOGETHER_API_KEY
  fireworks       FIREWORKS_API_KEY
  perplexity      PERPLEXITY_API_KEY
  cohere          COHERE_API_KEY
  azure           AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT
  ollama          (no key, local http://localhost:11434)
  mock            (offline)

Set REPOFORGE_PROVIDER=deepseek (or any name above) to choose default.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base import BaseProvider
from .mock import MockProvider


def _env(*names: str) -> Optional[str]:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None


# Provider definitions: name -> (env keys, base_url, default models)
PROVIDER_DEFS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "env": ["OPENAI_API_KEY"],
        "base_url": None,
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o1-mini"],
    },
    "deepseek": {
        "env": ["DEEPSEEK_API_KEY", "OPENAI_API_KEY"],
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "openrouter": {
        "env": ["OPENROUTER_API_KEY"],
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            "openrouter/auto",
            "deepseek/deepseek-chat",
            "anthropic/claude-sonnet-4",
            "openai/gpt-4o",
            "google/gemini-2.5-pro",
            "x-ai/grok-3",
            "meta-llama/llama-3.3-70b-instruct",
            "mistralai/mistral-large",
        ],
    },
    "anthropic": {
        "env": ["ANTHROPIC_API_KEY"],
        "base_url": None,  # special SDK
        "models": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022"],
        "special": "anthropic",
    },
    "groq": {
        "env": ["GROQ_API_KEY"],
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
    },
    "xai": {
        "env": ["XAI_API_KEY", "GROK_API_KEY"],
        "base_url": "https://api.x.ai/v1",
        "models": ["grok-3", "grok-3-mini", "grok-2"],
    },
    "grok": {  # alias
        "env": ["XAI_API_KEY", "GROK_API_KEY"],
        "base_url": "https://api.x.ai/v1",
        "models": ["grok-3", "grok-3-mini", "grok-2"],
    },
    "mistral": {
        "env": ["MISTRAL_API_KEY"],
        "base_url": "https://api.mistral.ai/v1",
        "models": ["mistral-large-latest", "mistral-small-latest", "codestral-latest"],
    },
    "gemini": {
        "env": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    },
    "together": {
        "env": ["TOGETHER_API_KEY"],
        "base_url": "https://api.together.xyz/v1",
        "models": ["meta-llama/Llama-3.3-70B-Instruct-Turbo", "deepseek-ai/DeepSeek-V3"],
    },
    "fireworks": {
        "env": ["FIREWORKS_API_KEY"],
        "base_url": "https://api.fireworks.ai/inference/v1",
        "models": ["accounts/fireworks/models/llama-v3p3-70b-instruct"],
    },
    "perplexity": {
        "env": ["PERPLEXITY_API_KEY"],
        "base_url": "https://api.perplexity.ai",
        "models": ["sonar-pro", "sonar"],
    },
    "cohere": {
        "env": ["COHERE_API_KEY"],
        "base_url": "https://api.cohere.ai/compatibility/v1",
        "models": ["command-r-plus", "command-r"],
    },
    "azure": {
        "env": ["AZURE_OPENAI_API_KEY"],
        "base_url": os.getenv("AZURE_OPENAI_ENDPOINT"),  # user must set
        "models": [os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")],
    },
    "ollama": {
        "env": [],
        "base_url": os.getenv("OLLAMA_HOST", "http://localhost:11434/v1"),
        "models": ["llama3.2", "llama3.1", "qwen2.5-coder", "deepseek-coder-v2", "codellama"],
        "no_key": True,
    },
    "mock": {
        "env": [],
        "base_url": None,
        "models": ["mock-v1"],
        "special": "mock",
    },
}


class ProviderFactory:
    """Create any supported provider by name."""

    def __init__(self, default: Optional[str] = None):
        # Prefer explicit env, then first available key, else mock
        self.default = (
            default
            or os.getenv("REPOFORGE_PROVIDER")
            or self._detect_best()
            or "mock"
        ).lower()

    def _detect_best(self) -> Optional[str]:
        """Pick the first provider that has a real key."""
        priority = [
            "deepseek", "openai", "openrouter", "anthropic",
            "groq", "xai", "mistral", "gemini", "together",
            "fireworks", "perplexity", "cohere", "azure", "ollama",
        ]
        for name in priority:
            defn = PROVIDER_DEFS.get(name, {})
            if defn.get("no_key") or defn.get("special") == "mock":
                continue
            if _env(*defn.get("env", [])):
                return name
        # Ollama if running locally is still useful
        return None

    def get(self, name: Optional[str] = None, **kwargs) -> BaseProvider:
        name = (name or self.default).lower()
        if name not in PROVIDER_DEFS:
            name = "mock"

        defn = PROVIDER_DEFS[name]

        if defn.get("special") == "mock":
            return MockProvider()

        if defn.get("special") == "anthropic":
            try:
                from .anthropic import AnthropicProvider
                key = _env(*defn["env"])
                return AnthropicProvider(api_key=key, **kwargs)
            except Exception:
                return MockProvider()

        # Everything else uses the compatible client
        from .compatible import CompatibleProvider

        key = _env(*defn.get("env", []))
        base_url = defn.get("base_url")
        models = defn.get("models", ["default"])

        # Azure needs endpoint
        if name == "azure" and not base_url:
            return MockProvider()

        return CompatibleProvider(
            api_key=key,
            base_url=base_url,
            models=models,
            name=name,
            **kwargs,
        )

    def list_available(self) -> List[str]:
        return list(PROVIDER_DEFS.keys())

    def list_configured(self) -> List[str]:
        """Providers that currently have keys (or need no key)."""
        result = []
        for name, defn in PROVIDER_DEFS.items():
            if defn.get("special") == "mock" or defn.get("no_key"):
                result.append(name)
                continue
            if _env(*defn.get("env", [])):
                result.append(name)
        return result

    def status(self) -> Dict[str, Any]:
        return {
            "default": self.default,
            "available": self.list_available(),
            "configured": self.list_configured(),
        }


def get_provider(provider_name: str, **kwargs) -> BaseProvider:
    return ProviderFactory().get(provider_name, **kwargs)


# Keep old name for compatibility
PROVIDER_MAP = {k: k for k in PROVIDER_DEFS}
