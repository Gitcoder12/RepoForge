from pathlib import Path

import pytest
from typer.testing import CliRunner

from repoforge.cli import app
from repoforge.assembly import (
    ApprovalRequired,
    AssemblyPipeline,
    PipelineError,
    STAGES,
)


def make_pipeline(tmp_path: Path) -> AssemblyPipeline:
    return AssemblyPipeline.create(
        tmp_path / "assembly.json",
        project_name="Example",
        description="A small service with a real API",
        target_environment="Docker on AWS",
        stack_requirements="Python 3.12, FastAPI, PostgreSQL",
        edge_cases="Concurrent requests, provider timeouts, malformed input",
    )


def test_pipeline_requires_human_approval_before_advancing(tmp_path: Path) -> None:
    pipeline = make_pipeline(tmp_path)
    assert pipeline.current_stage() == "blueprint"
    prompt = pipeline.prompt_for_current_stage()
    assert "Do not write implementation code" in prompt
    assert "Current stage: BLUEPRINT" in prompt

    pipeline.submit_output("Approved architecture proposal")
    with pytest.raises(ApprovalRequired):
        pipeline.prompt_for_current_stage()

    with pytest.raises(ApprovalRequired):
        pipeline.submit_output("replacement")

    pipeline.approve_current("Architecture reviewed")
    assert pipeline.current_stage() == "foundation"
    assert "Approved architecture proposal" in pipeline.prompt_for_current_stage()


def test_pipeline_rejects_stage_and_includes_feedback(tmp_path: Path) -> None:
    pipeline = make_pipeline(tmp_path)
    pipeline.submit_output("Incomplete architecture")
    pipeline.reject_current("Add explicit data flows and failure modes")

    prompt = pipeline.prompt_for_current_stage()
    assert "Add explicit data flows and failure modes" in prompt
    assert "complete revised stage deliverable" in prompt

    pipeline.submit_output("Revised architecture")
    assert pipeline.status()["stages"]["blueprint"]["attempts"] == 2


def test_pipeline_persists_state_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "assembly.json"
    pipeline = AssemblyPipeline.create(
        path,
        "Example",
        "A service",
        "Local Docker",
        "Python",
        "Timeouts",
    )
    pipeline.submit_output("Architecture")
    pipeline.approve_current()

    restored = AssemblyPipeline(path)
    assert restored.current_stage() == "foundation"
    assert restored.status()["stages"]["blueprint"]["status"] == "approved"


def test_pipeline_requires_all_prior_stages_to_be_approved(tmp_path: Path) -> None:
    pipeline = make_pipeline(tmp_path)
    for stage in STAGES[:4]:
        assert pipeline.current_stage() == stage
        pipeline.submit_output(f"{stage} artifact")
        pipeline.approve_current()

    assert pipeline.current_stage() == "deployment"
    assert len(STAGES) == 5


def test_pipeline_rejects_empty_brief_and_artifacts(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="description"):
        AssemblyPipeline.create(
            tmp_path / "bad.json",
            "Example",
            " ",
            "Docker",
            "Python",
            "timeouts",
        )
    pipeline = make_pipeline(tmp_path)
    with pytest.raises(ValueError, match="must not be empty"):
        pipeline.submit_output(" ")


def test_pipeline_rejects_unapproved_or_missing_stage_progress(tmp_path: Path) -> None:
    pipeline = make_pipeline(tmp_path)
    pipeline.state["stages"]["blueprint"]["status"] = "awaiting_approval"
    pipeline.state["stages"]["blueprint"]["artifact"] = "architecture"
    pipeline._save()
    with pytest.raises(ApprovalRequired, match="awaiting human approval"):
        pipeline.prompt_for_current_stage()
    with pytest.raises(ApprovalRequired, match="awaiting human approval"):
        pipeline.submit_output("replacement")
    pipeline.approve_current()
    assert pipeline.current_stage() == "foundation"




def test_pipeline_cli_initializes_and_reports_state(tmp_path: Path) -> None:
    state_file = tmp_path / "assembly.json"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "pipeline",
            "init",
            "--project-name",
            "Example",
            "--description",
            "A small API service",
            "--target-environment",
            "Docker",
            "--stack",
            "Python and FastAPI",
            "--edge-cases",
            "Timeouts and malformed requests",
            "--state-file",
            str(state_file),
        ],
    )

    assert result.exit_code == 0
    assert state_file.is_file()

    prompt = runner.invoke(app, ["pipeline", "prompt", "--state-file", str(state_file)])
    assert prompt.exit_code == 0
    assert "Current stage: BLUEPRINT" in prompt.stdout

    status = runner.invoke(app, ["pipeline", "status", "--state-file", str(state_file)])
    assert status.exit_code == 0
    assert '"blueprint"' in status.stdout


def test_pipeline_rejects_corrupted_out_of_order_state(tmp_path: Path) -> None:
    pipeline = make_pipeline(tmp_path)
    pipeline.state["stages"]["foundation"]["status"] = "approved"
    pipeline.state["stages"]["foundation"]["artifact"] = "Foundation without blueprint"
    with pytest.raises(PipelineError, match="cannot progress before blueprint"):
        pipeline._save()
