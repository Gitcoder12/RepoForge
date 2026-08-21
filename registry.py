from typing import Dict, Type, Optional
from .base import BaseProvider

class ProviderRegistry:
    """Registry for AI providers"""
    
    _providers: Dict[str, Type[BaseProvider]] = {}
    
    @classmethod
    def register(cls, provider_class: Type[BaseProvider]):
        """Register a provider class"""
        instance = provider_class.__new__(provider_class)
        cls._providers[instance.name] = provider_class
        return provider_class
    
    @classmethod
    def get_provider(cls, name: str) -> Optional[Type[BaseProvider]]:
        """Get provider class by name"""
        return cls._providers.get(name)
    
    @classmethod
    def list_providers(cls) -> list:
        """List all registered providers"""
        return list(cls._providers.keys())
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if provider is registered"""
        return name in cls._providers