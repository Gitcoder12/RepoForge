"""Tests for explicit, classified model-provider standby routing."""

from __future__ import annotations

import pytest

from repoforge.providers.errors import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderTimeoutError,
)
from repoforge.providers.failover import (
    ProviderFailoverExhaustedError,
    StandbyProviderPool,
)
from repoforge.providers.mock import MockProvider


class ResultProvider(MockProvider):
    def __init__(self, result: str = "ok", error: Exception | None = None):
        super().__init__(response=result)
        self.error = error

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "kwargs": kwargs})
        if self.error is not None:
            raise self.error
        return self.response


def test_primary_is_used_without_calling_standby():
    primary = ResultProvider("primary response")
    standby = ResultProvider("standby response")
    pool = StandbyProviderPool(
        primary_name="primary",
        providers={"primary": primary, "standby": standby},
        standby_names=("standby",),
    )

    result = pool.generate_with_report("hello")

    assert result.text == "primary response"
    assert result.provider_name == "primary"
    assert result.used_standby is False
    assert len(primary.calls) == 1
    assert standby.calls == []


@pytest.mark.parametrize(
    "error",
    [
        ProviderConnectionError("offline"),
        ProviderTimeoutError("slow"),
    ],
)
def test_transient_primary_failure_uses_explicit_standby(error):
    primary = ResultProvider(error=error)
    standby = ResultProvider("backup response")
    pool = StandbyProviderPool(
        primary_name="primary",
        providers={"primary": primary, "standby": standby},
        standby_names=("standby",),
    )

    result = pool.generate_with_report("hello")

    assert result.text == "backup response"
    assert result.provider_name == "standby"
    assert result.used_standby is True
    assert [item.status for item in result.attempts] == ["failed", "success"]
    assert result.attempts[0].error_type == type(error).__name__


def test_authentication_failure_does_not_trigger_standby():
    primary = ResultProvider(error=ProviderAuthenticationError("bad key"))
    standby = ResultProvider("must not be called")
    pool = StandbyProviderPool(
        primary_name="primary",
        providers={"primary": primary, "standby": standby},
        standby_names=("standby",),
    )

    with pytest.raises(ProviderAuthenticationError):
        pool.generate("hello")
    assert standby.calls == []


def test_request_error_does_not_trigger_standby():
    primary = ResultProvider(error=ProviderRequestError("bad request"))
    standby = ResultProvider("must not be called")
    pool = StandbyProviderPool(
        primary_name="primary",
        providers={"primary": primary, "standby": standby},
        standby_names=("standby",),
    )

    with pytest.raises(ProviderRequestError):
        pool.generate("hello")
    assert standby.calls == []


def test_rate_limit_does_not_switch_without_explicit_permission():
    primary = ResultProvider(error=ProviderRateLimitError("quota"))
    standby = ResultProvider("must not be called")
    pool = StandbyProviderPool(
        primary_name="primary",
        providers={"primary": primary, "standby": standby},
        standby_names=("standby",),
    )

    with pytest.raises(ProviderRateLimitError):
        pool.generate("hello")
    assert standby.calls == []


def test_rate_limit_can_switch_when_explicitly_enabled():
    primary = ResultProvider(error=ProviderRateLimitError("quota"))
    standby = ResultProvider("paid backup")
    pool = StandbyProviderPool(
        primary_name="primary",
        providers={"primary": primary, "standby": standby},
        standby_names=("standby",),
        allow_rate_limit_fallback=True,
    )

    assert pool.generate("hello") == "paid backup"
    assert len(standby.calls) == 1


def test_all_retryable_candidates_exhaust_with_an_audit_summary():
    primary = ResultProvider(error=ProviderConnectionError("offline"))
    standby = ResultProvider(error=ProviderTimeoutError("slow"))
    pool = StandbyProviderPool(
        primary_name="primary",
        providers={"primary": primary, "standby": standby},
        standby_names=("standby",),
    )

    with pytest.raises(ProviderFailoverExhaustedError) as error:
        pool.generate("hello")

    assert [item.provider_name for item in error.value.attempts] == ["primary", "standby"]
    assert all(item.status == "failed" for item in error.value.attempts)
    assert "offline" not in str(error.value)


def test_pool_rejects_duplicate_or_unregistered_routes():
    provider = ResultProvider()

    with pytest.raises(ValueError, match="duplicates"):
        StandbyProviderPool(
            primary_name="primary",
            providers={"primary": provider},
            standby_names=("primary",),
        )

    with pytest.raises(ValueError, match="unregistered"):
        StandbyProviderPool(
            primary_name="primary",
            providers={"primary": provider},
            standby_names=("missing",),
        )


def test_pool_never_uses_an_implicit_mock():
    primary = ResultProvider(error=ProviderConnectionError("offline"))
    pool = StandbyProviderPool(primary_name="primary", providers={"primary": primary})

    with pytest.raises(ProviderFailoverExhaustedError):
        pool.generate("hello")



def test_generate_cli_loads_an_explicit_route_config(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    from typer.testing import CliRunner

    from repoforge.cli import app
    from repoforge.providers.failover import StandbyProviderPool

    config = tmp_path / "route.json"
    config.write_text(
        json.dumps(
            {
                "primary": {"provider": "deepseek", "model_override": "deepseek-flash"},
                "standby": [
                    {"provider": "openai", "model_override": None, "enabled": True},
                    {"provider": "ollama", "model_override": None, "enabled": False},
                ],
                "policy": {"fallback_on_rate_limit": False},
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    class FakeRoute:
        def generate_with_report(self, prompt, **kwargs):
            captured["prompt"] = prompt
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                text="standby success",
                attempts=(
                    SimpleNamespace(
                        provider_name="openai",
                        model="gpt-4o-mini",
                        status="success",
                        error_type=None,
                    ),
                ),
            )

    def fake_from_factory(cls, **kwargs):
        captured.update(kwargs)
        return FakeRoute()

    monkeypatch.setattr(
        StandbyProviderPool, "from_factory", classmethod(fake_from_factory)
    )
    result = CliRunner().invoke(
        app,
        ["generate", "test prompt", "--route-config", str(config)],
    )

    assert result.exit_code == 0, result.output
    assert "standby success" in result.output
    assert captured["primary_name"] == "deepseek"
    assert captured["standby_names"] == ("openai",)
    assert captured["model_overrides"]["deepseek"] == "deepseek-flash"
    assert captured["allow_rate_limit_fallback"] is False
