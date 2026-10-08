"""
RepoForge CLI – Main command interface.
"""

import typer
from typing import Optional
import os

app = typer.Typer(
    help="🔥 RepoForge Engine – Autonomous AI Software Engineering Platform"
)


# ============================================================================
# Existing Commands (unchanged except version and forge)
# ============================================================================

@app.command()
def hello():
    """Check RepoForge status."""
    typer.echo("🚀 RepoForge Engine is alive!")


@app.command()
def doctor():
    """Run system diagnostics."""
    from repoforge.commands.doctor import run_doctor
    run_doctor()


@app.command()
def chat(
    prompt: str,
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Choose AI model."),
):
    """Chat with AI models."""
    from repoforge.commands.chat import run_chat
    run_chat(prompt, model)


@app.command()
def providers():
    """List AI providers."""
    from repoforge.commands.providers import run_providers
    run_providers()


@app.command()
def models():
    """List AI models."""
    from repoforge.commands.models import run_models
    run_models()


@app.command()
def use(provider: str):
    """Select active provider."""
    from repoforge.commands.use import run_use
    run_use(provider)


@app.command()
def version():
    """Show RepoForge version."""
    typer.echo("RepoForge Engine V5.0.0 – Multi‑Agent Autonomous Engineering")


@app.command()
def scan(path: str = typer.Argument(".", help="Project path")):
    """Scan repository."""
    from repoforge.commands.scan import run_scan
    run_scan(path)



@app.command()
def audit(
    path: str = typer.Argument(".", help="Repository path to audit"),
):
    """RepoForge Audit — architecture, security, quality, improvement plan (read-only)."""
    from repoforge.audit import RepoAuditor, print_audit

    typer.echo("")
    typer.echo("📋 Running RepoForge Audit (read-only)...")
    auditor = RepoAuditor(path)
    report = auditor.run()
    print_audit(report)
    out = auditor.save(report)
    typer.echo(f"💾 Report saved: {out}")
    typer.echo("")


# ============================================================================
# UPDATED `forge` – with `--approve` flag
# ============================================================================

