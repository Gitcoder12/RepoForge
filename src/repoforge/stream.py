"""Thread-safe task progress stream with consistent snapshots and counters."""

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

    def add_task(
        self, name: str, model: str | None = None, provider: str | None = None
    ) -> StreamTask:
        with self.lock:
            if name in self.tasks:
                raise ValueError(f"Task {name!r} already exists")
            task = StreamTask(name=name, model=model, provider=provider)
            self.tasks[name] = task
            return task

    def _transition(
        self,
        name: str,
        status: TaskStatus,
        message: str = "",
        response: str | None = None,
        error: str | None = None,
    ) -> StreamTask:
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
        with self.lock:
            self.finished = time.perf_counter()

    def register_callback(self, callback: Callable[[StreamEvent, StreamTask], None]) -> None:
        with self.lock:
            self.callbacks.append(callback)

    def emit(self, event: StreamEvent, task: StreamTask) -> None:
        with self.lock:
            callbacks = tuple(self.callbacks)
        for callback in callbacks:
            callback(event, task)

    @property
    def total_tasks(self) -> int:
        with self.lock:
            return len(self.tasks)

    @property
    def completed_tasks(self) -> int:
        with self.lock:
            return sum(task.status == TaskStatus.COMPLETED for task in self.tasks.values())

    @property
    def failed_tasks(self) -> int:
        with self.lock:
            return sum(task.status == TaskStatus.FAILED for task in self.tasks.values())

    @property
    def running_tasks(self) -> int:
        with self.lock:
            return sum(task.status == TaskStatus.RUNNING for task in self.tasks.values())

    @property
    def pending_tasks(self) -> int:
        with self.lock:
            return sum(task.status == TaskStatus.PENDING for task in self.tasks.values())

    @property
    def progress(self) -> float:
        with self.lock:
            total = len(self.tasks)
            if not total:
                return 0.0
            terminal = sum(
                task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
                for task in self.tasks.values()
            )
            return 100.0 * terminal / total

    def elapsed(self) -> float:
        with self.lock:
            return max(0.0, (self.finished or time.perf_counter()) - self.started)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            tasks = list(self.tasks.values())
            total = len(tasks)
            completed = sum(task.status == TaskStatus.COMPLETED for task in tasks)
            failed = sum(task.status == TaskStatus.FAILED for task in tasks)
            running = sum(task.status == TaskStatus.RUNNING for task in tasks)
            pending = sum(task.status == TaskStatus.PENDING for task in tasks)
            progress = 0.0 if not total else 100.0 * (completed + failed) / total
            elapsed = max(0.0, (self.finished or time.perf_counter()) - self.started)
            task_snapshots = [
                {**asdict(task), "status": task.status.value, "duration": task.duration()}
                for task in tasks
            ]
            return {
                "total_tasks": total,
                "progress": progress,
                "elapsed": elapsed,
                "tasks": task_snapshots,
                "statistics": {
                    "total": total,
                    "completed": completed,
                    "failed": failed,
                    "running": running,
                    "pending": pending,
                },
            }

    def statistics(self) -> dict[str, int | float]:
        with self.lock:
            total = len(self.tasks)
            completed = sum(task.status == TaskStatus.COMPLETED for task in self.tasks.values())
            failed = sum(task.status == TaskStatus.FAILED for task in self.tasks.values())
            running = sum(task.status == TaskStatus.RUNNING for task in self.tasks.values())
            pending = sum(task.status == TaskStatus.PENDING for task in self.tasks.values())
            progress = 0.0 if not total else 100.0 * (completed + failed) / total
            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "running": running,
                "pending": pending,
                "progress": progress,
            }

    def summary(self) -> str:
        with self.lock:
            completed = sum(task.status == TaskStatus.COMPLETED for task in self.tasks.values())
            failed = sum(task.status == TaskStatus.FAILED for task in self.tasks.values())
            pending = sum(task.status == TaskStatus.PENDING for task in self.tasks.values())
            return f"{completed} completed, {failed} failed, {pending} pending"

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
