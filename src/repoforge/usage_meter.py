"""Safe usage and budget snapshots for hosted model evaluation."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def openrouter_key_snapshot(api_key: str) -> dict:
    """Fetch aggregate key limits without retaining the credential or raw payload."""
    if not api_key:
        return {"status": "missing_credential"}
    request = Request(
        "https://openrouter.ai/api/v1/key",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            return {"status": "malformed_response"}
        data = payload.get("data")
        if not isinstance(data, dict):
            return {"status": "malformed_response"}

        limit = data.get("limit")
        remaining = data.get("limit_remaining")
        numeric_limit = isinstance(limit, (int, float)) and not isinstance(limit, bool)
        numeric_remaining = isinstance(remaining, (int, float)) and not isinstance(remaining, bool)
        if (limit is not None and not numeric_limit) or (
            remaining is not None and not numeric_remaining
        ):
            return {"status": "invalid_quota_metadata"}

        status = "available"
        if numeric_remaining and remaining <= 0:
            status = "limit_exhausted"
        elif numeric_limit and limit > 0 and numeric_remaining:
            if remaining / limit <= 0.1:
                status = "near_limit"
        return {
            "status": status,
            "limit": limit,
            "limit_remaining": remaining,
            "limit_reset": data.get("limit_reset"),
            "usage": data.get("usage"),
            "usage_daily": data.get("usage_daily"),
            "usage_monthly": data.get("usage_monthly"),
            "expires_at": data.get("expires_at"),
        }
    except HTTPError as exc:
        return {"status": "http_error", "http_status": exc.code}
    except (URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"status": "unavailable", "error_type": type(exc).__name__}
