"""List AI providers and which keys are configured."""

import typer
from repoforge.providers.factory import ProviderFactory


def run_providers():
    factory = ProviderFactory()
    status = factory.status()

    typer.echo("")
    typer.echo("📦 RepoForge Providers")
    typer.echo("=" * 50)
    typer.echo(f"Default provider : {status['default']}")
    typer.echo("")

    configured = set(status["configured"])

    typer.echo("Configured (ready to use):")
    for name in status["available"]:
        if name in configured:
            mark = "✅"
            typer.echo(f"  {mark} {name}")

    typer.echo("")
    typer.echo("Available (need API key):")
    for name in status["available"]:
        if name not in configured:
            typer.echo(f"  ⚪ {name}")

    typer.echo("")
    typer.echo("Set REPOFORGE_PROVIDER=<name> or put the matching *_API_KEY in .env")
    typer.echo("")
