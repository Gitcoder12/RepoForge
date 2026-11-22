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
    provider: str | None = typer.Option(
        None, "--provider", "-p", help="Primary provider name; selection is explicit."
    ),
    model: str | None = typer.Option(
        None, "--model", help="Override the primary provider's default model."
    ),
    standby: list[str] = typer.Option(
        [],
        "--standby",
        help="Explicit standby provider; repeat the option to declare an ordered route.",
    ),
    route_config: Path | None = typer.Option(
        None,
        "--route-config",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Load the explicit provider route from a JSON config file.",
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
        if route_config is not None:
            if provider is not None or standby or allow_rate_limit_fallback:
                raise ValueError(
                    "Use either --route-config or explicit --provider/--standby options, not both"
                )
            from repoforge.providers.failover import StandbyProviderPool

            config = json.loads(route_config.read_text(encoding="utf-8"))
            primary = config.get("primary")
            if not isinstance(primary, dict) or not isinstance(primary.get("provider"), str):
                raise ValueError("route config requires primary.provider")
            standby_entries = config.get("standby", [])
            if not isinstance(standby_entries, list):
                raise ValueError("route config standby must be a JSON array")
            standby_names = []
            model_overrides = {}
            for entry in standby_entries:
                if not isinstance(entry, dict) or not isinstance(entry.get("provider"), str):
                    raise ValueError("each standby entry requires a provider name")
                if entry.get("enabled", True):
                    name = entry["provider"].strip().lower()
                    standby_names.append(name)
                    override = entry.get("model_override")
                    if override is not None:
                        if not isinstance(override, str) or not override.strip():
                            raise ValueError("standby model_override must be a non-empty string")
                        model_overrides[name] = override
            primary_name = primary["provider"].strip().lower()
            primary_model = primary.get("model_override")
            if primary_model is not None:
                if not isinstance(primary_model, str) or not primary_model.strip():
                    raise ValueError("primary model_override must be a non-empty string")
                model_overrides[primary_name] = primary_model
            policy = config.get("policy", {})
            if not isinstance(policy, dict):
                raise ValueError("route config policy must be a JSON object")
            rate_limit_fallback = policy.get("fallback_on_rate_limit", False)
            if not isinstance(rate_limit_fallback, bool):
                raise ValueError("fallback_on_rate_limit must be a boolean")
            route = StandbyProviderPool.from_factory(
                primary_name=primary_name,
                standby_names=tuple(standby_names),
                model_overrides=model_overrides,
                timeout=timeout,
                allow_rate_limit_fallback=rate_limit_fallback,
            )
            result = route.generate_with_report(prompt, max_tokens=max_tokens)
            response = result.text
            for attempt in result.attempts:
                typer.echo(
                    f"Route: {attempt.provider_name} / {attempt.model} — {attempt.status}"
                    + (f" ({attempt.error_type})" if attempt.error_type else ""),
                    err=True,
                )
        elif provider is not None:
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
        else:
            raise ValueError("Specify --provider or --route-config")
    except (ProviderError, ValueError, OSError, json.JSONDecodeError) as exc:
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
    """Rank a repository and report bounded repairs plus selectable upgrade paths."""
    from repoforge.blacksmith import Blacksmith

    try:
        result = Blacksmith(repo_path).run(apply_fixes=apply_fixes)
    except ValueError as exc:
        typer.echo(f"Blacksmith error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("upgrade")
def upgrade_command(
    repo_path: Path = typer.Argument(
        Path("."),
        exists=True,
        file_okay=False,
        readable=True,
        help="Local repository to assess and plan upgrades for.",
    ),
    profile: str = typer.Option(
        "all",
        "--profile",
        help="Upgrade path: all, foundation, security, quality, delivery, or maintainability.",
    ),
    select: str | None = typer.Option(
        None,
        "--select",
        help="Comma-separated option IDs to select from the generated upgrade catalogue.",
    ),
) -> None:
    """Rank available repository upgrades and produce a review-only plan."""
    from repoforge.blacksmith import Blacksmith
    from repoforge.upgrades import UpgradePlanner

    try:
        snapshot = Blacksmith(repo_path).inspect()
        planner = UpgradePlanner()
        report = planner.build(snapshot)
        option_ids = (
            [item.strip() for item in select.split(",") if item.strip()] if select else None
        )
        result = planner.select(report, profile=profile, option_ids=option_ids)
    except ValueError as exc:
        typer.echo(f"UpgradeForge error: {exc}", err=True)
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


@app.command("model-lab")
def model_lab_command(
    target: list[str] = typer.Option(
        [],
        "--target",
        "-t",
        help="Explicit provider:model target; repeat to compare several models.",
    ),
    catalog: bool = typer.Option(
        False,
        "--catalog",
        help="Show suggested model targets and provider configuration status.",
    ),
    timeout: float = typer.Option(45.0, "--timeout", min=1.0, max=180.0),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Optional path for the JSON evaluation report.",
    ),
) -> None:
    """Compare selected model endpoints on the deterministic Model Lab smoke suite."""
    from repoforge.model_lab import ModelLab, ModelTarget, suggested_models

    _load_environment()
    if catalog:
        from repoforge.providers.factory import ProviderFactory

        typer.echo("Suggested model starting points")
        for item in suggested_models():
            typer.echo(f"  {item['role']}: {item['target']}")
            typer.echo(f"    {item['reason']} {item['cost_note']}")
        typer.echo("\nProvider configuration")
        for item in ProviderFactory().list_status():
            state = (
                "local endpoint (connectivity not checked)"
                if item["kind"] == "local"
                else "configured"
                if item["configured"]
                else f"missing {item['credential_variable']}"
            )
            typer.echo(f"  {item['name']}: {state}")
        return

    if not target:
        typer.echo("Select at least one model with --target provider:model.", err=True)
        raise typer.Exit(code=2)

    try:
        selected = [ModelTarget.parse(item) for item in target]
        report = ModelLab().run(selected, timeout=timeout)
        rendered = json.dumps(report, indent=2, ensure_ascii=False)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered + "\n", encoding="utf-8")
            typer.echo(f"Report written to {output}")
        typer.echo(rendered)
    except (ValueError, OSError) as exc:
        typer.echo(f"Model Lab error: {exc}", err=True)
        raise typer.Exit(code=2) from exc


