"""Tests for the OpenRouter usage meter without network or credentials."""

from __future__ import annotations

import json

from scripts import write_usage_meter


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_key_snapshot_reports_remaining_budget(monkeypatch):
    monkeypatch.setattr(
        write_usage_meter,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(
            {"data": {"limit": 5, "limit_remaining": 4.25, "limit_reset": "monthly", "usage": 0.75}}
        ),
    )
    result = write_usage_meter.openrouter_key_snapshot("not-a-real-key")
    assert result["status"] == "available"
    assert result["limit_remaining"] == 4.25
    assert "not-a-real-key" not in json.dumps(result)


def test_key_snapshot_flags_exhausted_budget(monkeypatch):
    monkeypatch.setattr(
        write_usage_meter,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse({"data": {"limit": 5, "limit_remaining": 0}}),
    )
    assert write_usage_meter.openrouter_key_snapshot("test")["status"] == "limit_exhausted"


def test_key_snapshot_does_not_claim_provider_quota_without_key():
    assert write_usage_meter.openrouter_key_snapshot("") == {"status": "missing_credential"}
