from __future__ import annotations

from typing import Callable, Dict

from PySide6.QtCore import QElapsedTimer, QTimer, Qt, Signal, QSize
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QStyle,
)

from core.models import DatabaseTask, ExecutionStatus


class RunTab(QWidget):
    def __init__(self, task: DatabaseTask, command: str, parent=None):
        super().__init__(parent)
        self.task = task
        self.command = command
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMargin(6)
        self.timer_label = QLabel("Temps écoulé : 00:00")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Les messages du process apparaîtront ici...")
        self.stop_button = QPushButton("Arrêter ce process")
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.setIconSize(QSize(20, 20))
        self.stop_button.setToolTip("Forcer l'arrêt de ce process en cours")
        self._elapsed_timer = QElapsedTimer()
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._update_elapsed_time)

        layout = QVBoxLayout(self)
        command_label = QLabel(f"Commande : {command}")
        command_label.setWordWrap(True)
        command_label.setStyleSheet("font-family: monospace; color: #333;")
        layout.addWidget(command_label)
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Statut :"))
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.timer_label)
        layout.addLayout(status_layout)
        layout.addWidget(self.log_view)
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        controls_layout.addWidget(self.stop_button)
        layout.addLayout(controls_layout)
        self.set_status(ExecutionStatus.PENDING)

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
        text_mapping = {
            ExecutionStatus.PENDING: "A Traiter",
            ExecutionStatus.RUNNING: "En cours de traitement",
            ExecutionStatus.SUCCEEDED: "Terminé",
            ExecutionStatus.FAILED: "Interrompu",
            ExecutionStatus.STOPPED: "Interrompu",
        }
        style_mapping = {
            ExecutionStatus.PENDING: "background-color: #E0ECFF; color: #0A4F8B; border-radius: 10px;",
            ExecutionStatus.RUNNING: "background-color: #FFF4CC; color: #8A6D3B; border-radius: 10px;",
            ExecutionStatus.SUCCEEDED: "background-color: #DFF2BF; color: #3C763D; border-radius: 10px;",
            ExecutionStatus.FAILED: "background-color: #F2DEDE; color: #A94442; border-radius: 10px;",
            ExecutionStatus.STOPPED: "background-color: #F2DEDE; color: #A94442; border-radius: 10px;",
        }
        self.status_label.setText(text_mapping.get(status, status.name))
        style = style_mapping.get(status)
        if style:
            self.status_label.setStyleSheet(style)
        self.stop_button.setEnabled(status == ExecutionStatus.RUNNING)
        if status == ExecutionStatus.RUNNING and not self._tick_timer.isActive():
            self._start_elapsed_timer()
        elif status in (ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED, ExecutionStatus.STOPPED):
            self._stop_elapsed_timer()

    def _start_elapsed_timer(self) -> None:
        self._elapsed_timer.start()
        self._update_elapsed_time()
        self._tick_timer.start()

    def _stop_elapsed_timer(self) -> None:
        if self._tick_timer.isActive():
            self._tick_timer.stop()
        if self._elapsed_timer.isValid():
            self._update_elapsed_time()

    def _update_elapsed_time(self) -> None:
        if not self._elapsed_timer.isValid():
            return
        elapsed_ms = self._elapsed_timer.elapsed()
        hours = elapsed_ms // 3_600_000
        minutes = (elapsed_ms // 60_000) % 60
        seconds = (elapsed_ms // 1_000) % 60
        if hours:
            formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            formatted = f"{minutes:02d}:{seconds:02d}"
        self.timer_label.setText(f"Temps écoulé : {formatted}")


class LotLogsTab(QWidget):
    def __init__(self, lot_name: str, stop_callback: Callable[[DatabaseTask], None], parent=None):
        super().__init__(parent)
        self.lot_name = lot_name
        self._stop_callback = stop_callback
        self._tabs: Dict[str, RunTab] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        header = QLabel(f"Logs du lot : {lot_name}")
        header.setAlignment(Qt.AlignLeft)
        header.setStyleSheet("font-weight: 600; color: #444;")
        layout.addWidget(header)

        self._tab_widget = QTabWidget()
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.setMovable(True)
        self._tab_widget.setTabPosition(QTabWidget.North)
        self._tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._tab_widget)

    def start_task(self, task: DatabaseTask, command: str) -> None:
        tab = RunTab(task, command)
        tab.set_status(ExecutionStatus.RUNNING)
        tab.stop_button.clicked.connect(lambda _=False, t=task: self._stop_callback(t))
        self._tabs[task.id()] = tab
        self._tab_widget.addTab(
            tab,
            self._icon_for_status(ExecutionStatus.RUNNING),
            task.display_name(),
        )
        self._tab_widget.setCurrentWidget(tab)

    def append_output(self, task: DatabaseTask, text: str, is_error: bool) -> None:
        tab = self._tabs.get(task.id())
        if tab:
            tab.append_text(text, is_error)

    def finish_task(self, task: DatabaseTask, status: ExecutionStatus) -> None:
        tab = self._tabs.get(task.id())
        if tab:
            tab.set_status(status)
            index = self._tab_widget.indexOf(tab)
            if index != -1:
                self._tab_widget.setTabIcon(index, self._icon_for_status(status))

    def _icon_for_status(self, status: ExecutionStatus):
        mapping = {
            ExecutionStatus.PENDING: QStyle.SP_BrowserReload,
            ExecutionStatus.RUNNING: QStyle.SP_MediaPlay,
            ExecutionStatus.SUCCEEDED: QStyle.SP_DialogApplyButton,
            ExecutionStatus.FAILED: QStyle.SP_MessageBoxCritical,
            ExecutionStatus.STOPPED: QStyle.SP_MessageBoxWarning,
        }
        icon_type = mapping.get(status, QStyle.SP_FileDialogInfoView)
        return self.style().standardIcon(icon_type)


class RunTabsWidget(QTabWidget):
    stop_requested = Signal(DatabaseTask)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lot_tabs: Dict[str, LotLogsTab] = {}
        self.setDocumentMode(True)
        self.setMovable(True)

    def reset(self) -> None:
        self._lot_tabs.clear()
        self.clear()

    def mark_lot_started(self, lot_name: str) -> None:
        tab = self._ensure_lot_tab(lot_name)
        index = self.indexOf(tab)
        if index != -1:
            self.setCurrentIndex(index)
            self.setTabIcon(index, self.style().standardIcon(QStyle.SP_MediaPlay))
            self.setTabToolTip(index, f"Lot {lot_name} en cours")

    def mark_lot_finished(self, lot_name: str) -> None:
        tab = self._lot_tabs.get(lot_name)
        if not tab:
            return
        index = self.indexOf(tab)
        if index != -1:
            self.setTabIcon(index, self.style().standardIcon(QStyle.SP_DialogApplyButton))
            self.setTabToolTip(index, f"Lot {lot_name} terminé")

    def mark_lot_skipped(self, lot_name: str, reason: str | None = None) -> None:
        tab = self._ensure_lot_tab(lot_name)
        index = self.indexOf(tab)
        if index != -1:
            icon = self.style().standardIcon(QStyle.SP_MessageBoxWarning)
            self.setTabIcon(index, icon)
            tooltip = f"Lot {lot_name} ignoré"
            if reason:
                tooltip += f" : {reason}"
            self.setTabToolTip(index, tooltip)

    def start_task(self, task: DatabaseTask, command: str) -> None:
        tab = self._ensure_lot_tab(task.lot.name)
        tab.start_task(task, command)
        index = self.indexOf(tab)
        if index != -1:
            self.setCurrentIndex(index)

    def append_output(self, task: DatabaseTask, text: str, is_error: bool) -> None:
        tab = self._lot_tabs.get(task.lot.name)
        if tab:
            tab.append_output(task, text, is_error)

    def finish_task(self, task: DatabaseTask, status: ExecutionStatus) -> None:
        tab = self._lot_tabs.get(task.lot.name)
        if tab:
            tab.finish_task(task, status)

    def _ensure_lot_tab(self, lot_name: str) -> LotLogsTab:
        tab = self._lot_tabs.get(lot_name)
        if tab:
            return tab
        tab = LotLogsTab(lot_name, self.stop_requested.emit)
        self._lot_tabs[lot_name] = tab
        icon = self.style().standardIcon(QStyle.SP_FileDialogInfoView)
        self.addTab(tab, icon, lot_name)
        self.setTabToolTip(self.indexOf(tab), f"Onglets de bases pour le lot {lot_name}")
        return tab
