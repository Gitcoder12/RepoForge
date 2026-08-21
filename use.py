import typer
from pathlib import Path

CONFIG = Path.home() / ".repoforge"
CONFIG.mkdir(exist_ok=True)

ACTIVE = CONFIG / "active_provider.txt"


def run_use(provider: str):
    ACTIVE.write_text(provider)
    typer.echo(f"✅ Active provider set to: {provider}")