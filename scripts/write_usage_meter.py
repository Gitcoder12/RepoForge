"""Write a safe per-model result and OpenRouter key-budget snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results_payload = {}
    if args.results.exists():
        try:
            results_payload = json.loads(args.results.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            results_payload = {"report_read_error": True}

    import os

    key_status = openrouter_key_snapshot(os.getenv("OPENROUTER_API_KEY", "").strip())
    model_rows = []
    for result in results_payload.get("results", []):
        cases = result.get("cases", [])
        limit_errors = [
            case for case in cases
            if "RateLimit" in str(case.get("detail", ""))
            or "quota" in str(case.get("detail", "")).lower()
            or "HTTP 402" in str(case.get("detail", ""))
            or "HTTP 429" in str(case.get("detail", ""))
        ]
        model_rows.append({
            "provider": result.get("provider"),
            "model": result.get("model"),
            "evaluation_status": result.get("status", "not_run"),
            "passed": result.get("passed", 0),
            "failed": result.get("failed", 0),
            "errors": result.get("errors", 0),
            "average_latency_ms": result.get("average_latency_ms"),
            "limit_hit_detected": bool(limit_errors),
            "limit_error_cases": [case.get("case_id") for case in limit_errors],
        })

    report = {
        "schema_version": 1,
        "key_provider": "openrouter",
        "key_budget": key_status,
        "models": model_rows,
        "notes": [
            "OpenRouter key metadata is an aggregate key/account budget, not a per-model quota.",
            "Per-model rows show evaluation errors and detectable 402/429 quota events.",
            "Direct-provider quota balances are not inferred from OpenRouter metadata.",
            "No API key, authorization header, or raw provider error body is written to this file.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "key_budget_status": key_status.get("status"),
        "limit_remaining": key_status.get("limit_remaining"),
        "models_reported": len(model_rows),
        "output": str(args.output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
