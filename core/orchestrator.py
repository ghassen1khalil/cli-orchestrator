from __future__ import annotations

import itertools
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from .models import AppSettings, DatabaseTask, ExecutionStatus, LotConfig
from .process_runner import ProcessRunner
from .worker_pool import WorkerPool


class Orchestrator(QObject):
    lot_started = Signal(LotConfig)
    lot_finished = Signal(LotConfig)
    lot_skipped = Signal(LotConfig, str)
    all_finished = Signal()
    task_started = Signal(DatabaseTask, str)
    task_output = Signal(DatabaseTask, str, bool)
    task_finished = Signal(DatabaseTask, ExecutionStatus, int)
    task_error = Signal(DatabaseTask, str)
    request_lot_confirmation = Signal(LotConfig)
    startup_error = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._settings: Optional[AppSettings] = None
        self._lots: List[LotConfig] = []
        self._current_lot_index: int = -1
        self._pending_tasks: set[str] = set()
        self._worker_pool = WorkerPool()
        self._worker_pool.task_started.connect(self.task_started)
        self._worker_pool.task_output.connect(self.task_output)
        self._worker_pool.task_finished.connect(self._on_task_finished)
        self._worker_pool.task_error.connect(self.task_error)
        self._awaiting_confirmation = False
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def start(self, settings: AppSettings) -> None:
        if self._running:
            return
        self._settings = settings
        self._lots = list(settings.lots)
        if not self._lots:
            self._running = False
            self.startup_error.emit("Aucun lot à exécuter")
            return
        jar_path = Path(settings.jar_path).expanduser()
        if not jar_path.exists():
            self._running = False
            self.startup_error.emit("Jar introuvable : %s" % jar_path)
            return
        self._current_lot_index = -1
        self._pending_tasks.clear()
        self._running = True
        self._awaiting_confirmation = False
        self._start_next_lot()

    def _start_next_lot(self) -> None:
        if not self._running:
            return
        self._current_lot_index += 1
        if self._current_lot_index >= len(self._lots):
            self._running = False
            self.all_finished.emit()
            return
        lot = self._lots[self._current_lot_index]
        databases = lot.iter_databases()
        if not databases:
            self.lot_skipped.emit(lot, "Aucune base trouvée pour ce lot")
            self._start_next_lot()
            return
        self._pending_tasks = {DatabaseTask(lot, db).id() for db in databases}
        self.lot_started.emit(lot)
        for db in databases:
            task = DatabaseTask(lot, db)
            command = self._build_command(task)
            runner = ProcessRunner(task, command)
            self._worker_pool.start_runner(runner)

    def _build_command(self, task: DatabaseTask) -> List[str]:
        assert self._settings is not None
        jar_path = Path(self._settings.jar_path).expanduser()
        jvm_args = self._settings.command_args.build_jvm_args(task.database)
        base_command = ["java", *jvm_args, "-jar", str(jar_path)]
        app_args = list(self._settings.command_args.app_arguments)
        return base_command + app_args

    def _on_task_finished(self, task: DatabaseTask, status: ExecutionStatus, exit_code: int) -> None:
        if task.id() in self._pending_tasks:
            self._pending_tasks.remove(task.id())
        self.task_finished.emit(task, status, exit_code)
        if not self._pending_tasks and self._running:
            lot = self._lots[self._current_lot_index]
            self.lot_finished.emit(lot)
            if self._settings and self._settings.auto_mode:
                self._start_next_lot()
            else:
                has_more_lots = self._current_lot_index + 1 < len(self._lots)
                if has_more_lots:
                    self._awaiting_confirmation = True
                    self.request_lot_confirmation.emit(lot)
                else:
                    # Aucun lot supplémentaire : terminer immédiatement sans demander.
                    self._start_next_lot()

    def continue_to_next_lot(self) -> None:
        if not self._running or not self._awaiting_confirmation:
            return
        self._awaiting_confirmation = False
        self._start_next_lot()

    def stop_all(self) -> None:
        self._worker_pool.stop_all()
        self._pending_tasks.clear()
        self._awaiting_confirmation = False
        if self._running:
            self._running = False
            self.all_finished.emit()

    def stop_task(self, task: DatabaseTask) -> None:
        self._worker_pool.stop_task(task)
