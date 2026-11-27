""""Resilience tests for OpenRouter budget snapshots; no live network or credentials."""

from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError, URLError

from repoforge import usage_meter


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_key_snapshot_flags_near_limit_at_ten_percent(monkeypatch):
    monkeypatch.setattr(
        usage_meter,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse({"data": {"limit": 5, "limit_remaining": 0.5}}),
    )
    result = usage_meter.openrouter_key_snapshot("test-secret")
    assert result["status"] == "near_limit"
    assert result["limit_remaining"] == 0.5


def test_key_snapshot_flags_http_429_without_exposing_response_body(monkeypatch):
    secret = "never-write-this-secret"

    def raise_http_error(*_args, **_kwargs):
        raise HTTPError(
            "https://openrouter.ai/api/v1/key",
            429,
            "rate limited",
            hdrs=None,
            fp=BytesIO(secret.encode("utf-8")),
        )

    monkeypatch.setattr(usage_meter, "urlopen", raise_http_error)
    result = usage_meter.openrouter_key_snapshot(secret)
    assert result == {"status": "http_error", "http_status": 429}
    assert secret not in json.dumps(result)


def test_key_snapshot_reports_network_unavailable(monkeypatch):
    monkeypatch.setattr(
        usage_meter,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("offline")),
    )
    result = usage_meter.openrouter_key_snapshot("test-secret")
    assert result == {"status": "unavailable", "error_type": "URLError"}


def test_key_snapshot_reports_malformed_json_as_unavailable(monkeypatch):
    class InvalidJsonResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"{not-json"

    monkeypatch.setattr(usage_meter, "urlopen", lambda *_args, **_kwargs: InvalidJsonResponse())
    result = usage_meter.openrouter_key_snapshot("test-secret")
    assert result == {"status": "unavailable", "error_type": "JSONDecodeError"}


def test_key_snapshot_rejects_non_object_payload(monkeypatch):
    monkeypatch.setattr(
        usage_meter,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(["unexpected", "list"]),
    )
    result = usage_meter.openrouter_key_snapshot("test-secret")
    assert result == {"status": "malformed_response"}


def test_key_snapshot_rejects_non_object_data(monkeypatch):
    monkeypatch.setattr(
        usage_meter,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse({"data": "unexpected"}),
    )
    result = usage_meter.openrouter_key_snapshot("test-secret")
    assert result == {"status": "malformed_response"}


def test_key_snapshot_marks_unavailable_when_quota_fields_are_invalid(monkeypatch):
    monkeypatch.setattr(
        usage_meter,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(
            {"data": {"limit": "five", "limit_remaining": "unknown"}}
        ),
    )
    result = usage_meter.openrouter_key_snapshot("test-secret")
    assert result == {"status": "invalid_quota_metadata"}
