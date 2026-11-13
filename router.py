"""
RepoForge Smart Model Router

Chooses the best available provider/model based on:
- repository languages & size
- task type (code, docs, security, architecture, etc.)
- which API keys the user actually has
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional, Tuple

# Import all the provider classes we wired up earlier
from . import (
    OpenAIProvider, AnthropicProvider, DeepSeekProvider, 
    GroqProvider, MistralProvider, OpenRouterProvider, 
    OllamaProvider, MockProvider
)

logger = logging.getLogger("RepoForge.AIRouter")

# Priority lists: first match with a real key wins
TASK_ROUTES: Dict[str, List[str]] = {
    "coding": ["deepseek", "mistral", "openai", "anthropic", "xai", "groq", "openrouter", "gemini"],
    "architecture": ["anthropic", "xai", "openai", "deepseek", "gemini", "openrouter", "mistral"],
    "analysis": ["deepseek", "anthropic", "openai", "xai", "gemini", "openrouter", "groq"],
    "docs": ["openai", "gemini", "anthropic", "deepseek", "mistral", "openrouter"],
    "security": ["anthropic", "openai", "deepseek", "xai", "openrouter"],
    "fast": ["groq", "gemini", "deepseek", "mistral", "openai"],
    "default": ["deepseek", "openai", "openrouter", "anthropic", "xai", "groq", "mistral", "gemini", "ollama", "mock"],
}

LANG_BIAS: Dict[str, str] = {
    "Python": "coding", "JavaScript": "coding", "TypeScript": "coding",
    "Go": "coding", "Rust": "coding", "Java": "coding", "C": "coding",
    "C++": "coding", "Markdown": "docs", "HTML": "docs", "CSS": "docs",
}

def _has_key(provider: str) -> bool:
    env_map = {
        "deepseek": ["DEEPSEEK_API_KEY"], "openai": ["OPENAI_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"], "anthropic": ["ANTHROPIC_API_KEY"],
        "groq": ["GROQ_API_KEY"], "xai": ["XAI_API_KEY", "GROK_API_KEY"],
        "grok": ["XAI_API_KEY", "GROK_API_KEY"], "mistral": ["MISTRAL_API_KEY"],
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"], "together": ["TOGETHER_API_KEY"],
        "fireworks": ["FIREWORKS_API_KEY"], "perplexity": ["PERPLEXITY_API_KEY"],
        "cohere": ["COHERE_API_KEY"], "azure": ["AZURE_OPENAI_API_KEY"],
        "ollama": [], "mock": [],
    }
    keys = env_map.get(provider, [])
    if provider in ("ollama", "mock"):
        return True
    return any(os.getenv(k) for k in keys)

def detect_task_category(prompt: str, scan: Optional[Dict[str, Any]] = None) -> str:
    p = (prompt or "").lower()

    if any(w in p for w in ("security", "vulnerab", "cve", "auth", "secret", "owasp")): return "security"
    if any(w in p for w in ("architect", "structure", "design", "refactor", "modular")): return "architecture"
    if any(w in p for w in ("doc", "readme", "comment", "explain", "guide")): return "docs"
    if any(w in p for w in ("fast", "quick", "cheap", "speed")): return "fast"
    if any(w in p for w in ("code", "type hint", "bug", "fix", "implement", "test", "error handling")): return "coding"
    if any(w in p for w in ("analy", "review", "quality", "health", "improve", "score")): return "analysis"

    if scan:
        langs = scan.get("languages") or {}
        if isinstance(langs, dict) and langs:
            primary = None
            if "profile" in scan and isinstance(scan["profile"], dict):
                primary = scan["profile"].get("primary_language")
            if not primary:
                primary = next(iter(langs.keys()), None)
            if primary and primary in LANG_BIAS:
                return LANG_BIAS[primary]

    return "default"


class AIRouter:
    def __init__(self):
        self.routes = TASK_ROUTES
        # Map provider names to their actual classes
        self.provider_classes = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "deepseek": DeepSeekProvider,
            "groq": GroqProvider,
            "mistral": MistralProvider,
            "openrouter": OpenRouterProvider,
            "ollama": OllamaProvider,
            "mock": MockProvider,
        }

    def select(self, prompt: str = "", scan: Optional[Dict[str, Any]] = None, prefer: Optional[str] = None) -> Tuple[str, str]:
        forced = os.getenv("REPOFORGE_PROVIDER", "").strip().lower()
        if forced and forced != "auto":
            if _has_key(forced) or forced == "mock":
                return forced, f"forced by REPOFORGE_PROVIDER={forced}"

        if prefer:
            prefer = prefer.lower()
            if _has_key(prefer):
                return prefer, f"preferred provider {prefer}"

        category = detect_task_category(prompt, scan)
        candidates = self.routes.get(category, self.routes["default"])

        for name in candidates:
            if _has_key(name):
                return name, f"best for '{category}' task → {name}"

        if _has_key("ollama"):
            return "ollama", "fallback to local ollama"
        return "mock", "no API keys found → mock"

    def choose(self, task_type: str = "default"):
        category = task_type if task_type in self.routes else "default"
        if task_type in ("coding", "code", "implement", "fix"): category = "coding"
        elif task_type in ("architecture", "design", "refactor"): category = "architecture"
        elif task_type in ("docs", "documentation", "readme"): category = "docs"
        elif task_type in ("security", "sec"): category = "security"
        elif task_type in ("analysis", "review", "audit"): category = "analysis"

        candidates = [c for c in self.routes.get(category, self.routes["default"]) if _has_key(c)]
        if not candidates: candidates = ["mock"]
        return {"free": candidates, "paid": candidates}

    def route_task(self, task_type: str) -> List[str]:
        return self.routes.get(task_type, self.routes["default"])

    #  THIS IS THE NEW MAGIC METHOD:
    def instantiate(self, provider_name: str, **kwargs) -> Any:
        """
        Takes the string name from select() and returns the actual class object.
        Falls back to MockProvider if the key is missing or class failed to import.
        """
        provider_cls = self.provider_classes.get(provider_name)
        
        if not provider_cls:
            logger.warning(f"Provider '{provider_name}' not imported. Falling back to Mock.")
            return MockProvider(**kwargs)
            
        try:
            logger.info(f"Instantiating {provider_name} provider...")
            return provider_cls(**kwargs)
        except Exception as e:
            logger.error(f"Failed to instantiate {provider_name}: {e}. Falling back to Mock.")
            return MockProvider(**kwargs)
