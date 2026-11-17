"""Tests for the installable package's real provider runtime."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from repoforge.providers.compatible import OpenAICompatibleProvider
from repoforge.providers.errors import (
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from repoforge.providers.factory import ProviderFactory


class FakeCompletions:
    def __init__(self, content: str | None = "real model response", error: Exception | None = None):
        self.content = content
        self.error = error
        self.request: dict | None = None

    def create(self, **kwargs):
        self.request = kwargs
        if self.error is not None:
            raise self.error
        if self.content is None:
            return SimpleNamespace(choices=[])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


def test_deepseek_requires_a_real_key_and_never_returns_mock_output(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(ProviderConfigurationError, match="DEEPSEEK_API_KEY"):
        ProviderFactory().get("deepseek")


def test_provider_status_never_exposes_secret_values(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-test-value")
    status = ProviderFactory().list_status()
    deepseek = next(item for item in status if item["name"] == "deepseek")

    assert deepseek["configured"] is True
    assert "secret-test-value" not in repr(status)
    assert deepseek["credential_variable"] == "DEEPSEEK_API_KEY"


def test_factory_builds_deepseek_with_explicit_endpoint_and_zero_retries(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    completions = FakeCompletions()
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    options: dict = {}

    class FakeOpenAI:
        def __new__(cls, **kwargs):
            options.update(kwargs)
            return fake_client

    sdk = ModuleType("openai")
    sdk.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", sdk)

    provider = ProviderFactory().get("deepseek")
    result = provider.generate(
        "Inspect this function",
        system_prompt="You are a careful code reviewer.",
        max_tokens=512,
    )

    assert result == "real model response"
    assert provider.name == "deepseek"
    assert provider.models == ["deepseek-flash"]
    assert options["base_url"] == "https://api.deepseek.com"
    assert options["max_retries"] == 0
    assert completions.request["model"] == "deepseek-flash"
    assert completions.request["max_tokens"] == 512
    assert completions.request["messages"][0]["role"] == "system"


def test_quota_exhaustion_is_reported_without_provider_switch():
    class RateLimitError(Exception):
        pass

    completions = FakeCompletions(error=RateLimitError("sensitive SDK error body"))
    provider = OpenAICompatibleProvider(
        provider_name="deepseek",
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-flash",
        client=SimpleNamespace(chat=SimpleNamespace(completions=completions)),
    )

    with pytest.raises(ProviderRateLimitError, match="No automatic provider switch"):
        provider.generate("Review this patch")


def test_timeout_is_converted_to_a_clear_provider_error():
    class APITimeoutError(Exception):
        pass

    provider = OpenAICompatibleProvider(
        provider_name="deepseek",
        api_key="test-key",
        model="deepseek-flash",
        client=SimpleNamespace(
            chat=SimpleNamespace(
                completions=FakeCompletions(error=APITimeoutError())
            )
        ),
    )

    with pytest.raises(ProviderTimeoutError, match="45 seconds"):
        provider.generate("Review this patch")


def test_empty_provider_response_is_not_reported_as_success():
    provider = OpenAICompatibleProvider(
        provider_name="deepseek",
        api_key="test-key",
        model="deepseek-flash",
        client=SimpleNamespace(
            chat=SimpleNamespace(completions=FakeCompletions(content=None))
        ),
    )

    with pytest.raises(ProviderResponseError, match="no completion choices"):
        provider.generate("Review this patch")


def test_generate_cli_does_not_fall_back_when_deepseek_is_unconfigured(monkeypatch):
    from typer.testing import CliRunner

    from repoforge.cli import app

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    result = CliRunner().invoke(
        app,
        ["generate", "Review this patch", "--provider", "deepseek"],
    )

    assert result.exit_code == 2
    assert "DEEPSEEK_API_KEY" in result.output
    assert "mock response" not in result.output.lower()



def test_groq_uses_a_current_production_model_id(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    definition = ProviderFactory().list_status()
    groq = next(item for item in definition if item["name"] == "groq")

    assert groq["configured"] is True
    assert ProviderFactory().get("groq").models == ["openai/gpt-oss-120b"]
