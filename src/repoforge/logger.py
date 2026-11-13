"""Small structured logger with a stable RepoForgeLogger API."""

from __future__ import annotations

import json
import logging
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class RepoForgeLogger:
    def __init__(self, name: str = "RepoForge", log_directory: str | Path = "logs", console: bool = True, file: bool = False):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self._lock = threading.RLock()
        self._execution_id: str | None = None
        self._logger.handlers.clear()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        if console:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
        if file:
            directory = Path(log_directory)
            directory.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(directory / "repoforge.log", encoding="utf-8")
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

    def set_execution_id(self, execution_id: str) -> None:
        self._execution_id = execution_id

    def get_execution_id(self) -> str | None:
        return self._execution_id

    def _write(self, level: int, module: str, message: str, metadata: dict[str, Any]) -> None:
        with self._lock:
            suffix = f" | {json.dumps(metadata, sort_keys=True, default=str)}" if metadata else ""
            execution = f" | id={self._execution_id}" if self._execution_id else ""
            self._logger.log(level, "%s | %s%s%s", module, message, execution, suffix)

    def debug(self, module: str, message: str, **metadata: Any) -> None:
        self._write(logging.DEBUG, module, message, metadata)

    def info(self, module: str, message: str, **metadata: Any) -> None:
        self._write(logging.INFO, module, message, metadata)

    def warning(self, module: str, message: str, **metadata: Any) -> None:
        self._write(logging.WARNING, module, message, metadata)

    def error(self, module: str, message: str, **metadata: Any) -> None:
        self._write(logging.ERROR, module, message, metadata)

    def critical(self, module: str, message: str, **metadata: Any) -> None:
        self._write(logging.CRITICAL, module, message, metadata)

    def exception(self, module: str, exc: Exception) -> None:
        self._logger.exception("%s | %s", module, exc)

    def banner(self, title: str) -> None:
        self.info("SYSTEM", "=" * 60)
        self.info("SYSTEM", title)
        self.info("SYSTEM", "=" * 60)

    def separator(self) -> None:
        self.info("SYSTEM", "-" * 60)

    @contextmanager
    def timer(self, module: str, operation: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self.info(module, f"{operation} completed", elapsed_seconds=round(time.perf_counter() - start, 4))

    def measure(self, func: Any, *args: Any, **kwargs: Any) -> tuple[Any, float]:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        return result, time.perf_counter() - start

    def log_duration(self, module: str, operation: str, seconds: float) -> None:
        self.info(module, operation, duration=round(seconds, 4))

    def start_session(self) -> None:
        self.banner("RepoForge Session Started")

    def end_session(self) -> None:
        self.banner("RepoForge Session Finished")

    def flush(self) -> None:
        for handler in self._logger.handlers:
            handler.flush()

    def close(self) -> None:
        for handler in self._logger.handlers[:]:
            handler.flush()
            handler.close()
            self._logger.removeHandler(handler)

    def is_enabled(self, level: int) -> bool:
        return self._logger.isEnabledFor(level)

    def set_level(self, level: int) -> None:
        self._logger.setLevel(level)
