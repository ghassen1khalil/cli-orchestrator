from __future__ import annotations

import shlex
from typing import List, Optional

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from .models import DatabaseTask, ExecutionStatus


class ProcessRunner(QObject):
    started = Signal(DatabaseTask, str)
    stdout_received = Signal(DatabaseTask, str)
    stderr_received = Signal(DatabaseTask, str)
    finished = Signal(DatabaseTask, ExecutionStatus, int)
    error = Signal(DatabaseTask, str)

    def __init__(self, task: DatabaseTask, command: List[str], working_directory: Optional[str] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.task = task
        self.command = command
        self.working_directory = working_directory
        self._process: Optional[QProcess] = None
        self._terminated = False

    def start(self) -> None:
        if self._process is not None:
            return
        self._process = QProcess(self)
        if self.working_directory:
            self._process.setWorkingDirectory(self.working_directory)
        program = self.command[0]
        args = self.command[1:]
        self._process.setProgram(program)
        self._process.setArguments(args)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.stateChanged.connect(self._on_state_changed)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)
        self._process.start()
        if not self._process.waitForStarted(5000):
            self.error.emit(self.task, "Impossible de démarrer le processus")
            return
        self.started.emit(self.task, self.command_as_string())

    def terminate(self) -> None:
        self._terminated = True
        if self._process and self._process.state() != QProcess.NotRunning:
            self._process.terminate()
            QTimer.singleShot(2000, self._force_kill_if_needed)

    def _force_kill_if_needed(self) -> None:
        if self._process and self._process.state() != QProcess.NotRunning:
            self._process.kill()

    def _on_state_changed(self, state):
        pass

    def _on_stdout(self) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardOutput().data().decode(errors="replace")
        if data:
            self.stdout_received.emit(self.task, data)

    def _on_stderr(self) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardError().data().decode(errors="replace")
        if data:
            self.stderr_received.emit(self.task, data)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        status = ExecutionStatus.SUCCEEDED
        if self._terminated:
            status = ExecutionStatus.STOPPED
        elif exit_status != QProcess.ExitStatus.NormalExit or exit_code != 0:
            status = ExecutionStatus.FAILED
        self.finished.emit(self.task, status, exit_code)
        if self._process:
            self._process.deleteLater()
            self._process = None

    def _on_error(self, process_error: QProcess.ProcessError) -> None:
        self.error.emit(self.task, f"Erreur du processus: {process_error}")

    def command_as_string(self) -> str:
        return " ".join(shlex.quote(part) for part in self.command)
