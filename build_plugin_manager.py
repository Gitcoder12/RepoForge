import yaml
from pathlib import Path
from typing import List

class PluginManager:
    def __init__(self):
        self.config_dir = Path.home() / ".repoforge"
        self.config_dir.mkdir(exist_ok=True)
        self.plugins_file = self.config_dir / "plugins.yaml"
        self.plugins = self._load_plugins()
    
    def _load_plugins(self) -> dict:
        if self.plugins_file.exists():
            with open(self.plugins_file, 'r') as f:
                return yaml.safe_load(f) or {"enabled": [], "disabled": []}
        return {"enabled": [], "disabled": []}
    
    def _save_plugins(self):
        with open(self.plugins_file, 'w') as f:
            yaml.safe_dump(self.plugins, f)
    
    def enable(self, name: str):
        if name in self.plugins["disabled"]:
            self.plugins["disabled"].remove(name)
        if name not in self.plugins["enabled"]:
            self.plugins["enabled"].append(name)
        self._save_plugins()
        print(f"Enabled {name}")
    
    def disable(self, name: str):
        if name in self.plugins["enabled"]:
            self.plugins["enabled"].remove(name)
        if name not in self.plugins["disabled"]:
            self.plugins["disabled"].append(name)
        self._save_plugins()
        print(f"Disabled {name}")
    
    def list_enabled(self) -> List[str]:
        return self.plugins["enabled"]