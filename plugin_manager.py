from pathlib import Path
from typing import Dict, Any, Optional
import importlib
import yaml
from .config import config

class PluginManager:
    """Manages provider plugins"""
    
    def __init__(self):
        self.plugins_dir = Path.home() / ".repoforge" / "plugins"
        self.plugins_dir.mkdir(exist_ok=True)
        self.installed_plugins = self._load_plugins()
    
    def _load_plugins(self) -> Dict[str, Dict[str, Any]]:
        plugins_file = self.plugins_dir / "installed.yaml"
        if plugins_file.exists():
            with open(plugins_file, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _save_plugins(self):
        plugins_file = self.plugins_dir / "installed.yaml"
        with open(plugins_file, 'w') as f:
            yaml.safe_dump(self.installed_plugins, f, default_flow_style=False)
    
    def install(self, provider_name: str, provider_config: Optional[Dict[str, Any]] = None) -> bool:
        """Install a provider plugin"""
        from .providers.registry import ProviderRegistry
        
        provider_class = ProviderRegistry.get_provider(provider_name)
        if not provider_class:
            return False
        
        if provider_name in self.installed_plugins:
            return False
        
        self.installed_plugins[provider_name] = {
            "enabled": True,
            "config": provider_config or {}
        }
        self._save_plugins()
        return True
    
    def uninstall(self, provider_name: str) -> bool:
        """Uninstall a provider plugin"""
        if provider_name not in self.installed_plugins:
            return False
        
        del self.installed_plugins[provider_name]
        self._save_plugins()
        return True
    
    def enable(self, provider_name: str) -> bool:
        """Enable a provider"""
        if provider_name not in self.installed_plugins:
            return False
        
        self.installed_plugins[provider_name]["enabled"] = True
        self._save_plugins()
        return True
    
    def disable(self, provider_name: str) -> bool:
        """Disable a provider"""
        if provider_name not in self.installed_plugins:
            return False
        
        self.installed_plugins[provider_name]["enabled"] = False
        self._save_plugins()
        return True
    
    def get_enabled_providers(self) -> list:
        """Get list of enabled providers"""
        return [name for name, info in self.installed_plugins.items() if info.get("enabled", False)]
    
    def get_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a provider"""
        plugin = self.installed_plugins.get(provider_name)
        return plugin.get("config") if plugin else None