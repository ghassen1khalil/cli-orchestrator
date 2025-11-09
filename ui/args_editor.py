from __future__ import annotations

from typing import List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QStyle,
)


class ArgsEditorDialog(QDialog):
    def __init__(self, jvm_properties: List[Tuple[str, str]], app_arguments: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Arguments Java")
        self.resize(600, 400)
        self._jvm_table = QTableWidget(0, 2)
        self._jvm_table.setHorizontalHeaderLabels(["Clé", "Valeur"])
        self._jvm_table.horizontalHeader().setStretchLastSection(True)
        self._jvm_table.verticalHeader().setVisible(False)
        self._jvm_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._jvm_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._jvm_table.setAlternatingRowColors(True)
        self._jvm_table.setMinimumHeight(150)

        self._app_list = QListWidget()
        self._app_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._app_list.setAlternatingRowColors(True)
        self._app_list.setMinimumHeight(150)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_jvm_group())
        layout.addWidget(self._build_app_group())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate_jvm(jvm_properties)
        self._populate_app(app_arguments)

    def _build_jvm_group(self) -> QGroupBox:
        group = QGroupBox("Propriétés JVM (-D)")
        layout = QVBoxLayout(group)
        layout.addWidget(self._jvm_table)
        button_bar = QHBoxLayout()
        add_btn = QPushButton("Ajouter")
        add_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        add_btn.setToolTip("Ajouter une propriété JVM (-Dclé=valeur)")
        remove_btn = QPushButton("Supprimer")
        remove_btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        remove_btn.setToolTip("Supprimer la propriété sélectionnée")
        add_btn.clicked.connect(self._add_jvm_row)
        remove_btn.clicked.connect(self._remove_jvm_row)
        button_bar.addWidget(add_btn)
        button_bar.addWidget(remove_btn)
        button_bar.addStretch()
        layout.addLayout(button_bar)
        return group

    def _build_app_group(self) -> QGroupBox:
        group = QGroupBox("Arguments applicatifs")
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel("Ordre de passage après le jar"))
        layout.addWidget(self._app_list)
        button_bar = QHBoxLayout()
        add_btn = QPushButton("Ajouter")
        add_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        add_btn.setToolTip("Ajouter un nouvel argument applicatif")
        edit_btn = QPushButton("Éditer")
        edit_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        edit_btn.setToolTip("Modifier l'argument sélectionné")
        remove_btn = QPushButton("Supprimer")
        remove_btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        remove_btn.setToolTip("Supprimer l'argument sélectionné")
        up_btn = QPushButton("Monter")
        up_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        up_btn.setToolTip("Monter l'argument dans la liste")
        down_btn = QPushButton("Descendre")
        down_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        down_btn.setToolTip("Descendre l'argument dans la liste")
        add_btn.clicked.connect(self._add_app_argument)
        edit_btn.clicked.connect(self._edit_app_argument)
        remove_btn.clicked.connect(self._remove_app_argument)
        up_btn.clicked.connect(lambda: self._move_app_argument(-1))
        down_btn.clicked.connect(lambda: self._move_app_argument(1))
        for btn in (add_btn, edit_btn, remove_btn, up_btn, down_btn):
            button_bar.addWidget(btn)
        button_bar.addStretch()
        layout.addLayout(button_bar)
        return group

    def _populate_jvm(self, properties: List[Tuple[str, str]]) -> None:
        for key, value in properties:
            row = self._jvm_table.rowCount()
            self._jvm_table.insertRow(row)
            self._jvm_table.setItem(row, 0, QTableWidgetItem(key))
            self._jvm_table.setItem(row, 1, QTableWidgetItem(value))

    def _populate_app(self, arguments: List[str]) -> None:
        for arg in arguments:
            QListWidgetItem(arg, self._app_list)

    def _add_jvm_row(self) -> None:
        row = self._jvm_table.rowCount()
        self._jvm_table.insertRow(row)
        self._jvm_table.setItem(row, 0, QTableWidgetItem(""))
        self._jvm_table.setItem(row, 1, QTableWidgetItem(""))
        self._jvm_table.editItem(self._jvm_table.item(row, 0))

    def _remove_jvm_row(self) -> None:
        row = self._jvm_table.currentRow()
        if row >= 0:
            self._jvm_table.removeRow(row)

    def _add_app_argument(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        text, ok = QInputDialog.getText(self, "Nouvel argument", "Argument :")
        if ok and text:
            QListWidgetItem(text, self._app_list)

    def _edit_app_argument(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        current = self._app_list.currentItem()
        if not current:
            return
        text, ok = QInputDialog.getText(self, "Modifier argument", "Argument :", text=current.text())
        if ok and text:
            current.setText(text)

    def _remove_app_argument(self) -> None:
        row = self._app_list.currentRow()
        if row >= 0:
            item = self._app_list.takeItem(row)
            del item

    def _move_app_argument(self, offset: int) -> None:
        row = self._app_list.currentRow()
        if row < 0:
            return
        new_row = row + offset
        if 0 <= new_row < self._app_list.count():
            item = self._app_list.takeItem(row)
            self._app_list.insertItem(new_row, item)
            self._app_list.setCurrentItem(item)

    def get_values(self) -> Tuple[List[Tuple[str, str]], List[str]]:
        properties: List[Tuple[str, str]] = []
        for row in range(self._jvm_table.rowCount()):
            key_item = self._jvm_table.item(row, 0)
            value_item = self._jvm_table.item(row, 1)
            key = key_item.text().strip() if key_item else ""
            value = value_item.text().strip() if value_item else ""
            if key:
                properties.append((key, value))
        arguments = [self._app_list.item(i).text() for i in range(self._app_list.count())]
        return properties, arguments
