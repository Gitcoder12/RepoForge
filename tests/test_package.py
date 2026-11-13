from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from repoforge import __version__
from repoforge.cli import app
from repoforge.orchestrator import AIOrchestrator
from repoforge.providers.mock import MockProvider


def test_package_version_and_cli_help() -> None:
    assert __version__ == "0.6.0"
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "validate" in result.stdout
    assert "version" in result.stdout


def test_offline_provider_orchestration() -> None:
    orchestrator = AIOrchestrator()
    provider = MockProvider("offline result")
    orchestrator.register("mock", provider)
    orchestrator.pm.enable("mock")

    assert orchestrator.generate("hello") == "offline result"
    assert provider.calls[0]["prompt"] == "hello"


def test_crucible_uses_the_same_provider_contract_and_redacts_secrets() -> None:
    from repoforge.security.crucible import Crucible

    wrapped = MockProvider("safe response")
    guarded = Crucible(wrapped)
    result = guarded.generate("token sk-abcdefghijklmnopqrstuvwxyz0123456789 is present")

    assert result == "safe response"
    assert wrapped.calls[0]["prompt"] == ("token [REDACTED_BY_CRUCIBLE] is present")


def test_crucible_blocks_dangerous_provider_output() -> None:
    from repoforge.security.crucible import Crucible

    guarded = Crucible(MockProvider("rm -rf /"))
    assert guarded.generate("write a harmless summary").startswith("ERROR: Response blocked")


def test_validator_rejects_symlink_escape(tmp_path) -> None:
    import asyncio

    from repoforge.validator import Validator

    repository = tmp_path / "repository"
    repository.mkdir()
    outside_file = tmp_path / "outside.py"
    outside_file.write_text("print('outside')\n", encoding="utf-8")
    (repository / "escape.py").symlink_to(outside_file)

    result = asyncio.run(Validator(str(repository)).validate())

    assert result["passed"] is False
    assert result["reason"] == "invalid_paths"
    assert result["invalid_paths"][0]["file"] == "escape.py"



def test_orchestrator_requires_explicit_choice_when_multiple_providers_are_enabled() -> None:
    import pytest

    orchestrator = AIOrchestrator()
    orchestrator.register("first", MockProvider("first result"))
    orchestrator.register("second", MockProvider("second result"))
    orchestrator.pm.enable("first")
    orchestrator.pm.enable("second")

    with pytest.raises(ValueError, match="Specify a provider"):
        orchestrator.generate("hello")

    assert orchestrator.generate("hello", provider="second") == "second result"


def test_validator_rejects_self_referential_python_symlink(tmp_path) -> None:
    import asyncio

    from repoforge.validator import Validator

    repository = tmp_path / "repository"
    repository.mkdir()
    loop = repository / "loop.py"
    loop.symlink_to(loop)

    result = asyncio.run(Validator(str(repository)).validate())

    assert result["passed"] is False
    assert result["reason"] == "invalid_paths"
    assert result["invalid_paths"][0]["file"] == "loop.py"



def test_cli_shows_validation_diagnostics(tmp_path) -> None:
    result_data = {
        "passed": False,
        "reason": "pytest_failed",
        "results": [{"file": "src/example.py", "error": "syntax error"}],
        "invalid_paths": [],
        "output": "1 failed",
    }
    with patch(
        "repoforge.cli.Validator.validate",
        new=AsyncMock(return_value=result_data),
    ):
        result = CliRunner().invoke(app, ["validate", str(tmp_path)])

    assert result.exit_code == 1
    assert "src/example.py: syntax error" in result.output
    assert "1 failed" in result.output
