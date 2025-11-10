from __future__ import annotations

from typing import Iterable, List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QStyle,
)


class EnvEditorDialog(QDialog):
    """Dialog allowing edition of simple key=value environment files."""

    def __init__(self, entries: Iterable[Tuple[str, str]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Variables d'environnement")
        self.resize(520, 420)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Clé", "Valeur"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)

        header = QLabel("Éditez les variables présentes dans le fichier .env")
        header.setWordWrap(True)
        header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(header)
        layout.addWidget(self._table, stretch=1)

        buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Ajouter")
        add_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        add_btn.setToolTip("Ajouter une nouvelle variable")
        remove_btn = QPushButton("Supprimer")
        remove_btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        remove_btn.setToolTip("Supprimer la variable sélectionnée")
        add_btn.clicked.connect(self._add_entry)
        remove_btn.clicked.connect(self._remove_entry)
        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(remove_btn)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate(entries)

    def _populate(self, entries: Iterable[Tuple[str, str]]) -> None:
        for key, value in entries:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(key))
            self._table.setItem(row, 1, QTableWidgetItem(value))

    def _add_entry(self) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        key_item = QTableWidgetItem("")
        value_item = QTableWidgetItem("")
        self._table.setItem(row, 0, key_item)
        self._table.setItem(row, 1, value_item)
        self._table.setCurrentCell(row, 0)
        self._table.editItem(key_item)

    def _remove_entry(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self._table.removeRow(row)

    def get_entries(self) -> List[Tuple[str, str]]:
        entries: List[Tuple[str, str]] = []
        for row in range(self._table.rowCount()):
            key_item = self._table.item(row, 0)
            value_item = self._table.item(row, 1)
            key = key_item.text().strip() if key_item else ""
            value = value_item.text() if value_item else ""
            if key:
                entries.append((key, value))
        return entries
