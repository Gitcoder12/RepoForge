"""Thread-safe task progress stream with deterministic snapshots."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StreamEvent(str, Enum):
    START = "start"
    UPDATE = "update"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class StreamTask:
    name: str
    status: TaskStatus = TaskStatus.PENDING
    model: str | None = None
    provider: str | None = None
    started: float | None = None
    finished: float | None = None
    message: str = ""
    response: str | None = None
    error: str | None = None

    def duration(self) -> float:
        if self.started is None:
            return 0.0
        return max(0.0, (self.finished or time.perf_counter()) - self.started)


class StreamManager:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.tasks: dict[str, StreamTask] = {}
        self.callbacks: list[Callable[[StreamEvent, StreamTask], None]] = []
        self.lock = threading.RLock()
        self.started = time.perf_counter()
        self.finished: float | None = None

    def add_task(self, name: str, model: str | None = None, provider: str | None = None) -> StreamTask:
        with self.lock:
            if name in self.tasks:
                raise ValueError(f"Task {name!r} already exists")
            task = StreamTask(name=name, model=model, provider=provider)
            self.tasks[name] = task
            return task

    def _transition(self, name: str, status: TaskStatus, message: str = "", response: str | None = None, error: str | None = None) -> StreamTask:
        with self.lock:
            if name not in self.tasks:
                raise ValueError(f"Task {name!r} does not exist")
            task = self.tasks[name]
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                raise ValueError(f"Task {name!r} is already terminal")
            now = time.perf_counter()
            if status == TaskStatus.RUNNING and task.started is None:
                task.started = now
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                task.finished = now
            task.status = status
            task.message = message
            task.response = response
            task.error = error
        event = {
            TaskStatus.RUNNING: StreamEvent.START,
            TaskStatus.COMPLETED: StreamEvent.COMPLETE,
            TaskStatus.FAILED: StreamEvent.ERROR,
            TaskStatus.PENDING: StreamEvent.UPDATE,
        }[status]
        self.emit(event, task)
        return task

    def start_task(self, name: str, message: str = "") -> StreamTask:
        return self._transition(name, TaskStatus.RUNNING, message)

    def update_task(self, name: str, message: str) -> None:
        with self.lock:
            if name not in self.tasks:
                raise ValueError(f"Task {name!r} does not exist")
            task = self.tasks[name]
            if task.status != TaskStatus.RUNNING:
                raise ValueError("Only running tasks can be updated")
            task.message = message
        self.emit(StreamEvent.UPDATE, task)

    def complete_task(self, name: str, response: str = "") -> None:
        self._transition(name, TaskStatus.COMPLETED, response, response=response)

    def fail_task(self, name: str, error: str) -> None:
        self._transition(name, TaskStatus.FAILED, error, error=error)

    def finish(self) -> None:
        self.finished = time.perf_counter()

    def register_callback(self, callback: Callable[[StreamEvent, StreamTask], None]) -> None:
        self.callbacks.append(callback)

    def emit(self, event: StreamEvent, task: StreamTask) -> None:
        for callback in tuple(self.callbacks):
            callback(event, task)

    @property
    def total_tasks(self) -> int:
        return len(self.tasks)

    @property
    def completed_tasks(self) -> int:
        return sum(task.status == TaskStatus.COMPLETED for task in self.tasks.values())

    @property
    def failed_tasks(self) -> int:
        return sum(task.status == TaskStatus.FAILED for task in self.tasks.values())

    @property
    def running_tasks(self) -> int:
        return sum(task.status == TaskStatus.RUNNING for task in self.tasks.values())

    @property
    def pending_tasks(self) -> int:
        return sum(task.status == TaskStatus.PENDING for task in self.tasks.values())

    @property
    def progress(self) -> float:
        return 0.0 if not self.total_tasks else 100.0 * (self.completed_tasks + self.failed_tasks) / self.total_tasks

    def elapsed(self) -> float:
        return max(0.0, (self.finished or time.perf_counter()) - self.started)

    def snapshot(self) -> dict[str, Any]:
        return {
            "progress": self.progress,
            "elapsed": self.elapsed(),
            "tasks": [
                {**asdict(task), "status": task.status.value, "duration": task.duration()}
                for task in self.tasks.values()
            ],
        }

    def statistics(self) -> dict[str, int | float]:
        return {
            "total": self.total_tasks,
            "completed": self.completed_tasks,
            "failed": self.failed_tasks,
            "running": self.running_tasks,
            "pending": self.pending_tasks,
            "progress": self.progress,
        }

    def summary(self) -> str:
        return f"{self.completed_tasks} completed, {self.failed_tasks} failed, {self.pending_tasks} pending"

    def to_dict(self) -> dict[str, Any]:
        return self.snapshot()

    def to_json(self) -> str:
        return json.dumps(self.snapshot(), indent=2)

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json() + "\n", encoding="utf-8")

    def render(self) -> None:
        if self.verbose:
            print(self.summary())
