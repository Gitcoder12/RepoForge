"""Multi-repository inspection, hook orchestration, and selectable action board."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Iterable

from repoforge.blacksmith import Blacksmith
from repoforge.megazord import MegazordEngine
from repoforge.upgrades import UpgradePlanner

Hook = Callable[[dict[str, Any]], None]


class HookChain:
    """Inspect one or more repositories and assemble a human-reviewed action board.

    Hooks are registered by trusted calling applications in-process. The chain
    never imports Python modules, plugins, or hook scripts from target repos.
    """

    MAX_REPOSITORIES = 30

    EVENTS = (
        "chain.started",
        "repository.inspect.started",
        "repository.inspect.completed",
        "repository.langfix.completed",
        "repository.plan.ready",
        "megazords.completed",
        "chain.completed",
    )

    def __init__(self) -> None:
        self._hooks: dict[str, list[Hook]] = {}
        self._repair_payloads: dict[str, tuple[Path, dict[str, Any]]] = {}
        self._event_trace: list[dict[str, Any]] = []

    def register_hook(self, event: str, callback: Hook) -> None:
        """Register a trusted in-process observer for a known lifecycle event."""
        if event not in self.EVENTS:
            raise ValueError(f"unsupported hook event: {event}")
        if not callable(callback):
            raise TypeError("hook callback must be callable")
        self._hooks.setdefault(event, []).append(callback)

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        self._event_trace.append({"event": event, **payload})
        for callback in self._hooks.get(event, []):
            try:
                callback(dict(payload))
            except Exception as exc:  # observer errors never trigger repository writes
                self._event_trace.append(
                    {
                        "event": "hook.error",
                        "hook_event": event,
                        "error_type": type(exc).__name__,
                        "message": str(exc)[:500],
                    }
                )

    @staticmethod
    def _slug(value: str) -> str:
        cleaned = re.sub(r"[^a-z0-9-]+", "-", value.casefold()).strip("-")
        return cleaned or "repository"

    def inspect(
        self,
        repo_paths: Iterable[str | Path],
        *,
        with_langfix: bool = False,
        langfix_timeout: int = 180,
        top_k: int = 15,
    ) -> dict[str, Any]:
        paths = tuple(Path(item).expanduser().resolve() for item in repo_paths)
        if not paths:
            raise ValueError("provide at least one repository path")
        if len(paths) > self.MAX_REPOSITORIES:
            raise ValueError(f"at most {self.MAX_REPOSITORIES} repositories can be inspected")
        if len(set(paths)) != len(paths):
            raise ValueError("duplicate repository paths are not allowed")
        for path in paths:
            if not path.is_dir():
                raise ValueError(f"repository path must be an existing directory: {path}")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")

        self._repair_payloads = {}
        self._event_trace = []
        self._emit("chain.started", {"repository_count": len(paths), "with_langfix": with_langfix})

        reports: list[dict[str, Any]] = []
        selection_items: list[dict[str, Any]] = []
        planner = UpgradePlanner()

        for index, path in enumerate(paths, start=1):
            repo_id = f"r{index}-{self._slug(path.name)}"
            self._emit("repository.inspect.started", {"repository": path.name, "repo_id": repo_id})

            blacksmith = Blacksmith(path)
            snapshot = blacksmith.inspect()
            repairs = blacksmith.repair_plan(snapshot)
            upgrades = planner.build(snapshot)

            self._emit(
                "repository.inspect.completed",
                {
                    "repository": path.name,
                    "repo_id": repo_id,
                    "files_scanned": snapshot["files_scanned"],
                    "rank": snapshot["rank"]["score"],
                },
            )

            repair_rows = []
            for repair in repairs:
                repair_id = f"repair:{repo_id}:{self._slug(repair['path'])}"
                safe = (
                    repair.get("operation") == "create_if_absent"
                    and repair.get("safe_to_apply") is True
                )
                self._repair_payloads[repair_id] = (path, repair)
                row = {
                    "id": repair_id,
                    "kind": "repair",
                    "repository": path.name,
                    "title": f"{repair['operation']}: {repair['path']}",
                    "detail": repair.get("reason", ""),
                    "risk": "low" if safe else "review",
                    "safe_to_apply": safe,
                }
                repair_rows.append({key: value for key, value in row.items() if key != "id"})
                selection_items.append(row)

            upgrade_rows = []
            for option in upgrades["options"]:
                upgrade_id = f"upgrade:{repo_id}:{option['id']}"
                row = {
                    "id": upgrade_id,
                    "kind": "upgrade",
                    "repository": path.name,
                    "title": option["title"],
                    "detail": option["evidence"],
                    "risk": option["risk"],
                    "safe_to_apply": False,
                    "priority_score": option["priority_score"],
                    "verification": option["verification"],
                }
                upgrade_rows.append({key: value for key, value in row.items() if key != "id"})
                selection_items.append(row)

            langfix_result = None
            if with_langfix:
                from repoforge.langfix_bridge import LangFixBridge

                langfix_result = LangFixBridge().scan(path, timeout=langfix_timeout)
                self._emit(
                    "repository.langfix.completed",
                    {
                        "repository": path.name,
                        "repo_id": repo_id,
                        "status": langfix_result["status"],
                        "files_scanned": langfix_result.get("files_scanned", 0),
                    },
                )

            report = {
                "id": repo_id,
                "name": path.name,
                "path": str(path),
                "blacksmith": snapshot,
                "repair_plan": repair_rows,
                "upgrade_options": upgrade_rows,
                "langfix": langfix_result,
            }
            reports.append(report)
            self._emit(
                "repository.plan.ready",
                {
                    "repository": path.name,
                    "repo_id": repo_id,
                    "repair_count": len(repair_rows),
                    "upgrade_count": len(upgrade_rows),
                },
            )

        megazords = None
        if len(paths) >= 2:
            megazords = MegazordEngine().suggest(paths, top_k=top_k)
            for index, suggestion in enumerate(megazords["suggestions"], start=1):
                left, right = suggestion["repositories"]
                complement_id = (
                    f"complement:{index}:{self._slug(left['name'])}:{self._slug(right['name'])}"
                )
                selection_items.append(
                    {
                        "id": complement_id,
                        "kind": "complement",
                        "repository": f"{left['name']} + {right['name']}",
                        "title": (
                            f"{left['name']} + {right['name']} "
                            f"(heuristic fit {suggestion['fit_score']}/100)"
                        ),
                        "detail": "; ".join(
                            item["pattern"] for item in suggestion["integration_blueprint"]
                        ),
                        "risk": "architecture_review",
                        "safe_to_apply": False,
                        "fit_score": suggestion["fit_score"],
                        "shared_languages": suggestion["shared_languages"],
                    }
                )
            self._emit(
                "megazords.completed",
                {
                    "repositories_analyzed": len(paths),
                    "pairings_evaluated": megazords["pairings_evaluated"],
                    "suggestions_returned": len(megazords["suggestions"]),
                },
            )

        report = {
            "engine": "RepoForge HookChain",
            "mode": "inspect_and_select",
            "repositories": reports,
            "megazords": megazords,
            "selection_items": selection_items,
            "hook_trace": list(self._event_trace),
            "safety": {
                "target_code_executed": False,
                "target_dependencies_installed": False,
                "target_files_modified": False,
                "langfix_apply_requested": False,
                "repository_defined_hooks_loaded": False,
                "notes": [
                    "LangFix runs in preview-only mode and its cache is isolated in a temporary directory.",
                    "Only safe create-if-absent repairs can be applied after explicit selection.",
                    "Upgrade options and Megazord complements are recommendations, never executable repairs.",
                    "Target build scripts, test suites, and project hooks are not executed.",
                ],
            },
        }
        self._emit("chain.completed", {"repository_count": len(paths), "selection_count": len(selection_items)})
        report["hook_trace"] = list(self._event_trace)
        return report

    def apply_selected(self, report: dict[str, Any], selected_ids: Iterable[str]) -> dict[str, Any]:
        """Apply only selected create-if-absent repairs; all other items remain plans."""
        if not isinstance(report, dict) or report.get("engine") != "RepoForge HookChain":
            raise ValueError("report was not produced by RepoForge HookChain")
        selected = list(dict.fromkeys(selected_ids))
        known = {item["id"]: item for item in report.get("selection_items", [])}
        unknown = sorted(set(selected) - set(known))
        if unknown:
            raise ValueError(f"unknown selection id(s): {', '.join(unknown)}")

        outcomes = []
        for item_id in selected:
            item = known[item_id]
            if item.get("kind") != "repair" or not item.get("safe_to_apply"):
                outcomes.append(
                    {
                        "id": item_id,
                        "status": "review_only",
                        "reason": "Selected item is a recommendation, not an automatic safe repair.",
                    }
                )
                continue
            payload = self._repair_payloads.get(item_id)
            if payload is None:
                outcomes.append({"id": item_id, "status": "unavailable", "reason": "Repair payload is not present in this chain instance."})
                continue
            path, repair = payload
            applied = Blacksmith(path).apply_repairs([repair])
            status = applied[0]["status"] if applied else "skipped"
            outcomes.append(
                {
                    "id": item_id,
                    "repository": path.name,
                    "path": repair["path"],
                    "status": status,
                }
            )

        return {
            "selected_ids": selected,
            "outcomes": outcomes,
            "applied_count": sum(item["status"] == "created" for item in outcomes),
            "review_only_count": sum(item["status"] == "review_only" for item in outcomes),
        }
