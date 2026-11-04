from .base import BaseProvider
from .mock import MockProvider
from .factory import ProviderFactory, get_provider, PROVIDER_DEFS, PROVIDER_MAP
from .compatible import CompatibleProvider

# --- TIER 1: Frontier Models ---
try:
    from .openai import OpenAIProvider
except ImportError:
    OpenAIProvider = None

try:
    from .anthropic import AnthropicProvider
except ImportError:
    AnthropicProvider = None

try:
    from .google import GeminiProvider
except ImportError:
    GeminiProvider = None

try:
    from .deepseek import DeepSeekProvider
except ImportError:
    DeepSeekProvider = None

# --- TIER 2: High-Speed & Open Source ---
try:
    from .groq import GroqProvider
except ImportError:
    GroqProvider = None

try:
    from .mistral import MistralProvider
except ImportError:
    MistralProvider = None

try:
    from .together import TogetherProvider
except ImportError:
    TogetherProvider = None

try:
    from .cohere import CohereProvider
except ImportError:
    CohereProvider = None

# --- TIER 3: Aggregators & Local ---
try:
    from .openrouter import OpenRouterProvider
except ImportError:
    OpenRouterProvider = None

try:
    from .ollama import OllamaProvider
except ImportError:
    OllamaProvider = None

try:
    from .huggingface import HuggingFaceProvider
except ImportError:
    HuggingFaceProvider = None

try:
    from .perplexity import PerplexityProvider
except ImportError:
    PerplexityProvider = None

# --- EXPORTS ---
__all__ = [
    # Core
    "BaseProvider",
    "MockProvider",
    "ProviderFactory",
    "get_provider",
    "PROVIDER_DEFS",
    "PROVIDER_MAP",
    "CompatibleProvider",
    
    # Frontier
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "DeepSeekProvider",
    
    # Fast & Open
    "GroqProvider",
    "MistralProvider",
    "TogetherProvider",
    "CohereProvider",
    
    # Aggregators & Local
    "OpenRouterProvider",
    "OllamaProvider",
    "HuggingFaceProvider",
    "PerplexityProvider",
]
