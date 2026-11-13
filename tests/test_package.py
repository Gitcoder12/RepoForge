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
