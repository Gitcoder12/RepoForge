import asyncio
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
    assert "providers" in result.stdout
    assert "generate" in result.stdout
    assert "blacksmith" in result.stdout
    assert "megazords" in result.stdout


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
        "test_run": {"status": "failed"},
    }
    with patch(
        "repoforge.cli.Validator.validate",
        new=AsyncMock(return_value=result_data),
    ):
        result = CliRunner().invoke(app, ["validate", str(tmp_path)])

    assert result.exit_code == 1
    assert "src/example.py: syntax error" in result.output
    assert "1 failed" in result.output


def test_validator_does_not_execute_target_tests_by_default(tmp_path, monkeypatch) -> None:
    from repoforge.validator import Validator

    (tmp_path / "safe.py").write_text("VALUE = 1\n", encoding="utf-8")
    create_process = AsyncMock(side_effect=AssertionError("pytest must not run by default"))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)

    result = asyncio.run(Validator(str(tmp_path)).validate())

    assert result["passed"] is True
    assert result["test_run"]["status"] == "skipped"
    create_process.assert_not_awaited()


def test_validator_executes_target_tests_only_after_opt_in(tmp_path, monkeypatch) -> None:
    from repoforge.validator import Validator

    (tmp_path / "safe.py").write_text("VALUE = 1\n", encoding="utf-8")

    class FakeProcess:
        returncode = 0

        async def communicate(self):
            return b"2 passed", b""

    create_process = AsyncMock(return_value=FakeProcess())
    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)

    result = asyncio.run(Validator(str(tmp_path)).validate(run_tests=True))

    assert result["passed"] is True
    assert result["test_run"]["status"] == "passed"
    create_process.assert_awaited_once()
    assert create_process.await_args.args[:3] == ("pytest", "--tb=short", "-q")


def test_validator_rejects_invalid_target_and_timeout(tmp_path) -> None:
    import pytest

    from repoforge.validator import Validator

    validator = Validator(str(tmp_path))
    (tmp_path / "note.txt").write_text("not python", encoding="utf-8")

    invalid_target = asyncio.run(validator.validate(target_files=["note.txt"]))
    assert invalid_target["passed"] is False
    assert invalid_target["reason"] == "invalid_paths"

    with pytest.raises(ValueError, match="test_timeout"):
        asyncio.run(validator.validate(test_timeout=0))


def test_orchestrator_registers_and_enables_explicit_real_provider():
    orchestrator = AIOrchestrator()
    provider = MockProvider("adapter result")

    with patch("repoforge.providers.factory.ProviderFactory.get", return_value=provider) as build:
        registered = orchestrator.register_real_provider(
            "DeepSeek",
            model="deepseek-flash",
            timeout=30.0,
        )

    build.assert_called_once_with(
        "deepseek",
        model="deepseek-flash",
        timeout=30.0,
    )
    assert registered is provider
    assert orchestrator.providers["deepseek"] is provider
    assert "deepseek" in orchestrator.pm.enabled
    assert orchestrator.generate("hello", provider="deepseek") == "adapter result"


def test_orchestrator_rejects_duplicate_real_provider_registration():
    import pytest

    orchestrator = AIOrchestrator()
    orchestrator.register("deepseek", MockProvider("existing"))

    with pytest.raises(ValueError, match="already registered"):
        orchestrator.register_real_provider("deepseek")


def test_generate_cli_uses_the_orchestrator_for_explicit_provider():
    with (
        patch("repoforge.orchestrator.AIOrchestrator.register_real_provider") as register,
        patch(
            "repoforge.orchestrator.AIOrchestrator.generate",
            return_value="integrated provider response",
        ) as generate,
    ):
        result = CliRunner().invoke(
            app,
            [
                "generate",
                "review this patch",
                "--provider",
                "deepseek",
                "--model",
                "deepseek-flash",
                "--timeout",
                "20",
                "--max-tokens",
                "1024",
            ],
        )

    assert result.exit_code == 0
    assert result.stdout.strip() == "integrated provider response"
    register.assert_called_once_with("deepseek", model="deepseek-flash", timeout=20.0)
    generate.assert_called_once_with(
        "review this patch",
        provider="deepseek",
        max_tokens=1024,
    )

def test_validate_cli_only_reports_failed_files_and_shows_threats(tmp_path) -> None:
    threat_message = "REVIEW: Potentially destructive operation 'subprocess.run()' at line 4"
    result_data = {
        "passed": False,
        "reason": "validation_failed",
        "results": [
            {"file": "safe.py", "passed": True},
            {
                "file": "review.py",
                "passed": False,
                "threats": [threat_message],
            },
            {"file": "broken.py", "passed": False, "error": "line 2: invalid syntax"},
        ],
        "invalid_paths": [{"file": "escape.py", "error": "path escapes repository root"}],
        "test_run": {"status": "not_started"},
    }
    with patch(
        "repoforge.cli.Validator.validate",
        new=AsyncMock(return_value=result_data),
    ):
        result = CliRunner().invoke(app, ["validate", str(tmp_path)])

    assert result.exit_code == 1
    assert "safe.py" not in result.output
    assert "review.py: REVIEW: Potentially destructive operation" in result.output
    assert "broken.py: line 2: invalid syntax" in result.output
    assert "escape.py: path escapes repository root" in result.output
