from __future__ import annotations

import csv
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List


@dataclass
class TaskMetric:
    name: str
    duration: float
    success: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ModelMetric:
    model: str
    tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    latency: float = 0.0
    calls: int = 0


@dataclass
class SessionMetric:
    started_at: datetime = field(default_factory=datetime.utcnow)
    tasks: List[TaskMetric] = field(default_factory=list)
    models: Dict[str, ModelMetric] = field(default_factory=dict)
    errors: int = 0

class MetricsCollector:
    """
    Production metrics collector for RepoForge.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.session = SessionMetric()

    def record_task(
        self,
        name: str,
        duration: float,
        success: bool = True,
    ):
        with self._lock:
            self.session.tasks.append(
                TaskMetric(
                    name=name,
                    duration=duration,
                    success=success,
                )
            )

            if not success:
                self.session.errors += 1

    def record_model(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        latency: float = 0.0,
    ):
        with self._lock:
            metric = self.session.models.setdefault(
                model,
                ModelMetric(model=model),
            )

            metric.calls += 1
            metric.input_tokens += input_tokens
            metric.output_tokens += output_tokens
            metric.tokens += input_tokens + output_tokens
            metric.cost += cost
            metric.latency += latency

    def record_error(self):
        with self._lock:
            self.session.errors += 1

    def summary(self) -> dict:
        with self._lock:
            total_tasks = len(self.session.tasks)
            successful = sum(
                1 for t in self.session.tasks if t.success
            )

            total_duration = sum(
                t.duration for t in self.session.tasks
            )

            total_tokens = sum(
                m.tokens for m in self.session.models.values()
            )

            total_cost = sum(
                m.cost for m in self.session.models.values()
            )

            total_calls = sum(
                m.calls for m in self.session.models.values()
            )

            avg_latency = (
                sum(m.latency for m in self.session.models.values())
                / total_calls
                if total_calls
                else 0.0
            )

            return {
                "started_at": self.session.started_at.isoformat(),
                "tasks": total_tasks,
                "successful": successful,
                "failed": self.session.errors,
                "success_rate": (
                    successful / total_tasks * 100
                    if total_tasks
                    else 0.0
                ),
                "duration": total_duration,
                "tokens": total_tokens,
                "cost": total_cost,
                "calls": total_calls,
                "avg_latency": avg_latency,
                "models": len(self.session.models),
            }

    def pretty_report(self) -> str:
        s = self.summary()

        return (
            "\n"
            "========== RepoForge Metrics ==========\n"
            f"Tasks          : {s['tasks']}\n"
            f"Success Rate   : {s['success_rate']:.2f}%\n"
            f"Failures       : {s['failed']}\n"
            f"Duration       : {s['duration']:.2f}s\n"
            f"Tokens         : {s['tokens']}\n"
            f"Cost           : £{s['cost']:.4f}\n"
            f"LLM Calls      : {s['calls']}\n"
            f"Avg Latency    : {s['avg_latency']:.2f}s\n"
            f"Models Used    : {s['models']}\n"
            "=======================================\n"
        )

    def export_json(self, path: str | Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                self.summary(),
                f,
                indent=4,
            )

    def export_csv(self, path: str | Path):
        with open(
            path,
            "w",
            newline="",
            encoding="utf-8",
        ) as f:

            writer = csv.writer(f)

            writer.writerow(
                [
                    "Model",
                    "Calls",
                    "Tokens",
                    "Input",
                    "Output",
                    "Cost",
                    "Latency",
                ]
            )

            for model in self.session.models.values():
                writer.writerow(
                    [
                        model.model,
                        model.calls,
                        model.tokens,
                        model.input_tokens,
                        model.output_tokens,
                        model.cost,
                        model.latency,
                    ]
                )

    def save(
        self,
        directory: str | Path = "metrics",
    ):
        directory = Path(directory)
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.export_json(directory / "metrics.json")
        self.export_csv(directory / "metrics.csv")


metrics = MetricsCollector()