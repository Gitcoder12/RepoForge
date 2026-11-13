"""Evidence-constrained research workflow."""

from __future__ import annotations

import json
import re
from typing import Any

from repoforge.agents.base import RoleAgent
from repoforge.base import BaseProvider


def _parse_audit(payload: str) -> dict[str, Any]:
    candidate = payload.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^\`\`\`(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*\`\`\`$", "", candidate)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return {
            "status": "FAIL",
            "unsupported_claims": [f"Invalid audit JSON: {exc.msg}"],
            "invalid_citations": [],
        }
    if not isinstance(parsed, dict):
        return {"status": "FAIL", "unsupported_claims": ["Audit must be a JSON object"]}
    status = str(parsed.get("status", "FAIL")).upper()
    if status not in {"PASS", "FAIL"}:
        status = "FAIL"
    for key in ("unsupported_claims", "invalid_citations"):
        values = parsed.get(key)
        if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
            parsed[key] = [f"{key} must be a list of strings"]
            status = "FAIL"
        else:
            parsed[key] = values
    if status == "PASS" and (parsed["unsupported_claims"] or parsed["invalid_citations"]):
        status = "FAIL"
    parsed["status"] = status
    return parsed


class ResearchSuperAgent:
    def __init__(
        self,
        extractor_provider: BaseProvider,
        synthesizer_provider: BaseProvider | None = None,
        auditor_provider: BaseProvider | None = None,
        formatter_provider: BaseProvider | None = None,
    ) -> None:
        self.extractor = RoleAgent(
            "Evidence Extractor",
            "You are a rigorous research evidence extractor. Use only the supplied source "
            "material. Extract research questions, methods, datasets, results, limitations, and "
            "verbatim citation metadata. Attach source_id to every extracted claim. Mark missing "
            "information as unavailable; never fill gaps from memory.",
            extractor_provider,
        )
        self.synthesizer = RoleAgent(
            "Research Synthesizer",
            "You are a critical academic researcher. Synthesize only the supplied extracted "
            "evidence. Distinguish source findings from interpretation, preserve disagreements, "
            "and attach source identifiers to factual claims. Never invent authors, titles, "
            "venues, dates, DOIs, datasets, or results.",
            synthesizer_provider or extractor_provider,
        )
        self.auditor = RoleAgent(
            "Citation Auditor",
            "You are an independent evidence and citation auditor. Check every factual claim "
            "against the supplied source records and ensure every cited source_id exists. "
            "Return only JSON with status (PASS or FAIL), unsupported_claims (array), and "
            "invalid_citations (array). Do not approve claims that are not supported.",
            auditor_provider or extractor_provider,
        )
        self.formatter = RoleAgent(
            "LaTeX Formatter",
            "You are a LaTeX formatter. Convert the audited draft into a complete LaTeX "
            "document. Preserve all citation keys and wording. Do not add facts, citations, "
            "bibliography entries, or claims. Return raw LaTeX only.",
            formatter_provider or extractor_provider,
        )

    def generate_paper(
        self,
        sources: list[dict[str, str]],
        topic: str,
    ) -> dict[str, Any]:
        if not topic.strip():
            raise ValueError("Research topic must not be empty")
        if not sources:
            raise ValueError("At least one source record is required")
        normalized: list[dict[str, str]] = []
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                raise ValueError(f"Source at index {index} must be an object")
            source_id = source.get("source_id")
            text = source.get("text")
            citation = source.get("citation")
            if not all(isinstance(value, str) for value in (source_id, text, citation)):
                raise ValueError(
                    f"Source at index {index} requires string source_id, text, and citation"
                )
            source_id = source_id.strip()
            text = text.strip()
            citation = citation.strip()
            if not source_id or not text or not citation:
                raise ValueError(
                    f"Source at index {index} requires source_id, text, and citation"
                )
            normalized.append(
                {
                    "source_id": source_id,
                    "text": text,
                    "citation": citation,
                }
            )

        source_ids = {source["source_id"] for source in normalized}
        if len(source_ids) != len(normalized):
            raise ValueError("Source identifiers must be unique")

        source_context = {"topic": topic, "sources": normalized}
        extracted = self.extractor.run(
            "Extract evidence relevant to this research topic: " + topic,
            source_context,
        )
        draft = self.synthesizer.run(
            "Write a critical literature review draft for: " + topic,
            {"sources": normalized, "extracted_evidence": extracted},
        )
        raw_audit = self.auditor.run(
            "Audit the draft against the source records. Return the required JSON only.",
            {"sources": normalized, "source_ids": sorted(source_ids), "draft": draft},
        )
        audit = _parse_audit(raw_audit)
        latex = None
        if audit["status"] == "PASS":
            latex = self.formatter.run(
                "Format this audited research draft as a complete LaTeX document.",
                {"draft": draft, "sources": normalized},
            )

        return {
            "topic": topic,
            "extracted_evidence": extracted,
            "draft": draft,
            "citation_audit": audit,
            "citation_audit_passed": audit["status"] == "PASS",
            "latex": latex,
            "publication_verified": False,
            "limitations": [
                "The workflow only evaluates the source records supplied by the caller.",
                "Citation audit is model-assisted and is not an external bibliographic verification.",
                "Human review and reproducible evidence checks are required before submission.",
            ],
        }
