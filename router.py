"""
RepoForge Smart Model Router

Chooses the best available provider/model based on:
- repository languages & size
- task type (code, docs, security, architecture, etc.)
- which API keys the user actually has
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple


# Priority lists: first match with a real key wins
# Maps task category → ordered list of provider names
TASK_ROUTES: Dict[str, List[str]] = {
    "coding": [
        "deepseek",      # strongest cheap code model
        "mistral",       # codestral-class
        "openai",
        "anthropic",
        "xai",
        "groq",
        "openrouter",
        "gemini",
    ],
    "architecture": [
        "anthropic",     # best at planning / structure
        "xai",           # Grok strong reasoning
        "openai",
        "deepseek",
        "gemini",
        "openrouter",
        "mistral",
    ],
    "analysis": [
        "deepseek",
        "anthropic",
        "openai",
        "xai",
        "gemini",
        "openrouter",
        "groq",
    ],
    "docs": [
        "openai",
        "gemini",
        "anthropic",
        "deepseek",
        "mistral",
        "openrouter",
    ],
    "security": [
        "anthropic",
        "openai",
        "deepseek",
        "xai",
        "openrouter",
    ],
    "fast": [
        "groq",
        "gemini",
        "deepseek",
        "mistral",
        "openai",
    ],
    "default": [
        "deepseek",
        "openai",
        "openrouter",
        "anthropic",
        "xai",
        "groq",
        "mistral",
        "gemini",
        "ollama",
        "mock",
    ],
}

# Language → preferred category bias
LANG_BIAS: Dict[str, str] = {
    "Python": "coding",
    "JavaScript": "coding",
    "TypeScript": "coding",
    "Go": "coding",
    "Rust": "coding",
    "Java": "coding",
    "C": "coding",
    "C++": "coding",
    "Markdown": "docs",
    "HTML": "docs",
    "CSS": "docs",
}


def _has_key(provider: str) -> bool:
    """Check if user has a usable key for this provider."""
    env_map = {
        "deepseek": ["DEEPSEEK_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY"],
        "groq": ["GROQ_API_KEY"],
        "xai": ["XAI_API_KEY", "GROK_API_KEY"],
        "grok": ["XAI_API_KEY", "GROK_API_KEY"],
        "mistral": ["MISTRAL_API_KEY"],
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "together": ["TOGETHER_API_KEY"],
        "fireworks": ["FIREWORKS_API_KEY"],
        "perplexity": ["PERPLEXITY_API_KEY"],
        "cohere": ["COHERE_API_KEY"],
        "azure": ["AZURE_OPENAI_API_KEY"],
        "ollama": [],  # no key needed
        "mock": [],
    }
    keys = env_map.get(provider, [])
    if provider in ("ollama", "mock"):
        return True
    return any(os.getenv(k) for k in keys)


def detect_task_category(prompt: str, scan: Optional[Dict[str, Any]] = None) -> str:
    """Infer task category from the user prompt + repo signals."""
    p = (prompt or "").lower()

    if any(w in p for w in ("security", "vulnerab", "cve", "auth", "secret", "owasp")):
        return "security"
    if any(w in p for w in ("architect", "structure", "design", "refactor", "modular")):
        return "architecture"
    if any(w in p for w in ("doc", "readme", "comment", "explain", "guide")):
        return "docs"
    if any(w in p for w in ("fast", "quick", "cheap", "speed")):
        return "fast"
    if any(w in p for w in ("code", "type hint", "bug", "fix", "implement", "test", "error handling")):
        return "coding"
    if any(w in p for w in ("analy", "review", "quality", "health", "improve", "score")):
        return "analysis"

    # Bias from primary language if available
    if scan:
        langs = scan.get("languages") or {}
        if isinstance(langs, dict) and langs:
            # pick language with most files/lines if nested
            primary = None
            if "profile" in scan and isinstance(scan["profile"], dict):
                primary = scan["profile"].get("primary_language")
            if not primary:
                # simple: first key
                primary = next(iter(langs.keys()), None)
            if primary and primary in LANG_BIAS:
                return LANG_BIAS[primary]

    return "default"


class AIRouter:
    """
    Selects the best available provider for a given task + repo.
    """

    def __init__(self):
        self.routes = TASK_ROUTES

    def select(
        self,
        prompt: str = "",
        scan: Optional[Dict[str, Any]] = None,
        prefer: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Returns (provider_name, reason).

        Priority:
        1. Explicit REPOFORGE_PROVIDER env (user override)
        2. prefer= argument
        3. Smart route based on task + available keys
        4. mock
        """
        # Hard override
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

        # Last resort
        if _has_key("ollama"):
            return "ollama", "fallback to local ollama"
        return "mock", "no API keys found → mock"

    def choose(self, task_type: str = "default"):
        """Legacy API for orchestrator — returns {free, paid} model lists."""
        # Map task types to categories we know
        category = task_type if task_type in self.routes else "default"
        if task_type in ("coding", "code", "implement", "fix"):
            category = "coding"
        elif task_type in ("architecture", "design", "refactor"):
            category = "architecture"
        elif task_type in ("docs", "documentation", "readme"):
            category = "docs"
        elif task_type in ("security", "sec"):
            category = "security"
        elif task_type in ("analysis", "review", "audit"):
            category = "analysis"

        candidates = [c for c in self.routes.get(category, self.routes["default"]) if _has_key(c)]
        if not candidates:
            candidates = ["mock"]
        # Orchestrator indexes route["free"][0] as model name — use provider names
        return {"free": candidates, "paid": candidates}

    def route_task(self, task_type: str) -> List[str]:
        """Legacy helper used by older orchestrator code."""
        return self.routes.get(task_type, self.routes["default"])