@app.command("forge")
def forge_command(
    repo_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        readable=True,
        help="Local Git repository to inspect and improve.",
    ),
    request: str = typer.Argument(..., help="Requested repository improvement."),
    provider: str | None = typer.Option(
        None, "--provider", help="Explicit model provider; omitted means read-only inspection."
    ),
    model: str | None = typer.Option(None, "--model", help="Optional model override."),
    apply: bool = typer.Option(
        False, "--apply", help="Apply proposed changes after exact path approvals."
    ),
    approve: list[str] = typer.Option(
        [], "--approve", help="Exact repository-relative path to approve; repeat as needed."
    ),
    run_tests: bool = typer.Option(
        False, "--run-tests", help="Run target tests after apply; only for trusted repositories."
    ),
    timeout: int = typer.Option(120, "--timeout", min=1, max=1800),
    output: Path | None = typer.Option(None, "--output", help="Optional JSON report path."),
) -> None:
    """Run the integrated inspect → plan → propose → approve → validate workflow."""
    from repoforge.forge import ForgeWorkflow

    try:
        report = ForgeWorkflow().run(
            repo_path,
            request,
            provider=provider,
            model=model,
            apply=apply,
            approved_paths=set(approve),
            run_tests=run_tests,
            timeout=timeout,
        )
        rendered = json.dumps(report, indent=2, ensure_ascii=False, default=str)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered + "\\n", encoding="utf-8")
            typer.echo(f"Report written to {output}")
        typer.echo(rendered)
    except (ValueError, OSError, RuntimeError) as exc:
        typer.echo(f"Forge failed safely: {exc}", err=True)
        raise typer.Exit(code=2) from exc
