"""Architect, implementation, and review workflow for coding tasks."""

from __future__ import annotations

import json
import re
from typing import Any

from repoforge.agents.base import RoleAgent
from repoforge.base import BaseProvider


def _parse_review(payload: str) -> dict[str, Any]:
    candidate = payload.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^\`\`\`(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*\`\`\`$", "", candidate)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return {
            "status": "FAIL",
            "findings": [f"Reviewer returned invalid JSON: {exc.msg}"],
            "raw_response": payload,
        }
    if not isinstance(parsed, dict):
        return {"status": "FAIL", "findings": ["Review must be a JSON object"]}
    status = str(parsed.get("status", "FAIL")).upper()
    if status not in {"PASS", "FAIL"}:
        status = "FAIL"
    findings = parsed.get("findings")
    if not isinstance(findings, list) or any(not isinstance(item, str) for item in findings):
        findings = ["Reviewer findings must be a list of strings"]
        status = "FAIL"
    if status == "PASS" and findings:
        status = "FAIL"
    required_tests = parsed.get("required_tests")
    if not isinstance(required_tests, list) or any(
        not isinstance(item, str) for item in required_tests
    ):
        required_tests = ["Reviewer required_tests must be a list of strings"]
        status = "FAIL"
    parsed["required_tests"] = required_tests
    parsed["status"] = status
    parsed["findings"] = findings
    return parsed


class CodingSuperAgent:
    def __init__(
        self,
        architect_provider: BaseProvider,
        coder_provider: BaseProvider | None = None,
        reviewer_provider: BaseProvider | None = None,
    ) -> None:
        self.architect = RoleAgent(
            "Architect",
            "Act as a principal software architect. Inspect the task and supplied context, "
            "identify constraints, edge cases, interfaces, risks, and a minimal implementation "
            "plan. Do not invent repository files or claim checks have run.",
            architect_provider,
        )
        self.coder = RoleAgent(
            "Coder",
            "Act as a senior software engineer. Implement the approved plan completely. "
            "Preserve existing interfaces and conventions. Include input validation and error "
            "handling. Do not invent test results, dependencies, files, or execution evidence.",
            coder_provider or architect_provider,
        )
        self.reviewer = RoleAgent(
            "Reviewer",
            "Act as an independent, adversarial code reviewer. Find correctness defects, "
            "security problems, missing edge cases, compatibility risks, and test gaps. "
            "Return only a JSON object with status (PASS or FAIL), findings (array of strings), "
            "and required_tests (array of strings). PASS means the submitted code review has "
            "no blocking findings; it does not mean code was executed or tests passed.",
            reviewer_provider or architect_provider,
        )

    def build_feature(
        self,
        task_description: str,
        context: dict[str, Any] | None = None,
        max_revisions: int = 2,
    ) -> dict[str, Any]:
        if not task_description.strip():
            raise ValueError("Task description must not be empty")
        if not 0 <= max_revisions <= 5:
            raise ValueError("max_revisions must be between 0 and 5")

        plan = self.architect.run(
            "Create a precise implementation plan for this task: " + task_description,
            context,
        )
        code = self.coder.run(
            "Implement the task from the architecture plan. Return complete code or a "
            "file-by-file patch proposal.\nTask: " + task_description,
            {"plan": plan, "repository_context": context or {}},
        )
        review: dict[str, Any] = {"status": "FAIL", "findings": ["Review not run"]}
        attempts = 0

        for attempts in range(1, max_revisions + 2):
            raw_review = self.reviewer.run(
                "Review this implementation against the task and plan. Return the required "
                "JSON schema only.\nTask: " + task_description,
                {"plan": plan, "implementation": code, "repository_context": context or {}},
            )
            review = _parse_review(raw_review)
            if review["status"] == "PASS":
                break
            if attempts <= max_revisions:
                code = self.coder.run(
                    "Revise the implementation to address every blocking review finding. "
                    "Return the complete revised implementation.",
                    {"plan": plan, "previous_implementation": code, "review": review},
                )

        return {
            "task": task_description,
            "plan": plan,
            "code": code,
            "review": review,
            "review_passed": review["status"] == "PASS",
            "review_attempts": attempts,
            "execution_verified": False,
            "verification_required": [
                "Apply the proposed change",
                "Run the repository test suite",
                "Inspect the final diff",
            ],
        }
