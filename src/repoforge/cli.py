"""Stable, credential-free command-line entry point."""

import json
from pathlib import Path

import typer

from repoforge import __version__
from repoforge.assembly import AssemblyPipeline, PipelineError
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


pipeline_app = typer.Typer(
    name="pipeline",
    help="Run the five-stage, approval-gated project assembly workflow.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(pipeline_app, name="pipeline")


def _load_pipeline(state_file: Path) -> AssemblyPipeline:
    try:
        return AssemblyPipeline(state_file)
    except (OSError, ValueError, PipelineError) as exc:
        typer.echo(f"Pipeline error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@pipeline_app.command("init")
def pipeline_init(
    project_name: str = typer.Option(..., "--project-name"),
    description: str = typer.Option(..., "--description"),
    target_environment: str = typer.Option(..., "--target-environment"),
    stack_requirements: str = typer.Option(..., "--stack"),
    edge_cases: str = typer.Option(..., "--edge-cases"),
    state_file: Path = typer.Option(Path(".repoforge/assembly.json"), "--state-file"),
) -> None:
    try:
        pipeline = AssemblyPipeline.create(
            state_file,
            project_name,
            description,
            target_environment,
            stack_requirements,
            edge_cases,
        )
    except (OSError, ValueError) as exc:
        typer.echo(f"Pipeline initialization failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Assembly initialized: {pipeline.state['run_id']}")
    typer.echo(f"State file: {state_file}")


@pipeline_app.command("prompt")
def pipeline_prompt(
    state_file: Path = typer.Option(Path(".repoforge/assembly.json"), "--state-file"),
) -> None:
    pipeline = _load_pipeline(state_file)
    try:
        typer.echo(pipeline.prompt_for_current_stage())
    except PipelineError as exc:
        typer.echo(f"Pipeline error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@pipeline_app.command("submit")
def pipeline_submit(
    artifact_file: Path = typer.Option(
        ...,
        "--artifact-file",
        exists=True,
        file_okay=True,
        readable=True,
    ),
    state_file: Path = typer.Option(Path(".repoforge/assembly.json"), "--state-file"),
) -> None:
    pipeline = _load_pipeline(state_file)
    try:
        artifact = artifact_file.read_text(encoding="utf-8")
        stage = pipeline.submit_output(artifact)
    except (OSError, ValueError, PipelineError) as exc:
        typer.echo(f"Submission failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Stage submitted for human approval: {stage}")


@pipeline_app.command("approve")
def pipeline_approve(
    note: str = typer.Option("", "--note"),
    state_file: Path = typer.Option(Path(".repoforge/assembly.json"), "--state-file"),
) -> None:
    pipeline = _load_pipeline(state_file)
    try:
        stage = pipeline.approve_current(note)
    except PipelineError as exc:
        typer.echo(f"Approval failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    next_stage = pipeline.current_stage()
    typer.echo(f"Approved: {stage}")
    typer.echo(f"Next stage: {next_stage or 'all stages approved'}")


@pipeline_app.command("reject")
def pipeline_reject(
    feedback: str = typer.Option(..., "--feedback"),
    state_file: Path = typer.Option(Path(".repoforge/assembly.json"), "--state-file"),
) -> None:
    pipeline = _load_pipeline(state_file)
    try:
        stage = pipeline.reject_current(feedback)
    except (ValueError, PipelineError) as exc:
        typer.echo(f"Rejection failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Stage rejected and unlocked for revision: {stage}")


@pipeline_app.command("status")
def pipeline_status(
    state_file: Path = typer.Option(Path(".repoforge/assembly.json"), "--state-file"),
) -> None:
    pipeline = _load_pipeline(state_file)
    typer.echo(json.dumps(pipeline.status(), indent=2))
