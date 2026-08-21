"""
RepoForge Stream Manager

Provides real-time streaming updates during orchestration.

Features
--------
- Thread-safe task updates
- Progress tracking
- Console streaming
- JSON events
- Callbacks
- Execution timing
"""

from __future__ import annotations

import json
import threading
import time

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional


# ==========================================================
# Task Status
# ==========================================================

class TaskStatus(str, Enum):
    """Current state of a task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ==========================================================
# Stream Event
# ==========================================================

class StreamEvent(str, Enum):
    """Events emitted by the stream manager."""

    START = "start"
    UPDATE = "update"
    COMPLETE = "complete"
    ERROR = "error"


# ==========================================================
# Individual Task State
# ==========================================================

@dataclass
class StreamTask:
    """
    Represents one orchestration task.
    """

    name: str

    status: TaskStatus = TaskStatus.PENDING

    model: Optional[str] = None

    provider: Optional[str] = None

    started: Optional[float] = None

    finished: Optional[float] = None

    message: str = ""

    response: Optional[str] = None

    error: Optional[str] = None

    def duration(self) -> float:
        """
        Returns execution duration.
        """

        if self.started is None:
            return 0.0

        if self.finished is None:
            return time.perf_counter() - self.started

        return self.finished - self.started


# ==========================================================
# Stream Configuration
# ==========================================================

@dataclass
class StreamConfig:

    verbose: bool = True

    json_output: bool = False

    show_timer: bool = True

    show_progress: bool = True

    auto_flush: bool = True


# ==========================================================
# Stream Manager
# ==========================================================

class StreamManager:
    """
    Handles real-time execution updates.
    """

    def __init__(
        self,
        config: Optional[StreamConfig] = None,
    ):

        self.config = config or StreamConfig()

        self.tasks: Dict[str, StreamTask] = {}

        self.callbacks: List[Callable] = []

        self.lock = threading.Lock()

        self.started = time.perf_counter()

        self.finished: Optional[float] = None

    # ------------------------------------------------------

    def add_task(
        self,
        name: str,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> StreamTask:
        """
        Register a new task.
        """

        task = StreamTask(
            name=name,
            model=model,
            provider=provider,
        )

        with self.lock:
            self.tasks[name] = task

        return task

    # ------------------------------------------------------

    def get_task(
        self,
        name: str,
    ) -> Optional[StreamTask]:

        return self.tasks.get(name)

    # ------------------------------------------------------

    @property
    def total_tasks(self) -> int:

        return len(self.tasks)

    # ------------------------------------------------------

    @property
    def completed_tasks(self) -> int:

        return sum(
            1
            for task in self.tasks.values()
            if task.status == TaskStatus.COMPLETED
        )

    # ------------------------------------------------------

    @property
    def failed_tasks(self) -> int:

        return sum(
            1
            for task in self.tasks.values()
            if task.status == TaskStatus.FAILED
        )

    # ------------------------------------------------------

    @property
    def running_tasks(self) -> int:

        return sum(
            1
            for task in self.tasks.values()
            if task.status == TaskStatus.RUNNING
        )

    # ------------------------------------------------------

    @property
    def pending_tasks(self) -> int:

        return sum(
            1
            for task in self.tasks.values()
            if task.status == TaskStatus.PENDING
        )

    # ------------------------------------------------------

    @property
    def progress(self) -> float:

        if self.total_tasks == 0:
            return 0.0

        return (
            (self.completed_tasks + self.failed_tasks)
            / self.total_tasks
        ) * 100

    # ------------------------------------------------------

    def elapsed(self) -> float:

        if self.finished:

            return self.finished - self.started

        return time.perf_counter() - self.started
    
    # ==========================================================
# Task Lifecycle
# ==========================================================

    def start_task(
        self,
        name: str,
        message: str = "",
    ) -> StreamTask:
        """
        Mark a task as running.
        """

        with self.lock:

            task = self.tasks.get(name)

            if task is None:
                raise ValueError(f"Task '{name}' does not exist.")

            task.status = TaskStatus.RUNNING
            task.started = time.perf_counter()
            task.message = message

        self.emit(StreamEvent.START, task)

        return task

    # ------------------------------------------------------

    def update_task(
        self,
        name: str,
        message: str,
    ) -> None:
        """
        Update task progress message.
        """

        with self.lock:

            task = self.tasks.get(name)

            if task is None:
                raise ValueError(f"Task '{name}' does not exist.")

            task.message = message

        self.emit(StreamEvent.UPDATE, task)

    # ------------------------------------------------------

    def complete_task(
        self,
        name: str,
        response: str = "",
    ) -> None:
        """
        Mark a task as completed.
        """

        with self.lock:

            task = self.tasks.get(name)

            if task is None:
                raise ValueError(f"Task '{name}' does not exist.")

            task.status = TaskStatus.COMPLETED
            task.finished = time.perf_counter()
            task.response = response

        self.emit(StreamEvent.COMPLETE, task)

    # ------------------------------------------------------

    def fail_task(
        self,
        name: str,
        error: str,
    ) -> None:
        """
        Mark a task as failed.
        """

        with self.lock:

            task = self.tasks.get(name)

            if task is None:
                raise ValueError(f"Task '{name}' does not exist.")

            task.status = TaskStatus.FAILED
            task.finished = time.perf_counter()
            task.error = error

        self.emit(StreamEvent.ERROR, task)

    # ------------------------------------------------------

    def finish(self) -> None:
        """
        Mark overall execution complete.
        """

        self.finished = time.perf_counter()
        
        # ==========================================================
# Event System
# ==========================================================

    def register_callback(
        self,
        callback: Callable,
    ) -> None:
        """
        Register a callback.

        Callback signature:

            callback(event, task)
        """

        self.callbacks.append(callback)

    # ------------------------------------------------------

    def emit(
        self,
        event: StreamEvent,
        task: StreamTask,
    ) -> None:
        """
        Notify all listeners.
        """

        for callback in self.callbacks:

            try:

                callback(event, task)

            except Exception:
                pass
            
            # ==========================================================
# Serialization
# ==========================================================

    def to_dict(self):

        return {

            "progress": self.progress,

            "elapsed": self.elapsed(),

            "tasks": [

                {

                    "name": task.name,

                    "status": task.status.value,

                    "model": task.model,

                    "provider": task.provider,

                    "duration": round(
                        task.duration(),
                        2,
                    ),

                    "message": task.message,

                }

                for task in self.tasks.values()

            ]

        }

    # ------------------------------------------------------

    def to_json(self):

        return json.dumps(

            self.to_dict(),

            indent=4,

        )
        
        # ==========================================================
# Console Renderer
# ==========================================================

    def render(self) -> None:
        """
        Render current execution state.
        """

        if not self.config.verbose:
            return

        print("\n" + "=" * 70)
        print("🚀 RepoForge Live Execution")
        print("=" * 70)

        for index, task in enumerate(
            self.tasks.values(),
            start=1,
        ):

            if task.status == TaskStatus.COMPLETED:
                icon = "✅"

            elif task.status == TaskStatus.RUNNING:
                icon = "🔄"

            elif task.status == TaskStatus.FAILED:
                icon = "❌"

            else:
                icon = "⏳"

            duration = f"{task.duration():.2f}s"

            print(
                f"[{index}/{self.total_tasks}] "
                f"{icon} "
                f"{task.name:<20}"
                f"{task.status.value:<10}"
                f"{duration:<10}"
                f"{task.message}"
            )

        if self.config.show_progress:

            print()

            print(
                f"Progress : "
                f"{self.progress:.1f}%"
            )

            print(
                f"Completed: {self.completed_tasks}"
            )

            print(
                f"Running  : {self.running_tasks}"
            )

            print(
                f"Pending  : {self.pending_tasks}"
            )

            print(
                f"Failed   : {self.failed_tasks}"
            )

        if self.config.show_timer:

            print(
                f"Elapsed  : {self.elapsed():.2f}s"
            )

        print("=" * 70)

    # ------------------------------------------------------

    def summary(self) -> None:
        """
        Print final execution summary.
        """

        print()

        print("=" * 70)
        print("📊 RepoForge Summary")
        print("=" * 70)

        print(f"Total Tasks : {self.total_tasks}")
        print(f"Completed   : {self.completed_tasks}")
        print(f"Failed      : {self.failed_tasks}")
        print(f"Elapsed     : {self.elapsed():.2f}s")

        print("=" * 70)
        
        # ==========================================================
# Utilities
# ==========================================================

    def reset(self) -> None:
        """
        Reset the stream manager for a new execution.
        """

        with self.lock:

            self.tasks.clear()
            self.callbacks.clear()

            self.started = time.perf_counter()
            self.finished = None

    # ------------------------------------------------------

    def save(
        self,
        filepath: str | Path,
    ) -> Path:
        """
        Save current stream state as JSON.
        """

        filepath = Path(filepath)

        filepath.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        filepath.write_text(
            self.to_json(),
            encoding="utf-8",
        )

        return filepath

    # ------------------------------------------------------

    def snapshot(self) -> dict:
        """
        Return current execution snapshot.
        """

        return {

            "progress": round(
                self.progress,
                2,
            ),

            "elapsed": round(
                self.elapsed(),
                2,
            ),

            "completed": self.completed_tasks,

            "failed": self.failed_tasks,

            "running": self.running_tasks,

            "pending": self.pending_tasks,

            "tasks": self.total_tasks,

        }

    # ------------------------------------------------------

    def statistics(self) -> dict:
        """
        Return execution statistics.
        """

        return {

            "total": self.total_tasks,

            "completed": self.completed_tasks,

            "failed": self.failed_tasks,

            "running": self.running_tasks,

            "pending": self.pending_tasks,

            "success_rate": (
                (
                    self.completed_tasks
                    / self.total_tasks
                ) * 100
                if self.total_tasks
                else 0
            ),

            "elapsed": round(
                self.elapsed(),
                2,
            ),

        }

    # ------------------------------------------------------

    def __len__(self):

        return self.total_tasks

    # ------------------------------------------------------

    def __iter__(self):

        return iter(
            self.tasks.values()
        )

    # ------------------------------------------------------

    def __contains__(
        self,
        name: str,
    ):

        return name in self.tasks

    # ------------------------------------------------------

    def __repr__(self):

        return (

            f"StreamManager("
            f"tasks={self.total_tasks}, "
            f"completed={self.completed_tasks}, "
            f"failed={self.failed_tasks}, "
            f"progress={self.progress:.1f}%"
            f")"

        )