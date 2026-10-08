import os
import sys

# 1. Ensure the directory exists
os.makedirs("src/repoforge", exist_ok=True)

# 2. Write plugin_manager.py
pm_code = """import yaml
from pathlib import Path

class PluginManager:
    def __init__(self):
        self.config_dir = Path.home() / ".repoforge"
        self.config_dir.mkdir(exist_ok=True)
        self.plugins_file = self.config_dir / "plugins.yaml"
        self.plugins = self._load_plugins()
    
    def _load_plugins(self):
        if self.plugins_file.exists():
            with open(self.plugins_file, 'r') as f:
                return yaml.safe_load(f) or {"enabled": [], "disabled": []}
        return {"enabled": [], "disabled": []}
    
    def _save_plugins(self):
        with open(self.plugins_file, 'w') as f:
            yaml.safe_dump(self.plugins, f)
    
    def enable(self, name):
        if name in self.plugins["disabled"]:
            self.plugins["disabled"].remove(name)
        if name not in self.plugins["enabled"]:
            self.plugins["enabled"].append(name)
        self._save_plugins()
        print(f"Enabled {name}")
    
    def list_enabled(self):
        return self.plugins["enabled"]
"""
with open("src/repoforge/plugin_manager.py", "w") as f:
    f.write(pm_code)

# 3. Write orchestrator.py
orch_code = """from .plugin_manager import PluginManager
from .providers.base import BaseProvider

class AIOrchestrator:
    def __init__(self):
        self.pm = PluginManager()
        self.providers = {}
    
    def register(self, name, provider):
        self.providers[name] = provider
        print(f"Registered: {name}")
    
    def generate(self, prompt, provider_name=None):
        if not provider_name:
            enabled = self.pm.list_enabled()
            if enabled:
                provider_name = enabled[0]
        
        if provider_name and provider_name in self.providers:
            return self.providers[provider_name].generate(prompt)
        
        return "Error: No provider available."
"""
with open("src/repoforge/orchestrator.py", "w") as f:
    f.write(orch_code)

print("Files created. Running test...")
os.system("python test_pm.py")