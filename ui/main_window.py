from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.models import AppSettings, CommandArguments, ExecutionStatus, LotConfig
from core.orchestrator import Orchestrator
from app_io.settings import SettingsManager
from app_io.yaml_io import load_lots_from_yaml, save_lots_to_yaml
from ui.args_editor import ArgsEditorDialog
from ui.lots_editor import LotEditorDialog
from ui.run_tabs import RunTabsWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Orchestrateur FSADA")
        self.resize(1200, 800)

        self._settings_manager = SettingsManager()
        self._orchestrator = Orchestrator()
        self._orchestrator.lot_started.connect(self._on_lot_started)
        self._orchestrator.lot_finished.connect(self._on_lot_finished)
        self._orchestrator.lot_skipped.connect(self._on_lot_skipped)
        self._orchestrator.task_started.connect(self._on_task_started)
        self._orchestrator.task_output.connect(self._on_task_output)
        self._orchestrator.task_finished.connect(self._on_task_finished)
        self._orchestrator.task_error.connect(self._on_task_error)
        self._orchestrator.all_finished.connect(self._on_all_finished)
        self._orchestrator.request_lot_confirmation.connect(self._on_request_confirmation)
        self._orchestrator.startup_error.connect(self._on_startup_error)

        self._jar_path = self._settings_manager.load_jar_path()
        jvm_props = self._settings_manager.load_jvm_properties()
        app_args = self._settings_manager.load_app_arguments()
        self._command_args = CommandArguments(jvm_props, app_args)
        self._lots: List[LotConfig] = []
        self._auto_mode = self._settings_manager.load_auto_mode()

        self._build_ui()
        self._update_mode_button()
        self._refresh_lots_table()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        self._jar_label = QLabel(self._format_jar_label())
        choose_jar_btn = QPushButton("Choisir .jar")
        choose_jar_btn.clicked.connect(self._choose_jar)

        args_button = QPushButton("Arguments JVM & App")
        args_button.clicked.connect(self._edit_arguments)

        load_yaml_btn = QPushButton("Charger YAML")
        load_yaml_btn.clicked.connect(self._load_yaml)
        save_yaml_btn = QPushButton("Enregistrer YAML")
        save_yaml_btn.clicked.connect(self._save_yaml)

        self._mode_button = QPushButton()
        self._mode_button.setCheckable(True)
        self._mode_button.clicked.connect(self._toggle_mode)

        self._start_button = QPushButton("Démarrer orchestration")
        self._start_button.clicked.connect(self._start_execution)
        self._stop_button = QPushButton("Arrêter tout")
        self._stop_button.clicked.connect(self._stop_execution)
        self._stop_button.setEnabled(False)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self._jar_label, stretch=1)
        top_layout.addWidget(choose_jar_btn)
        top_layout.addWidget(args_button)
        top_layout.addWidget(load_yaml_btn)
        top_layout.addWidget(save_yaml_btn)
        top_layout.addWidget(self._mode_button)
        top_layout.addWidget(self._start_button)
        top_layout.addWidget(self._stop_button)
        root_layout.addLayout(top_layout)

        self._lots_table = QTableWidget(0, 4)
        self._lots_table.setHorizontalHeaderLabels(["Nom", "Dossier", "Pattern", "Fichiers"])
        self._lots_table.horizontalHeader().setStretchLastSection(True)
        self._lots_table.verticalHeader().setVisible(False)
        self._lots_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._lots_table.setSelectionMode(QTableWidget.SingleSelection)

        lot_buttons_layout = QHBoxLayout()
        add_lot_btn = QPushButton("Ajouter")
        edit_lot_btn = QPushButton("Éditer")
        remove_lot_btn = QPushButton("Supprimer")
        up_btn = QPushButton("Monter")
        down_btn = QPushButton("Descendre")
        add_lot_btn.clicked.connect(self._add_lot)
        edit_lot_btn.clicked.connect(self._edit_lot)
        remove_lot_btn.clicked.connect(self._remove_lot)
        up_btn.clicked.connect(lambda: self._move_lot(-1))
        down_btn.clicked.connect(lambda: self._move_lot(1))
        for btn in (add_lot_btn, edit_lot_btn, remove_lot_btn, up_btn, down_btn):
            lot_buttons_layout.addWidget(btn)
        lot_buttons_layout.addStretch()

        root_layout.addWidget(self._lots_table)
        root_layout.addLayout(lot_buttons_layout)

        self._status_label = QLabel("Prêt")
        root_layout.addWidget(self._status_label)

        self._run_tabs = RunTabsWidget()
        self._run_tabs.stop_requested.connect(self._stop_single_task)
        root_layout.addWidget(self._run_tabs, stretch=1)

    def _format_jar_label(self) -> str:
        return f"Jar sélectionné : {self._jar_path or 'Aucun'}"

    def _update_mode_button(self) -> None:
        self._mode_button.setChecked(self._auto_mode)
        self._mode_button.setText("Mode Auto" if self._auto_mode else "Mode Manuel")

    def _choose_jar(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choisir le jar", self._jar_path or str(Path.home()), "Java Archive (*.jar)")
        if path:
            self._jar_path = path
            self._jar_label.setText(self._format_jar_label())
            self._settings_manager.save_jar_path(path)

    def _edit_arguments(self) -> None:
        dialog = ArgsEditorDialog(self._command_args.jvm_properties, self._command_args.app_arguments, self)
        if dialog.exec() == QDialog.Accepted:
            jvm_props, app_args = dialog.get_values()
            self._command_args.jvm_properties = jvm_props
            self._command_args.app_arguments = app_args
            self._settings_manager.save_jvm_properties(jvm_props)
            self._settings_manager.save_app_arguments(app_args)

    def _load_yaml(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Charger configuration YAML", str(Path.home()), "YAML (*.yaml *.yml)")
        if path:
            try:
                lots = load_lots_from_yaml(path)
            except Exception as exc:  # pragma: no cover
                QMessageBox.critical(self, "Erreur", f"Impossible de charger le fichier : {exc}")
                return
            self._lots = lots
            self._refresh_lots_table()

    def _save_yaml(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer configuration", str(Path.home()), "YAML (*.yaml *.yml)")
        if path:
            save_lots_to_yaml(path, self._lots)
            QMessageBox.information(self, "Enregistré", "Configuration sauvegardée")

    def _add_lot(self) -> None:
        dialog = LotEditorDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._lots.append(dialog.get_lot())
            self._refresh_lots_table()

    def _edit_lot(self) -> None:
        row = self._lots_table.currentRow()
        if row < 0 or row >= len(self._lots):
            return
        dialog = LotEditorDialog(self._lots[row], self)
        if dialog.exec() == QDialog.Accepted:
            self._lots[row] = dialog.get_lot()
            self._refresh_lots_table()

    def _remove_lot(self) -> None:
        row = self._lots_table.currentRow()
        if row >= 0 and row < len(self._lots):
            self._lots.pop(row)
            self._refresh_lots_table()

    def _move_lot(self, offset: int) -> None:
        row = self._lots_table.currentRow()
        if row < 0:
            return
        new_row = row + offset
        if 0 <= new_row < len(self._lots):
            self._lots[row], self._lots[new_row] = self._lots[new_row], self._lots[row]
            self._refresh_lots_table()
            self._lots_table.selectRow(new_row)

    def _refresh_lots_table(self) -> None:
        self._lots_table.setRowCount(len(self._lots))
        for row, lot in enumerate(self._lots):
            self._lots_table.setItem(row, 0, QTableWidgetItem(lot.name))
            self._lots_table.setItem(row, 1, QTableWidgetItem(lot.databases_path))
            self._lots_table.setItem(row, 2, QTableWidgetItem(lot.pattern))
            resolved_files = lot.iter_databases()
            if resolved_files:
                files_text = "\n".join(str(path) for path in resolved_files)
            else:
                files_text = "Aucun fichier trouvé"
            files_item = QTableWidgetItem(files_text)
            files_item.setFlags(files_item.flags() & ~Qt.ItemIsEditable)
            self._lots_table.setItem(row, 3, files_item)
        self._lots_table.resizeColumnsToContents()
        self._lots_table.resizeRowsToContents()

    def _toggle_mode(self) -> None:
        self._auto_mode = not self._auto_mode
        self._settings_manager.save_auto_mode(self._auto_mode)
        self._update_mode_button()

    def _start_execution(self) -> None:
        if not self._jar_path:
            QMessageBox.warning(self, "Jar manquant", "Veuillez sélectionner un fichier jar")
            return
        if not self._lots:
            QMessageBox.warning(self, "Aucun lot", "Veuillez configurer au moins un lot")
            return
        settings = AppSettings(
            jar_path=self._jar_path,
            lots=list(self._lots),
            command_args=self._command_args,
            auto_mode=self._auto_mode,
        )
        self._run_tabs.clear_tasks()
        self._start_button.setEnabled(False)
        self._stop_button.setEnabled(True)
        self._status_label.setText("Initialisation...")
        self._orchestrator.start(settings)

    def _stop_execution(self) -> None:
        self._orchestrator.stop_all()

    def _stop_single_task(self, task) -> None:
        self._orchestrator.stop_task(task)

    def _on_lot_started(self, lot: LotConfig) -> None:
        self._status_label.setText(f"Lot en cours : {lot.name}")
        self._run_tabs.clear_tasks()

    def _on_lot_finished(self, lot: LotConfig) -> None:
        self._status_label.setText(f"Lot terminé : {lot.name}")

    def _on_lot_skipped(self, lot: LotConfig, reason: str) -> None:
        QMessageBox.information(self, "Lot ignoré", f"{lot.name} : {reason}")

    def _on_task_started(self, task, command: str) -> None:
        self._run_tabs.start_task(task, command)

    def _on_task_output(self, task, text: str, is_error: bool) -> None:
        self._run_tabs.append_output(task, text, is_error)

    def _on_task_finished(self, task, status: ExecutionStatus, exit_code: int) -> None:
        self._run_tabs.finish_task(task, status)

    def _on_task_error(self, task, message: str) -> None:
        QMessageBox.critical(self, "Erreur", f"{task.display_name()} : {message}")

    def _on_all_finished(self) -> None:
        self._start_button.setEnabled(True)
        self._stop_button.setEnabled(False)
        self._status_label.setText("Prêt")

    def _on_request_confirmation(self, lot: LotConfig) -> None:
        reply = QMessageBox.question(self, "Continuer", f"Passer au lot suivant après {lot.name} ?")
        if reply == QMessageBox.Yes:
            self._orchestrator.continue_to_next_lot()
        else:
            self._orchestrator.stop_all()

    def _on_startup_error(self, message: str) -> None:
        QMessageBox.critical(self, "Erreur", message)
        self._start_button.setEnabled(True)
        self._stop_button.setEnabled(False)
        self._status_label.setText("Prêt")


def create_app() -> QApplication:
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    return app
