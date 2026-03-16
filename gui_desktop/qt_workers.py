from __future__ import annotations

import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Signal


class TaskSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()
    log = Signal(str, str)


class FunctionTask(QRunnable):
    def __init__(self, fn: Callable[[TaskSignals], Any]):
        super().__init__()
        self.fn = fn
        self.signals = TaskSignals()

    def run(self) -> None:
        try:
            result = self.fn(self.signals)
            self.signals.result.emit(result)
        except Exception:
            self.signals.error.emit(traceback.format_exc())
        finally:
            self.signals.finished.emit()