@app.command()
def forge(
    path: str = typer.Argument(".", help="Repository path"),
    prompt: str = typer.Argument("Fix prioritized audit issues", help="Improvement instruction"),
    approve: bool = typer.Option(False, "--approve", "-a", help="Request approval before applying changes"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Analyze and plan only – do not write files"),
    fix: bool = typer.Option(False, "--fix", "-f", help="Use audit issues as the plan, then apply safe fixes"),
):
    """Engineering mode: analyze and improve a repository. Use --fix after audit."""
    from repoforge.workflow_engine import WorkflowEngine
    from repoforge.display import Display

    typer.echo("")
    typer.echo("=" * 60)
    typer.echo("🔥 RepoForge Engine – Single Repository Run")
    typer.echo("=" * 60)
    typer.echo(f"📂 Repository: {path}")
    typer.echo(f"🎯 Task: {prompt}")
    if dry_run:
        typer.echo("🧪 Mode: DRY-RUN (no files will be written)")
    if fix:
        typer.echo("🔧 Mode: FIX (audit issues → planned safe changes)")

    engine = WorkflowEngine(path)
    result = engine.execute(prompt, dry_run=dry_run, fix_mode=fix)

    # Display results
    Display.forge_result(result)

    # If approval requested, show the selected action and ask for confirmation
    if approve:
        v5 = result.get("stages", {}).get("v5_agents", {})
        if v5 and v5.get("enabled", False):
            selected = v5.get("selected_improvement")
            if selected:
                desc = selected.get("description", "unknown action")
                typer.echo("\n📌 Proposed Action:")
                typer.echo(f"   {desc}")
                if typer.confirm("Apply this action?", default=True):
                    typer.echo("✅ Action confirmed.")
                else:
                    typer.echo("❌ Action rejected. No changes made.")
            else:
                typer.echo("\nℹ️  No action selected by agents. Nothing to approve.")
        else:
            typer.echo("\nℹ️  Agents disabled – no action to approve.")


# ============================================================================
# NEW MULTI‑REPO COMMANDS
# ============================================================================

@app.command()
def multi(
    prompt: str = typer.Argument("Improve repository", help="Improvement instruction"),
    manifest: Optional[str] = typer.Option(None, "--manifest", "-m", help="Path to a text file with repo paths (one per line)"),
    approve: bool = typer.Option(False, "--approve", "-a", help="Request approval before applying changes on each repo"),
):
    """Run RepoForge on multiple repositories."""
    from repoforge.projects.project_manager import ProjectManager
    from repoforge.display import Display

    pm = ProjectManager()

    if manifest:
        if not os.path.exists(manifest):
            typer.echo(f"❌ Manifest file not found: {manifest}")
            raise typer.Exit(1)
        with open(manifest) as f:
            paths = [line.strip() for line in f if line.strip()]
        for p in paths:
            pm.add_project(p)

    projects = pm.list_projects()
    if not projects:
        typer.echo("❌ No projects registered. Use `add-project` or provide a manifest.")
        raise typer.Exit(1)

    # Show dashboard
    Display.multi_repo_table(projects)

    if not typer.confirm("\nContinue with these projects?", default=True):
        typer.echo("Aborted.")
        raise typer.Exit()

    typer.echo("\n🔨 Running RepoForge on all projects...")
    results = pm.run_all(prompt, approve=approve)

    # Show updated dashboard
    typer.echo("\n📊 Final Multi‑Repo Report:")
    Display.multi_repo_table([r["project"] for r in results])
    typer.echo("✅ Multi‑repo run complete.")


@app.command()
def add_project(
    path: str = typer.Argument(..., help="Repository path"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Custom project name (default: folder name)"),
):
    """Add a project to the multi‑repo registry."""
    from repoforge.projects.project_manager import ProjectManager
    pm = ProjectManager()
    project = pm.add_project(path, name)
    typer.echo(f"✅ Added project: {project['name']} ({project['path']})")


@app.command()
def remove_project(
    path: str = typer.Argument(..., help="Repository path"),
):
    """Remove a project from the registry."""
    from repoforge.projects.project_manager import ProjectManager
    pm = ProjectManager()
    if pm.remove_project(path):
        typer.echo(f"✅ Removed project: {path}")
    else:
        typer.echo(f"❌ Project not found: {path}")


@app.command()
def list_projects():
    """List all registered projects with health scores."""
    from repoforge.projects.project_manager import ProjectManager
    from repoforge.display import Display
    pm = ProjectManager()
    projects = pm.list_projects()
    if not projects:
        typer.echo("No projects registered.")
    else:
        Display.multi_repo_table(projects)


# ============================================================================
# Existing `fix` command (unchanged)
# ============================================================================

@app.command()
def fix(
    path: str = typer.Argument(".", help="Repository path"),
    file: str = typer.Option(..., "--file", "-f", help="File to modify"),
    issue: str = typer.Option(..., "--issue", "-i", help="Problem to fix"),
):
    """Apply AI generated fix safely (V3 Patch Engine)."""
    from repoforge.patch_engine import PatchEngine

    typer.echo("")
    typer.echo("=" * 60)
    typer.echo("🔨 RepoForge Engine – Patch Engine")
    typer.echo("=" * 60)
    typer.echo(f"📂 Repository: {path}")
    typer.echo(f"📄 File: {file}")
    typer.echo(f"🐛 Issue: {issue}")

    engine = PatchEngine(path)
    result = engine.apply_fix(file, issue)

    typer.echo("")
    if result.get("success", False):
        typer.echo("✅ Fix applied successfully")
        typer.echo(result.get("message", ""))
        if result.get("backup"):
            typer.echo(f"💾 Backup: {result['backup']}")
    else:
        typer.echo("❌ Fix failed")
        typer.echo(result.get("message", ""))


# ============================================================================
# Main entry point
# ============================================================================

if __name__ == "__main__":
    app()