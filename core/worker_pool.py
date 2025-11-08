from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from PySide6.QtCore import QObject, Signal

from .models import DatabaseTask, ExecutionStatus
from .process_runner import ProcessRunner


class WorkerPool(QObject):
    task_started = Signal(DatabaseTask, str)
    task_output = Signal(DatabaseTask, str, bool)
    task_finished = Signal(DatabaseTask, ExecutionStatus, int)
    task_error = Signal(DatabaseTask, str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._runners: Dict[str, ProcessRunner] = {}

    def active_tasks(self) -> List[str]:
        return list(self._runners.keys())

    def start_runner(self, runner: ProcessRunner) -> None:
        task_id = runner.task.id()
        self._runners[task_id] = runner
        runner.started.connect(self.task_started)
        runner.stdout_received.connect(lambda task, text: self.task_output.emit(task, text, False))
        runner.stderr_received.connect(lambda task, text: self.task_output.emit(task, text, True))
        runner.finished.connect(self._on_finished)
        runner.error.connect(self.task_error)
        runner.start()

    def stop_all(self) -> None:
        for runner in list(self._runners.values()):
            runner.terminate()

    def stop_task(self, task: DatabaseTask) -> None:
        runner = self._runners.get(task.id())
        if runner:
            runner.terminate()

    def _on_finished(self, task: DatabaseTask, status: ExecutionStatus, exit_code: int) -> None:
        task_id = task.id()
        runner = self._runners.pop(task_id, None)
        if runner:
            runner.deleteLater()
        self.task_finished.emit(task, status, exit_code)
