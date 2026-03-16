from __future__ import annotations

from typing import Callable, Optional


class EventLogger:
    def __init__(self, sink: Optional[Callable[[str, str], None]] = None):
        self._sink = sink

    def _emit(self, level: str, message: str) -> None:
        if self._sink is not None:
            self._sink(level, message)

    def debug(self, message: str) -> None:
        self._emit("DEBUG", message)

    def info(self, message: str) -> None:
        self._emit("INFO", message)

    def warning(self, message: str) -> None:
        self._emit("WARNING", message)

    def error(self, message: str) -> None:
        self._emit("ERROR", message)

