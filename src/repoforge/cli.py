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
    if result.get("passed"):
        typer.echo("Validation passed.")
        return

    typer.echo(f"Validation failed: {result.get('reason')}", err=True)
    for key in ("results", "invalid_paths"):
        for item in result.get(key, []):
            if isinstance(item, dict):
                location = item.get("file", item.get("path", "unknown"))
                detail = item.get("error", item.get("reason", "validation failed"))
                typer.echo(f"  {location}: {detail}", err=True)
    output = result.get("output")
    if isinstance(output, str) and output.strip():
        typer.echo("Test output:", err=True)
        typer.echo(output[-8000:], err=True)
    raise typer.Exit(code=1)
