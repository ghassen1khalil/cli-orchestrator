from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.models import DatabaseTask, ExecutionStatus, LotConfig


@dataclass
class LotProgress:
    lot: LotConfig
    total_databases: int
    processed: int = 0
    running: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: bool = False
    status: str = field(default="En attente", init=False)

    def reset(self) -> None:
        self.processed = 0
        self.running = 0
        self.succeeded = 0
        self.failed = 0
        self.skipped = False
        self.status = "En attente"


class DashboardWidget(QFrame):
    """Widget qui présente un récapitulatif visuel de l'état des lots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lot_rows: List[str] = []
        self._progress: Dict[str, LotProgress] = {}
        self._summary_labels: Dict[str, QLabel] = {}

        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("dashboardFrame")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self._build_summary(layout)
        self._build_table(layout)

    def _build_summary(self, parent_layout: QVBoxLayout) -> None:
        summary_frame = QFrame()
        summary_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        summary_layout = QGridLayout(summary_frame)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setHorizontalSpacing(16)
        summary_layout.setVerticalSpacing(0)

        metrics = [
            ("Lots chargés", "lots"),
            ("Bases détectées", "databases"),
            ("Lots terminés", "lots_done"),
            ("Lots en cours", "lots_running"),
            ("Lots en attente", "lots_pending"),
            ("Erreurs cumulées", "errors"),
        ]
        for index, (label, key) in enumerate(metrics):
            column = index
            container = QFrame()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(2)
            title = QLabel(label)
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("color: #666; font-size: 10px; font-weight: 500;")
            value = QLabel("0")
            value.setAlignment(Qt.AlignCenter)
            value.setStyleSheet("font-size: 18px; font-weight: 600;")
            container_layout.addWidget(value)
            container_layout.addWidget(title)
            summary_layout.addWidget(container, 0, column)
            self._summary_labels[key] = value

        summary_layout.setColumnStretch(0, 1)
        summary_layout.setColumnStretch(1, 1)
        summary_layout.setColumnStretch(2, 1)
        summary_layout.setColumnStretch(3, 1)
        summary_layout.setColumnStretch(4, 1)
        summary_layout.setColumnStretch(5, 1)

        parent_layout.addWidget(summary_frame)

    def _build_table(self, parent_layout: QVBoxLayout) -> None:
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            [
                "Lot",
                "Bases totales",
                "Traitées",
                "En cours",
                "Erreurs",
                "Statut",
            ]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        parent_layout.addWidget(self._table)

    # --- Données ---
    def set_lots(self, lots: List[LotConfig]) -> None:
        self._lot_rows = [lot.name for lot in lots]
        self._progress = {
            lot.name: LotProgress(lot=lot, total_databases=len(lot.iter_databases()))
            for lot in lots
        }
        self.prepare_for_run()

    def prepare_for_run(self) -> None:
        for progress in self._progress.values():
            progress.reset()
        self._refresh_ui()

    def mark_lot_started(self, lot: LotConfig) -> None:
        progress = self._progress.get(lot.name)
        if not progress:
            return
        progress.status = "En cours"
        self._refresh_ui()

    def mark_lot_finished(self, lot: LotConfig) -> None:
        progress = self._progress.get(lot.name)
        if not progress:
            return
        progress.status = "Terminé" if progress.failed == 0 else "Terminé avec erreurs"
        self._refresh_ui()

    def mark_lot_skipped(self, lot: LotConfig, reason: str | None = None) -> None:
        progress = self._progress.get(lot.name)
        if not progress:
            return
        progress.skipped = True
        progress.status = "Ignoré" if not reason else f"Ignoré ({reason})"
        self._refresh_ui()

    def mark_task_started(self, task: DatabaseTask) -> None:
        progress = self._progress.get(task.lot.name)
        if not progress:
            return
        progress.running += 1
        if progress.status == "En attente":
            progress.status = "En cours"
        self._refresh_ui()

    def mark_task_finished(self, task: DatabaseTask, status: ExecutionStatus) -> None:
        progress = self._progress.get(task.lot.name)
        if not progress:
            return
        progress.running = max(0, progress.running - 1)
        progress.processed += 1
        if status == ExecutionStatus.SUCCEEDED:
            progress.succeeded += 1
        elif status in (ExecutionStatus.FAILED, ExecutionStatus.STOPPED):
            progress.failed += 1
        if progress.processed >= progress.total_databases and not progress.skipped:
            progress.status = "Terminé" if progress.failed == 0 else "Terminé avec erreurs"
        elif not progress.skipped:
            progress.status = "En cours"
        self._refresh_ui()

    def mark_run_completed(self) -> None:
        self._refresh_ui()

    # --- UI updates ---
    def _refresh_ui(self) -> None:
        self._update_table()
        self._update_summary()

    def _update_table(self) -> None:
        self._table.setRowCount(len(self._lot_rows))
        for row, lot_name in enumerate(self._lot_rows):
            progress = self._progress.get(lot_name)
            if not progress:
                continue
            self._table.setItem(row, 0, QTableWidgetItem(lot_name))
            self._table.setItem(row, 1, QTableWidgetItem(str(progress.total_databases)))
            progress_text = f"{progress.processed}/{progress.total_databases}"
            self._table.setItem(row, 2, QTableWidgetItem(progress_text))
            self._table.setItem(row, 3, QTableWidgetItem(str(progress.running)))
            self._table.setItem(row, 4, QTableWidgetItem(str(progress.failed)))
            self._table.setItem(row, 5, QTableWidgetItem(progress.status))
        self._table.resizeRowsToContents()

    def _update_summary(self) -> None:
        lots_total = len(self._progress)
        databases_total = sum(p.total_databases for p in self._progress.values())
        lots_done = sum(1 for p in self._progress.values() if p.status.startswith("Terminé") or p.skipped)
        lots_running = sum(1 for p in self._progress.values() if p.status == "En cours")
        lots_pending = sum(1 for p in self._progress.values() if p.status == "En attente")
        errors = sum(p.failed for p in self._progress.values())

        self._set_summary_value("lots", lots_total)
        self._set_summary_value("databases", databases_total)
        self._set_summary_value("lots_done", lots_done)
        self._set_summary_value("lots_running", lots_running)
        self._set_summary_value("lots_pending", lots_pending)
        self._set_summary_value("errors", errors)

    def _set_summary_value(self, key: str, value: int) -> None:
        label = self._summary_labels.get(key)
        if label:
            label.setText(str(value))
