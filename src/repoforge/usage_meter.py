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
        data = payload.get("data", {})
        limit = data.get("limit")
        remaining = data.get("limit_remaining")
        status = "available"
        if isinstance(remaining, (int, float)) and remaining <= 0:
            status = "limit_exhausted"
        elif isinstance(limit, (int, float)) and limit > 0 and isinstance(remaining, (int, float)):
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
