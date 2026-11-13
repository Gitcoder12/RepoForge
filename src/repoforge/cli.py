"""RepoForge command-line interface."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import typer

from repoforge import __version__
from repoforge.assembly import AssemblyPipeline, PipelineError
from repoforge.providers.factory import create_provider, provider_status
from repoforge.repository import collect_repository_context, resolve_repository
from repoforge.turbo import apply_edit, propose_edit
from repoforge.validator import Validator

DEFAULT_STATE_FILE = Path.home() / ".repoforge" / "assembly.json"

app = typer.Typer(
    name="repoforge",
    help="Multi-model repository engineering with explicit human approval.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def version() -> None:
    """Print the installed RepoForge version."""
    typer.echo(f"RepoForge {__version__}")


@app.command()
def models() -> None:
    """Show supported providers and whether their environment is configured."""
    for item in provider_status():
        state = "configured" if item["configured"] else "not configured"
        typer.echo(f"{item['provider']}: {state} | model: {item['model']}")


@app.command()
def inspect(
    repository: str = typer.Argument(..., help="Local path, GitHub URL, or owner/repo."),
    cache_dir: Path | None = typer.Option(None, "--cache-dir"),
) -> None:
    """Resolve a repository and show a bounded, secret-filtered context summary."""
    try:
        target = resolve_repository(repository, cache_dir=cache_dir)
        context = collect_repository_context(target.path)
    except (OSError, ValueError, RuntimeError) as exc:
        typer.echo(f"Repository intake failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Repository: {context['repository_name']}")
    typer.echo(f"Path: {target.path}")
    typer.echo(f"Source: {'cloned from ' + (target.remote_url or '') if target.cloned else 'local'}")
    typer.echo(f"Files discovered: {context['file_count']}")
    typer.echo(f"Languages: {', '.join(context['languages']) or 'not detected'}")
    typer.echo(f"Context files included: {len(context['files'])}")
    for relative in context["files"]:
        typer.echo(f"  - {relative}")


@app.command()
def forge(
    repository: str = typer.Argument(..., help="Local path, GitHub URL, or owner/repo."),
    task: str = typer.Argument(..., help="Engineering task to plan and implement."),
    architect_provider: str = typer.Option("openrouter", "--architect-provider"),
    architect_model: str | None = typer.Option(None, "--architect-model"),
    coder_provider: str = typer.Option("openrouter", "--coder-provider"),
    coder_model: str | None = typer.Option(None, "--coder-model"),
    reviewer_provider: str = typer.Option("openrouter", "--reviewer-provider"),
    reviewer_model: str | None = typer.Option(None, "--reviewer-model"),
    cache_dir: Path | None = typer.Option(None, "--cache-dir"),
    max_revisions: int = typer.Option(1, "--max-revisions", min=0, max=5),
) -> None:
    """Run architect/coder/reviewer agents and save a proposal without editing files."""
    from repoforge.agents.coding import CodingSuperAgent

    try:
        target = resolve_repository(repository, cache_dir=cache_dir)
        context = collect_repository_context(target.path)
        architect = create_provider(architect_provider, model=architect_model)
        coder = create_provider(coder_provider, model=coder_model)
        reviewer = create_provider(reviewer_provider, model=reviewer_model)
        result = CodingSuperAgent(
            architect_provider=architect,
            coder_provider=coder,
            reviewer_provider=reviewer,
        ).build_feature(task, context=context, max_revisions=max_revisions)
    except Exception as exc:
        typer.echo(f"Forge failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    proposal_dir = Path.home() / ".repoforge" / "proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    proposal_path = proposal_dir / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{run_id}.json"
    artifact = {
        "schema_version": 1,
        "run_id": run_id,
        "repository": str(target.path),
        "remote_url": target.remote_url,
        "task": task,
        "providers": {
            "architect": {"name": architect.name, "models": architect.models},
            "coder": {"name": coder.name, "models": coder.models},
            "reviewer": {"name": reviewer.name, "models": reviewer.models},
        },
        "result": result,
        "execution_verified": False,
        "applied": False,
    }
    proposal_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    typer.echo(f"Repository: {target.path}")
    typer.echo(f"Review passed: {result['review_passed']}")
    typer.echo("Execution verified: no (this command generates a proposal only)")
    typer.echo(f"Proposal: {proposal_path}")
    typer.echo("No repository files were changed.")


@app.command()
def turbo(
    repository: str = typer.Argument(..., help="Local path, GitHub URL, or owner/repo."),
    file_path: str = typer.Argument(..., help="Repository-relative path to an existing file."),
    instruction: str = typer.Argument(..., help="Requested change."),
    provider_name: str = typer.Option("openrouter", "--provider"),
    model: str | None = typer.Option(None, "--model"),
    cache_dir: Path | None = typer.Option(None, "--cache-dir"),
) -> None:
    """Propose a single-file edit, show a diff, and apply only after confirmation."""
    try:
        target = resolve_repository(repository, cache_dir=cache_dir)
        provider = create_provider(provider_name, model=model)
        proposal = propose_edit(target.path, file_path, instruction, provider)
    except Exception as exc:
        typer.echo(f"Turbo failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not proposal.diff:
        typer.echo("No changes proposed.")
        return
    typer.echo(proposal.diff)
    approval = typer.prompt("Apply this edit? Type 'yes' to continue", default="no")
    if approval.strip().lower() != "yes":
        typer.echo("Proposal rejected. No repository files were changed.")
        return
    try:
        backup = apply_edit(proposal)
    except (OSError, RuntimeError, ValueError) as exc:
        typer.echo(f"Apply failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Updated: {proposal.path}")
    typer.echo(f"Backup: {backup}")
    typer.echo("No commit, push, or pull request was created.")


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
    state_file: Path = typer.Option(DEFAULT_STATE_FILE, "--state-file"),
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
    state_file: Path = typer.Option(DEFAULT_STATE_FILE, "--state-file"),
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
    state_file: Path = typer.Option(DEFAULT_STATE_FILE, "--state-file"),
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
    state_file: Path = typer.Option(DEFAULT_STATE_FILE, "--state-file"),
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
    state_file: Path = typer.Option(DEFAULT_STATE_FILE, "--state-file"),
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
    state_file: Path = typer.Option(DEFAULT_STATE_FILE, "--state-file"),
) -> None:
    pipeline = _load_pipeline(state_file)
    typer.echo(json.dumps(pipeline.status(), indent=2))
