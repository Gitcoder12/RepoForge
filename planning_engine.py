from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ExecutionStep:
    name: str
    priority: int
    reason: str
    dependencies: List[str] = field(default_factory=list)


class PlanningEngine:
    """
    Converts repository analysis into an ordered execution plan.
    """

    def create_plan(
        self,
        scan: Dict[str, Any],
        intelligence: Dict[str, Any],
        issues: List[Dict[str, Any]],
        priorities: List[Dict[str, Any]],
        improvements: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        plan = {
            "summary": self._summary(scan, issues),
            "goals": self._goals(improvements),
            "execution_order": self._execution(priorities, improvements),
            "risks": self._risks(issues),
            "dependencies": self._dependencies(improvements),
            "estimated_difficulty": self._difficulty(issues),
            "confidence": self._confidence(
                scan,
                intelligence,
                issues,
            ),
        }

        return plan

    def _summary(self, scan, issues):

        stats = scan.get("statistics", {})

        return (
            f"Repository contains "
            f"{stats.get('files',0)} files, "
            f"{stats.get('lines',0)} lines, "
            f"with {len(issues)} detected issues."
        )

    def _goals(self, improvements):

        goals = []

        for item in improvements:
            title = item.get("title") or item.get("name")
            if title:
                goals.append(title)

        return goals

    def _execution(self, priorities, improvements):

        order = []

        improvement_lookup = {
            i.get("id"): i for i in improvements
        }

        for priority in priorities:

            improvement = improvement_lookup.get(priority.get("id"))

            if improvement is None:
                continue

            order.append(
                ExecutionStep(
                    name=improvement.get("title", "Unnamed"),
                    priority=priority.get("priority", 999),
                    reason=priority.get("reason", ""),
                    dependencies=improvement.get(
                        "dependencies",
                        [],
                    ),
                )
            )

        order.sort(key=lambda x: x.priority)

        return [
            {
                "name": step.name,
                "priority": step.priority,
                "reason": step.reason,
                "dependencies": step.dependencies,
            }
            for step in order
        ]

    def _dependencies(self, improvements):

        deps = {}

        for item in improvements:
            deps[item.get("title", "Unnamed")] = item.get(
                "dependencies",
                [],
            )

        return deps

    def _risks(self, issues):

        risks = []

        for issue in issues:
            severity = issue.get("severity", "low")

            if severity.lower() in {
                "critical",
                "high",
            }:
                risks.append(issue)

        return risks

    def _difficulty(self, issues):

        critical = sum(
            1
            for i in issues
            if i.get("severity") == "critical"
        )

        high = sum(
            1
            for i in issues
            if i.get("severity") == "high"
        )

        score = critical * 3 + high * 2 + len(issues)

        if score < 10:
            return "Easy"

        if score < 30:
            return "Medium"

        return "Hard"

    def _confidence(
        self,
        scan,
        intelligence,
        issues,
    ):

        confidence = 1.0

        if not scan:
            confidence -= 0.30

        if not intelligence:
            confidence -= 0.25

        confidence -= min(
            len(issues) * 0.01,
            0.25,
        )

        return round(max(confidence, 0.0), 2)