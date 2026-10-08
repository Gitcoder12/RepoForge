# src/repoforge/logger.py

from __future__ import annotations

import json
import logging
import os
import threading
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


class LogLevel(IntEnum):
    """Supported logging levels."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass(slots=True)
class LoggerConfig:
    """
    Configuration for RepoForgeLogger.
    """

    name: str = "RepoForge"

    log_directory: Path = Path("logs")

    console: bool = True

    file: bool = True

    json_logs: bool = False

    timestamps: bool = True

    colors: bool = True

    level: LogLevel = LogLevel.INFO

    max_log_size: int = 5 * 1024 * 1024

    backup_count: int = 5


@dataclass(slots=True)
class LogRecord:
    """
    Represents a single log event.
    """

    timestamp: datetime

    level: LogLevel

    module: str

    message: str

    execution_id: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    exception: Optional[str] = None
    
    class RepoForgeLogger:
        """
    Central logger used throughout RepoForge.
    """

    COLORS = {
        LogLevel.DEBUG: "\033[90m",
        LogLevel.INFO: "\033[94m",
        LogLevel.WARNING: "\033[93m",
        LogLevel.ERROR: "\033[91m",
        LogLevel.CRITICAL: "\033[95m",
    }

    RESET = "\033[0m"

    def __init__(self, config: LoggerConfig | None = None):

        self.config = config or LoggerConfig()

        self._lock = threading.RLock()

        self._execution_id: Optional[str] = None

        self.config.log_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._logger = logging.getLogger(self.config.name)

        self._logger.setLevel(self.config.level.value)

        self._logger.handlers.clear()

        self._configure_handlers()
        
def set_execution_id(self, execution_id: str) -> None:
            self._execution_id = execution_id

def get_execution_id(self) -> Optional[str]:
        return self._execution_id
    
def debug(
        self,
        module: str,
        message: str,
        **metadata: Any,
    ) -> None:
        self._log(LogLevel.DEBUG, module, message, metadata)

def info(
        self,
        module: str,
        message: str,
        **metadata: Any,
    ) -> None:
        self._log(LogLevel.INFO, module, message, metadata)

def warning(
        self,
        module: str,
        message: str,
        **metadata: Any,
    ) -> None:
        self._log(LogLevel.WARNING, module, message, metadata)

def error(
        self,
        module: str,
        message: str,
        **metadata: Any,
    ) -> None:
        self._log(LogLevel.ERROR, module, message, metadata)

def critical(
        self,
        module: str,
        message: str,
        **metadata: Any,
    ) -> None:
        self._log(LogLevel.CRITICAL, module, message, metadata)
        
def exception(
        self,
        module: str,
        exc: Exception,
    ) -> None:

        self._log(
            LogLevel.ERROR,
            module,
            str(exc),
            {},
            traceback.format_exc(),
        )
        
def _configure_handlers(self) -> None:
        """Configure console and file handlers."""

        formatter = logging.Formatter(
            fmt="%(message)s"
        )

        if self.config.console:
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            self._logger.addHandler(console)

        if self.config.file:
            logfile = (
                self.config.log_directory
                / "repoforge.log"
            )

            file_handler = logging.FileHandler(
                logfile,
                encoding="utf-8",
            )

            file_handler.setFormatter(formatter)

            self._logger.addHandler(file_handler)
            
def _log(
        self,
        level: LogLevel,
        module: str,
        message: str,
        metadata: Dict[str, Any],
        exception: str | None = None,
    ) -> None:

        with self._lock:

            record = LogRecord(
                timestamp=datetime.now(),
                level=level,
                module=module,
                message=message,
                execution_id=self._execution_id,
                metadata=metadata,
                exception=exception,
            )

            formatted = self._format(record)

            self._logger.log(
                level.value,
                formatted,
            )
            
def _format(
        self,
        record: LogRecord,
    ) -> str:

        parts = []

        if self.config.timestamps:
            parts.append(
                record.timestamp.strftime("%H:%M:%S")
            )

        parts.append(record.level.name)

        parts.append(record.module)

        parts.append(record.message)

        if record.execution_id:
            parts.append(
                f"id={record.execution_id}"
            )

        if record.metadata:
            parts.append(
                json.dumps(
                    record.metadata,
                    ensure_ascii=False,
                )
            )

        if record.exception:
            parts.append(record.exception)

        output = " | ".join(parts)

        if self.config.colors:

            colour = self.COLORS.get(
                record.level,
                "",
            )

            output = (
                colour
                + output
                + self.RESET
            )

        return output
def banner(
        self,
        title: str,
    ) -> None:

        line = "=" * 70

        self.info(
            "SYSTEM",
            line,
        )

        self.info(
            "SYSTEM",
            title,
        )

        self.info(
            "SYSTEM",
            line,
        )
        
def separator(self) -> None:
    
        self.info(
            "SYSTEM",
            "-" * 70,
        )
        
def close(self) -> None:
    
        handlers = self._logger.handlers[:]

        for handler in handlers:

            handler.close()

            self._logger.removeHandler(
                handler
            )

def _to_json(
    self,
    record: LogRecord,
) -> str:
    """
    Convert a LogRecord into JSON.
    """

    return json.dumps(
        {
            "timestamp": record.timestamp.isoformat(),
            "level": record.level.name,
            "module": record.module,
            "message": record.message,
            "execution_id": record.execution_id,
            "metadata": record.metadata,
            "exception": record.exception,
        },
        ensure_ascii=False,
    )
    
@contextmanager
def timer(
    self,
    module: str,
    operation: str,
):
    """
    Measure execution time.
    """

    start = time.perf_counter()

    try:
        yield

    finally:

        elapsed = time.perf_counter() - start

        self.info(
            module,
            f"{operation} completed",
            elapsed_seconds=round(elapsed, 4),
        )

def measure(
    self,
    func,
    *args,
    **kwargs,
):
    """
    Execute a function while measuring duration.
    """

    start = time.perf_counter()

    result = func(*args, **kwargs)

    elapsed = time.perf_counter() - start

    return result, elapsed

def log_duration(
    self,
    module: str,
    operation: str,
    seconds: float,
) -> None:
    """
    Log elapsed time.
    """

    self.info(
        module,
        operation,
        duration=round(seconds, 4),
    )
    
def start_session(self) -> None:
    """
    Begin a logging session.
    """

    self.banner("RepoForge Session Started")

    self.info(
        "SYSTEM",
        "Logger initialized",
    )
    
def end_session(self) -> None:
    """
    Finish a logging session.
    """

    self.info(
        "SYSTEM",
        "Logger shutting down",
    )

    self.banner("Session Finished")
    
def flush(self) -> None:
    """
    Flush all handlers.
    """

    for handler in self._logger.handlers:

        handler.flush()
        
def is_enabled(
    self,
    level: LogLevel,
) -> bool:
    """
    Check if a log level is enabled.
    """

    return level.value >= self.config.level.value

def set_level(
    self,
    level: LogLevel,
) -> None:
    """
    Change logger level.
    """

    self.config.level = level

    self._logger.setLevel(level.value)
    
