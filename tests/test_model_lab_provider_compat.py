"""Provider parameter compatibility tests for currently recommended targets."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from repoforge.providers.compatible import OpenAICompatibleProvider


class CaptureCompletions:
    def __init__(self) -> None:
        self.request: dict | None = None

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )


@pytest.mark.parametrize(
    "model",
    ["gpt-6.2-astra", "gpt-6.2-sol", "openai/gpt-6.2-astra"],
)
def test_gpt_62_omits_unsupported_temperature(model: str):
    completions = CaptureCompletions()
    provider = OpenAICompatibleProvider(
        provider_name="openai",
        api_key="test-key",
        model=model,
        client=SimpleNamespace(chat=SimpleNamespace(completions=completions)),
    )

    assert provider.generate("Return ok", temperature=0.0) == "ok"
    assert completions.request is not None
    assert "temperature" not in completions.request


def test_non_gpt_62_models_keep_temperature_parameter():
    completions = CaptureCompletions()
    provider = OpenAICompatibleProvider(
        provider_name="deepseek",
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-flash",
        client=SimpleNamespace(chat=SimpleNamespace(completions=completions)),
    )

    assert provider.generate("Return ok", temperature=0.0) == "ok"
    assert completions.request is not None
    assert completions.request["temperature"] == 0.0
