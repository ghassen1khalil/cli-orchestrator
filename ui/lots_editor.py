from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QStyle,
)

from core.models import LotConfig


class LotEditorDialog(QDialog):
    def __init__(self, lot: Optional[LotConfig] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Éditer un lot")
        self.resize(500, 400)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Nom du lot (ex: Import clients)")
        self._name_edit.setClearButtonEnabled(True)
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Dossier contenant les bases")
        self._path_edit.setClearButtonEnabled(True)
        self._pattern_edit = QLineEdit("*.db")
        self._pattern_edit.setPlaceholderText("Pattern de fichiers (ex: *.db)")
        self._pattern_edit.setClearButtonEnabled(True)
        self._files_list = QListWidget()
        self._files_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._files_list.setAlternatingRowColors(True)

        form = QFormLayout()
        form.addRow("Nom", self._name_edit)

        method1_group = QGroupBox("Méthode 1 : Extraire automatiquement depuis un dossier")
        method1_layout = QFormLayout(method1_group)
        method1_info = QLabel(
            "Choisissez un dossier contenant vos bases SQLite et laissez l'application "
            "récupérer automatiquement tous les fichiers correspondant au pattern (par défaut *.db)."
        )
        method1_info.setWordWrap(True)
        method1_layout.addRow(method1_info)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self._path_edit)
        browse_btn = QPushButton("Choisir")
        browse_btn.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        browse_btn.setToolTip("Sélectionner le dossier contenant les bases")
        browse_btn.clicked.connect(self._choose_directory)
        path_layout.addWidget(browse_btn)
        method1_layout.addRow("Dossier", path_layout)

        pattern_label = QLabel("Pattern")
        pattern_label.setToolTip("Les fichiers trouvés dans le dossier seront filtrés avec ce pattern.")
        method1_layout.addRow(pattern_label, self._pattern_edit)

        files_group = QGroupBox("Méthode 2 : Ajouter manuellement des fichiers")
        files_layout = QVBoxLayout(files_group)
        files_info = QLabel(
            "Utilisez cette méthode si vous souhaitez sélectionner précisément les fichiers .db à inclure dans le lot."
            " Vous pouvez ajouter, retirer ou vider la liste selon vos besoins."
        )
        files_info.setWordWrap(True)
        files_layout.addWidget(files_info)
        files_layout.addWidget(QLabel("Lorsque la liste est vide, le pattern de la méthode 1 sera utilisé."))
        files_layout.addWidget(self._files_list)
        btn_bar = QHBoxLayout()
        add_files_btn = QPushButton("Ajouter fichiers")
        add_files_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        add_files_btn.setToolTip("Ajouter des fichiers spécifiques pour ce lot")
        remove_btn = QPushButton("Supprimer")
        remove_btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        remove_btn.setToolTip("Retirer le fichier sélectionné de la liste")
        clear_btn = QPushButton("Vider")
        clear_btn.setIcon(self.style().standardIcon(QStyle.SP_LineEditClearButton))
        clear_btn.setToolTip("Supprimer tous les fichiers sélectionnés")
        add_files_btn.clicked.connect(self._add_files)
        remove_btn.clicked.connect(self._remove_file)
        clear_btn.clicked.connect(self._clear_files)
        for btn in (add_files_btn, remove_btn, clear_btn):
            btn_bar.addWidget(btn)
        btn_bar.addStretch()
        files_layout.addLayout(btn_bar)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(method1_group)
        layout.addWidget(files_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if lot:
            self._name_edit.setText(lot.name)
            self._path_edit.setText(lot.databases_path)
            self._pattern_edit.setText(lot.pattern)
            for file in lot.files:
                QListWidgetItem(file, self._files_list)

    def _choose_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier", self._path_edit.text() or str(Path.home()))
        if directory:
            self._path_edit.setText(directory)

    def _add_files(self) -> None:
        directory = self._path_edit.text() or str(Path.home())
        files, _ = QFileDialog.getOpenFileNames(self, "Sélectionner des bases SQLite", directory, "SQLite (*.db *.sqlite);;Tous (*.*)")
        for file_path in files:
            if not self._contains_file(file_path):
                QListWidgetItem(file_path, self._files_list)

    def _remove_file(self) -> None:
        row = self._files_list.currentRow()
        if row >= 0:
            item = self._files_list.takeItem(row)
            del item

    def _clear_files(self) -> None:
        self._files_list.clear()

    def _contains_file(self, file_path: str) -> bool:
        return any(self._files_list.item(i).text() == file_path for i in range(self._files_list.count()))

    def _on_accept(self) -> None:
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            return
        has_path = bool(self._path_edit.text().strip())
        has_files = self._files_list.count() > 0
        if not has_path and has_files:
            first_file = Path(self._files_list.item(0).text()).expanduser()
            self._path_edit.setText(str(first_file.parent))
            has_path = True
        if not has_path:
            self._path_edit.setFocus()
            return
        self.accept()

    def get_lot(self) -> LotConfig:
        files = [self._files_list.item(i).text() for i in range(self._files_list.count())]
        return LotConfig(
            name=self._name_edit.text().strip(),
            databases_path=self._path_edit.text().strip(),
            pattern=self._pattern_edit.text().strip() or "*.db",
            files=files,
        )
