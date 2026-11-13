"""Stable, credential-free command-line entry point."""

from pathlib import Path

import typer

from repoforge import __version__
from repoforge.validator import Validator

app = typer.Typer(
    name="repoforge",
    help="Inspect and validate Python repositories.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def version() -> None:
    """Print the installed RepoForge version."""
    typer.echo(f"RepoForge {__version__}")


@app.command()
def validate(
    repo_path: Path = typer.Argument(Path("."), exists=True, file_okay=False, readable=True),
) -> None:
    """Run static validation and the repository's pytest suite."""
    import asyncio

    result = asyncio.run(Validator(str(repo_path)).validate())
    typer.echo("Validation passed." if result.get("passed") else f"Validation failed: {result.get('reason')}")
    if not result.get("passed"):
        raise typer.Exit(code=1)
