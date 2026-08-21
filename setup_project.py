import os

files = {
    "pyproject.toml": """[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "repoforge"
version = "0.1.0"
description = "AI Orchestration Platform"
requires-python = ">=3.9"
dependencies = [
    "openai>=1.0.0",
    "anthropic>=0.7.0",
    "google-generativeai>=0.3.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
    "rich>=13.0.0",
    "typer>=0.9.0",
]

[tool.setuptools.packages.find]
where = ["src"]
""",
    "src/repoforge/__init__.py": "__version__ = '0.1.0'",
    "src/repoforge/providers/__init__.py": "",
    "src/repoforge/generators/__init__.py": "",
    "src/repoforge/workflows/__init__.py": "",
    "src/repoforge/config.py": """import os
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
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {"providers": {}, "default_provider": "openai"}
    
    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self.config, f, default_flow_style=False)
    
    def get_api_key(self, provider_name: str) -> Optional[str]:
        env_key = f"{provider_name.upper()}_API_KEY"
        return os.getenv(env_key)

config = Config()
""",
    "src/repoforge/cli.py": """import typer
from rich.console import Console

app = typer.Typer(help="RepoForge - AI Orchestration Platform")
console = Console()

@app.command()
def hello():
    console.print('[bold green]RepoForge is alive! 🚀[/bold green]')

if __name__ == "__main__":
    app()
"""
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created: {path}")

print("\\n✅ Done! Now run: pip install -e .")