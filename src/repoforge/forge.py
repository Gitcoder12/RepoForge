"""End-to-end, approval-gated repository engineering workflow."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from repoforge.action_runner import ActionRunner
from repoforge.blacksmith import Blacksmith
from repoforge.testing import TestForge
from repoforge.validator import Validator


class ForgeWorkflow:
    """Connect inspection, planning, optional model proposals, and validation.

    The default path is read-only. Applying model-proposed changes requires an
    explicit provider, --apply, exact approved paths, and a clean non-protected
    Git working tree. Target tests remain opt-in and are not sandboxed.
    """

    MAX_ACTIONS = 30
    MAX_FILE_BYTES = 1_000_000
    DENIED_PATH_PARTS = {
        ".git",
        ".env",
        ".ssh",
        ".aws",
        ".venv",
        "venv",
        "node_modules",
        "secrets",
        "credentials",
    }

    @classmethod
    def parse_actions(cls, response: str) -> list[dict[str, str]]:
        """Parse and validate a strict JSON action envelope from a model."""
        if not isinstance(response, str):
            raise ValueError("model response must be text")
        candidate = response.strip()
        candidate = re.sub(r"^\x60{3}(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*\x60{3}$", "", candidate)
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ValueError("model must return a JSON object containing an actions array") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("actions"), list):
            raise ValueError("model response requires an actions array")
        raw_actions = payload["actions"]
        if len(raw_actions) > cls.MAX_ACTIONS:
            raise ValueError(f"model returned more than {cls.MAX_ACTIONS} actions")

        actions: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in raw_actions:
            if not isinstance(item, dict):
                raise ValueError("each action must be a JSON object")
            action_type = item.get("type")
            filepath = item.get("file")
            content = item.get("content")
            if action_type not in {"create", "modify"}:
                raise ValueError("only create and modify actions are supported; delete is disabled")
            if not isinstance(filepath, str) or not filepath.strip():
                raise ValueError("each action requires a non-empty file path")
            normalized = filepath.replace("\\", "/")
            path = PurePosixPath(normalized)
            raw_parts = normalized.split("/")
            if (
                path.is_absolute()
                or any(part in {"", ".", ".."} for part in raw_parts)
            ):
                raise ValueError(f"unsafe repository-relative path: {filepath!r}")
            if ":" in path.parts[0] or normalized.startswith("//"):
                raise ValueError(f"unsafe repository-relative path: {filepath!r}")
            if any(part.casefold() in cls.DENIED_PATH_PARTS for part in path.parts):
                raise ValueError(f"protected or sensitive path denied: {filepath!r}")
            if path.parts[0].casefold() == ".github" and len(path.parts) > 1:
                if path.parts[1].casefold() == "workflows":
                    raise ValueError("workflow-file changes require a separate reviewed process")
            relative = path.as_posix()
            if relative in seen:
                raise ValueError(f"duplicate action path: {relative}")
            seen.add(relative)
            if not isinstance(content, str):
                raise ValueError(f"action content must be text: {relative}")
            if len(content.encode("utf-8")) > cls.MAX_FILE_BYTES:
                raise ValueError(f"action content exceeds 1 MB: {relative}")
            actions.append({"type": action_type, "file": relative, "content": content})
        return actions

    @staticmethod
    def _model_prompt(request: str, snapshot: dict[str, Any], test_plan: dict[str, Any]) -> str:
        context = json.dumps(
            {"repository_snapshot": snapshot, "test_plan": test_plan},
            ensure_ascii=False,
            default=str,
        )[:14_000]
        return (
            "You are RepoForge, a cautious repository engineering agent.\n"
            "Task: " + request + "\n"
            "Repository evidence (truncated if needed):\n" + context + "\n\n"
            "Return ONLY JSON: {\"actions\":[{\"type\":\"create|modify\","
            "\"file\":\"relative/path\",\"content\":\"complete file content\"}]}\n"
            "Rules: no delete actions; no absolute paths or traversal; keep scope minimal; "
            "never include secrets; do not claim tests passed; do not modify generated, "
            "dependency, credential, or deployment files unless the request explicitly "
            "requires them. If no safe change is justified, return an empty actions array."
        )

    def run(
        self,
        repo_path: str | Path,
        request: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        apply: bool = False,
        approved_paths: set[str] | None = None,
        run_tests: bool = False,
        timeout: int = 120,
    ) -> dict[str, Any]:
        root = Path(repo_path).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"repository path is not a directory: {root}")
        if not isinstance(request, str) or not request.strip():
            raise ValueError("request must be non-empty")
        if apply and not provider:
            raise ValueError("--apply requires an explicitly selected --provider")
        if run_tests and not apply:
            raise ValueError("--run-tests is only available after an approved apply run")

        snapshot = Blacksmith(root).inspect()
        test_plan = TestForge(root).plan()
        validation = asyncio.run(Validator(root).validate())
        report: dict[str, Any] = {
            "engine": "RepoForge Forge",
            "repository": str(root),
            "request": request,
            "status": "inspected",
            "inspection": snapshot,
            "test_plan": test_plan,
            "preflight_validation": validation,
            "actions": [],
            "mutation": {"status": "not_requested"},
            "post_validation": None,
            "test_execution": {"status": "not_requested"},
            "safety": {
                "default_read_only": True,
                "delete_actions_enabled": False,
                "apply_requires_exact_path_approval": True,
                "target_tests_are_sandboxed": False,
            },
        }

        if provider is None:
            report["status"] = "plan_only"
            report["next_step"] = (
                "Choose an explicit model provider (for example --provider ollama) "
                "to generate a bounded patch proposal."
            )
            return report

        from repoforge.orchestrator import AIOrchestrator

        orchestrator = AIOrchestrator()
        orchestrator.register_real_provider(provider, model=model)
        response = orchestrator.generate(
            self._model_prompt(request, snapshot, test_plan),
            provider=provider.strip().lower(),
            max_tokens=8192,
        )
        actions = self.parse_actions(response)
        report["actions"] = actions
        if not actions:
            report["status"] = "no_changes_proposed"
            report["mutation"] = {"status": "no_actions"}
            return report

        runner = ActionRunner(root)
        if apply:
            report["mutation"] = runner.run(
                actions,
                dry_run=False,
                approved_paths=approved_paths or set(),
                allow_delete=False,
            )
        else:
            report["mutation"] = runner.run(actions, dry_run=True)

        if report["mutation"].get("status") != "completed":
            report["status"] = "blocked"
            return report

        if not apply:
            report["status"] = "previewed"
            return report

        report["post_validation"] = asyncio.run(Validator(root).validate())
        if not report["post_validation"].get("passed"):
            report["status"] = "applied_validation_failed"
            return report

        if run_tests:
            report["test_execution"] = TestForge(root).run(execute=True, timeout=timeout)
            if report["test_execution"].get("status") != "passed":
                report["status"] = "applied_tests_failed"
                return report
        else:
            report["test_execution"] = {
                "status": "skipped",
                "reason": "Pass --run-tests only for a repository whose code you trust.",
            }
        report["status"] = "applied_and_validated"
        return report
