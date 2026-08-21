"""
Blackboard – shared context for agents to read/write.
"""

from typing import Dict, Any
import threading


class Blackboard:
    """Thread-safe shared memory for agent communication."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any):
        with self._lock:
            self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def update(self, data: Dict[str, Any]):
        with self._lock:
            self._data.update(data)

    def all(self) -> Dict[str, Any]:
        with self._lock:
            return self._data.copy()

    def clear(self):
        with self._lock:
            self._data.clear()