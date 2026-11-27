"""Write a safe per-model result and OpenRouter key-budget snapshot."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from repoforge.usage_meter import openrouter_key_snapshot


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

    key_status = openrouter_key_snapshot(os.getenv("OPENROUTER_API_KEY", "").strip())
    model_rows = []
    for result in results_payload.get("results", []):
        cases = result.get("cases", [])
        limit_errors = [
            case
            for case in cases
            if "RateLimit" in str(case.get("detail", ""))
            or "quota" in str(case.get("detail", "")).lower()
            or "HTTP 402" in str(case.get("detail", ""))
            or "HTTP 429" in str(case.get("detail", ""))
        ]
        model_rows.append(
            {
                "provider": result.get("provider"),
                "model": result.get("model"),
                "evaluation_status": result.get("status", "not_run"),
                "passed": result.get("passed", 0),
                "failed": result.get("failed", 0),
                "errors": result.get("errors", 0),
                "average_latency_ms": result.get("average_latency_ms"),
                "limit_hit_detected": bool(limit_errors),
                "limit_error_cases": [case.get("case_id") for case in limit_errors],
            }
        )

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
    print(
        json.dumps(
            {
                "key_budget_status": key_status.get("status"),
                "limit_remaining": key_status.get("limit_remaining"),
                "models_reported": len(model_rows),
                "output": str(args.output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
