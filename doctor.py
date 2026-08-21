"""System diagnostics for RepoForge."""

import os
import platform
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def run_doctor():
    print("")
    print("🩺 RepoForge Doctor")
    print("=" * 50)

    print(f"Python        : {sys.version.split()[0]}")
    print(f"Platform      : {platform.system()} {platform.release()}")
    print(f"CWD           : {Path.cwd()}")

    # Keys
    print("")
    print("API Keys:")
    keys = [
        ("DEEPSEEK_API_KEY", "DeepSeek"),
        ("OPENAI_API_KEY", "OpenAI"),
        ("OPENROUTER_API_KEY", "OpenRouter"),
        ("ANTHROPIC_API_KEY", "Anthropic"),
        ("GROQ_API_KEY", "Groq"),
        ("XAI_API_KEY", "xAI / Grok"),
        ("GROK_API_KEY", "Grok (alias)"),
        ("MISTRAL_API_KEY", "Mistral"),
        ("GEMINI_API_KEY", "Gemini"),
        ("GOOGLE_API_KEY", "Google"),
        ("TOGETHER_API_KEY", "Together"),
        ("FIREWORKS_API_KEY", "Fireworks"),
        ("PERPLEXITY_API_KEY", "Perplexity"),
        ("COHERE_API_KEY", "Cohere"),
        ("AZURE_OPENAI_API_KEY", "Azure OpenAI"),
    ]
    found = 0
    for env_name, label in keys:
        val = os.getenv(env_name)
        if val:
            masked = val[:6] + "..." + val[-4:] if len(val) > 12 else "***"
            print(f"  ✅ {label:<16} {env_name} = {masked}")
            found += 1
        else:
            print(f"  ⚪ {label:<16} {env_name} (not set)")

    print("")
    print(f"Keys found    : {found}")

    # Default provider
    from repoforge.providers.factory import ProviderFactory
    factory = ProviderFactory()
    print(f"Default       : {factory.default}")
    print(f"Configured    : {', '.join(factory.list_configured())}")

    # Quick generate test with mock
    print("")
    print("Quick test (mock):")
    try:
        p = factory.get("mock")
        out = p.generate("ping")
        print(f"  ✅ Mock provider responded ({len(out)} chars)")
    except Exception as e:
        print(f"  ❌ Mock failed: {e}")

    print("")
    print("Doctor finished.")
    print("")
