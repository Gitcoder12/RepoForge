import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.config_dir = Path.home() / ".repoforge"
        self.config_file = self.config_dir / "config.yaml"
        self.config_dir.mkdir(exist_ok=True)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        return {"providers": {}, "default_provider": "openai"}
    
    def save_config(self):
        with open(self.config_file, 'w') as f:
            yaml.safe_dump(self.config, f, default_flow_style=False)
    
    def get_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        return self.config.get("providers", {}).get(provider_name)
    
    def set_provider_config(self, provider_name: str, config: Dict[str, Any]):
        if "providers" not in self.config:
            self.config["providers"] = {}
        self.config["providers"][provider_name] = config
        self.save_config()
    
    def get_api_key(self, provider_name: str) -> Optional[str]:
        env_key = f"{provider_name.upper()}_API_KEY"
        return os.getenv(env_key)
    
    def set_default_provider(self, provider_name: str):
        self.config["default_provider"] = provider_name
        self.save_config()
    
    def get_default_provider(self) -> str:
        return self.config.get("default_provider", "openai")

config = Config()