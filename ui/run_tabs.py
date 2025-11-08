from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.models import DatabaseTask, ExecutionStatus


class RunTab(QWidget):
    def __init__(self, task: DatabaseTask, command: str, parent=None):
        super().__init__(parent)
        self.task = task
        self.command = command
        self.status_label = QLabel("En attente")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.stop_button = QPushButton("Arrêter ce process")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Commande : {command}"))
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_view)
        layout.addWidget(self.stop_button)

    def append_text(self, text: str, is_error: bool = False) -> None:
        if is_error:
            self.log_view.setTextColor(Qt.red)
        else:
            self.log_view.setTextColor(Qt.black)
        self.log_view.append(text)
        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_view.setTextCursor(cursor)

    def set_status(self, status: ExecutionStatus) -> None:
        mapping = {
            ExecutionStatus.RUNNING: "En cours",
            ExecutionStatus.SUCCEEDED: "Terminé",
            ExecutionStatus.FAILED: "Échec",
            ExecutionStatus.STOPPED: "Arrêté",
            ExecutionStatus.PENDING: "En attente",
        }
        self.status_label.setText(mapping.get(status, status.name))


class RunTabsWidget(QTabWidget):
    stop_requested = Signal(DatabaseTask)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tabs: Dict[str, RunTab] = {}

    def start_task(self, task: DatabaseTask, command: str) -> None:
        tab = RunTab(task, command)
        tab.set_status(ExecutionStatus.RUNNING)
        tab.stop_button.clicked.connect(lambda: self.stop_requested.emit(task))
        self._tabs[task.id()] = tab
        self.addTab(tab, task.display_name())
        self.setCurrentWidget(tab)

    def append_output(self, task: DatabaseTask, text: str, is_error: bool) -> None:
        tab = self._tabs.get(task.id())
        if tab:
            tab.append_text(text, is_error)

    def finish_task(self, task: DatabaseTask, status: ExecutionStatus) -> None:
        tab = self._tabs.get(task.id())
        if tab:
            tab.set_status(status)

    def clear_tasks(self) -> None:
        self._tabs.clear()
        self.clear()
