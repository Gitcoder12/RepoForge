"""Stable, credential-free command-line entry point."""

import json
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
    run_tests: bool = typer.Option(
        False,
        "--run-tests",
        help="Execute the target repository's pytest suite (only for trusted repositories).",
    ),
    test_timeout: int = typer.Option(
        120,
        "--test-timeout",
        min=1,
        max=1800,
        help="Maximum seconds to wait when --run-tests is enabled.",
    ),
) -> None:
    """Run static validation; target tests require explicit --run-tests opt-in."""
    import asyncio

    result = asyncio.run(
        Validator(str(repo_path)).validate(
            run_tests=run_tests,
            test_timeout=test_timeout,
        )
    )
    if result.get("passed"):
        typer.echo("Static validation passed.")
        test_status = result.get("test_run", {}).get("status")
        if test_status == "passed":
            typer.echo("Target test suite passed.")
        elif test_status == "skipped":
            typer.echo("Target tests were not executed. Use --run-tests for trusted repositories.")
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


def _load_environment() -> None:
    """Load a local .env file without overriding variables from the shell."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(override=False)


@app.command()
def providers() -> None:
    """Show provider configuration without displaying API keys."""
    from repoforge.providers.factory import ProviderFactory

    _load_environment()
    typer.echo("RepoForge model providers")
    for item in ProviderFactory().list_status():
        if item["kind"] == "local":
            state = "local endpoint (connectivity not checked)"
        else:
            state = "configured" if item["configured"] else f"missing {item['credential_variable']}"
        typer.echo(f"  {item['name']}: {state}")


@app.command()
def generate(
    prompt: str = typer.Argument(..., help="Prompt to send to the selected model."),
    provider: str = typer.Option(
        ..., "--provider", "-p", help="Primary provider name; selection is explicit."
    ),
    model: str | None = typer.Option(
        None, "--model", help="Override the primary provider's default model."
    ),
    standby: list[str] = typer.Option(
        [],
        "--standby",
        help="Explicit standby provider; repeat the option to declare an ordered route.",
    ),
    allow_rate_limit_fallback: bool = typer.Option(
        False,
        "--allow-rate-limit-fallback",
        help="Permit standby after quota/rate-limit failures; may incur additional charges.",
    ),
    timeout: float = typer.Option(45.0, "--timeout", min=1.0, max=180.0),
    max_tokens: int = typer.Option(2048, "--max-tokens", min=1, max=32768),
) -> None:
    """Generate with one explicit provider or a declared primary/standby route."""
    from repoforge.orchestrator import AIOrchestrator
    from repoforge.providers.errors import ProviderError

    _load_environment()
    try:
        if standby:
            from repoforge.providers.failover import StandbyProviderPool

            route = StandbyProviderPool.from_factory(
                primary_name=provider.strip().lower(),
                standby_names=tuple(name.strip().lower() for name in standby),
                model_overrides={provider.strip().lower(): model} if model else {},
                timeout=timeout,
                allow_rate_limit_fallback=allow_rate_limit_fallback,
            )
            result = route.generate_with_report(prompt, max_tokens=max_tokens)
            response = result.text
            for attempt in result.attempts:
                typer.echo(
                    f"Route: {attempt.provider_name} / {attempt.model} — {attempt.status}"
                    + (f" ({attempt.error_type})" if attempt.error_type else ""),
                    err=True,
                )
        else:
            if allow_rate_limit_fallback:
                raise ValueError("--allow-rate-limit-fallback requires at least one --standby")
            orchestrator = AIOrchestrator()
            orchestrator.register_real_provider(provider, model=model, timeout=timeout)
            response = orchestrator.generate(
                prompt,
                provider=provider.strip().lower(),
                max_tokens=max_tokens,
            )
    except (ProviderError, ValueError) as exc:
        typer.echo(f"Provider error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    typer.echo(response)


@app.command("blacksmith")
def blacksmith_command(
    repo_path: Path = typer.Argument(
        Path("."),
        exists=True,
        file_okay=False,
        readable=True,
        help="Local repository to inspect.",
    ),
    apply_fixes: bool = typer.Option(
        False,
        "--apply",
        help="Apply safe create-if-absent repairs. The default is a dry run.",
    ),
) -> None:
    """Rank a repository and propose/apply bounded, non-destructive repairs."""
    from repoforge.blacksmith import Blacksmith

    try:
        result = Blacksmith(repo_path).run(apply_fixes=apply_fixes)
    except ValueError as exc:
        typer.echo(f"Blacksmith error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("megazords")
def megazords_command(
    repo_paths: list[Path] = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        readable=True,
        help="Two or more local repositories to compare.",
    ),
    top_k: int = typer.Option(10, "--top", min=1, max=100),
) -> None:
    """Suggest complementary repository combinations without modifying them."""
    from repoforge.megazord import MegazordEngine

    try:
        result = MegazordEngine().suggest(repo_paths, top_k=top_k)
    except ValueError as exc:
        typer.echo(f"Megazord error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("test")
def test_command(
    repo_path: Path = typer.Argument(
        Path("."),
        exists=True,
        file_okay=False,
        readable=True,
        help="Local repository to inspect or test.",
    ),
    execute: bool = typer.Option(
        False,
        "--execute",
        help="Execute detected test commands. Only use this for repositories you trust.",
    ),
    timeout: int = typer.Option(120, "--timeout", min=1, max=1800),
) -> None:
    """Discover test commands; execution is opt-in and is not sandboxed."""
    from repoforge.testing import TestForge

    try:
        result = TestForge(repo_path).run(execute=execute, timeout=timeout)
    except ValueError as exc:
        typer.echo(f"TestForge error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    if execute and result["status"] in {"failed", "scan_incomplete"}:
        raise typer.Exit(code=1)
