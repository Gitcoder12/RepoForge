"""Strict adapter for TruthStream claim-verification results.

TruthStream provides factual context, never proof of a repository mutation or tool call.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any
from urllib.parse import urlsplit


@dataclass(frozen=True)
class TruthstreamAssessment:
    claim: str
    status: str
    confidence: float
    provenance_status: str
    distinct_source_host_count: int
    usable_as_context: bool
    limitations: tuple[str, ...]


def assess_truthstream_result(
    payload: dict[str, Any], *, min_source_hosts: int = 2
) -> TruthstreamAssessment:
    if (
        isinstance(min_source_hosts, bool)
        or not isinstance(min_source_hosts, int)
        or min_source_hosts < 1
    ):
        raise ValueError("min_source_hosts must be a positive integer")
    if not isinstance(payload, dict):
        raise ValueError("TruthStream assessment must be an object")
    claim_obj = payload.get("claim")
    claim = claim_obj.get("text", "") if isinstance(claim_obj, dict) else ""
    status = payload.get("status", "unknown")
    confidence = payload.get("confidence_score", 0.0)
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not isfinite(confidence)
        or not 0 <= confidence <= 1
    ):
        raise ValueError("confidence_score must be a finite number between 0 and 1")

    evidence_items: list[Any] = []
    all_complete = True
    for key in ("supporting_evidence", "contradicting_evidence", "neutral_evidence"):
        group = payload.get(key, [])
        if not isinstance(group, list):
            all_complete = False
            continue
        evidence_items.extend(group)

    verified_hosts: set[str] = set()
    seen_ids: set[str] = set()
    all_complete = all_complete and bool(evidence_items)
    for item in evidence_items:
        if not isinstance(item, dict):
            all_complete = False
            continue
        source = item.get("source")
        url = source.get("url") if isinstance(source, dict) else None
        evidence_id = item.get("evidence_id")
        retrieved_at = item.get("retrieved_at")
        try:
            parsed_url = urlsplit(url) if isinstance(url, str) else None
            host = parsed_url.hostname if parsed_url else None
            _ = parsed_url.port if parsed_url else None
            timestamp = (
                datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
                if isinstance(retrieved_at, str)
                else None
            )
        except ValueError:
            host = None
            timestamp = None
            parsed_url = None
        valid_timestamp = (
            timestamp is not None
            and timestamp.tzinfo is not None
            and timestamp.utcoffset() is not None
        )
        valid_id = (
            isinstance(evidence_id, str)
            and bool(evidence_id.strip())
            and evidence_id not in seen_ids
        )
        if (
            parsed_url is None
            or parsed_url.scheme != "https"
            or not host
            or parsed_url.username is not None
            or parsed_url.password is not None
            or not valid_id
            or not valid_timestamp
        ):
            all_complete = False
        else:
            seen_ids.add(evidence_id)
            verified_hosts.add(host.lower())

    provenance = payload.get("provenance")
    declared_source_backed = (
        isinstance(provenance, dict) and provenance.get("status") == "source_backed"
    )
    host_count = len(verified_hosts)
    usable = (
        isinstance(claim, str)
        and bool(claim.strip())
        and isinstance(status, str)
        and bool(status.strip())
        and all_complete
        and declared_source_backed
        and host_count >= min_source_hosts
    )
    limitations = (
        ()
        if usable
        else (
            "TruthStream result is not accepted as source-backed context.",
            "Demo, incomplete, or single-host results must not drive decisions.",
        )
    )
    return TruthstreamAssessment(
        claim=claim,
        status=status if isinstance(status, str) else "unknown",
        confidence=float(confidence),
        provenance_status="source_backed" if usable else "unverified",
        distinct_source_host_count=host_count,
        usable_as_context=usable,
        limitations=limitations,
    )
