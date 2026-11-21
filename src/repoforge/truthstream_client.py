"""Small, bounded HTTP client for the TruthStream /verify API."""

from __future__ import annotations

import json
from math import isfinite
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from repoforge.truthstream_bridge import TruthstreamAssessment, assess_truthstream_result


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


class TruthstreamClient:
    def __init__(
        self,
        endpoint: str,
        *,
        timeout: float = 5.0,
        max_response_bytes: int = 1_000_000,
    ) -> None:
        if not isinstance(endpoint, str) or not endpoint.strip():
            raise ValueError("endpoint must be a non-empty URL")
        try:
            parsed = urlparse(endpoint)
            hostname = parsed.hostname
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("endpoint URL is malformed") from exc
        local_http = parsed.scheme == "http" and hostname in {
            "localhost",
            "127.0.0.1",
            "::1",
        }
        if parsed.scheme != "https" and not local_http:
            raise ValueError(
                "TruthStream endpoint must use HTTPS (HTTP is allowed only on loopback)"
            )
        if (
            not parsed.netloc
            or not hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "endpoint must be absolute, have a host, and contain no credentials or query"
            )
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout must be a positive finite number")
        if (
            isinstance(max_response_bytes, bool)
            or not isinstance(max_response_bytes, int)
            or max_response_bytes < 1
        ):
            raise ValueError("response limit must be a positive integer")
        self.endpoint = endpoint.rstrip("/") + "/verify"
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes
        self._opener = build_opener(_NoRedirect())

    def verify(self, text: str) -> tuple[TruthstreamAssessment, ...]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("claim text must not be empty")
        request = Request(
            self.endpoint,
            data=json.dumps({"text": text}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with self._opener.open(request, timeout=self.timeout) as response:
            raw = response.read(self.max_response_bytes + 1)
        if len(raw) > self.max_response_bytes:
            raise ValueError("TruthStream response exceeded configured size limit")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, list):
            raise ValueError("TruthStream /verify response must be a JSON array")
        if any(not isinstance(item, dict) for item in payload):
            raise ValueError("TruthStream response items must all be objects")
        assessments = [assess_truthstream_result(item) for item in payload]
        return tuple(assessments)
