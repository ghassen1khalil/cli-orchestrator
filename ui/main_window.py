from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from PySide6.QtCore import Qt, QSize, QFileSystemWatcher
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from core.models import AppSettings, CommandArguments, ExecutionStatus, LotConfig
from core.orchestrator import Orchestrator
from app_io.settings import SettingsManager
from app_io.yaml_io import load_lots_from_yaml, save_lots_to_yaml
from ui.args_editor import ArgsEditorDialog
from ui.dashboard import DashboardWidget
from ui.env_editor import EnvEditorDialog
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

        self._env_watcher = QFileSystemWatcher(self)
        self._env_watcher.fileChanged.connect(self._on_env_fs_event)
        self._env_watcher.directoryChanged.connect(self._on_env_fs_event)
        self._env_last_known_exists = False
        self._env_prompted_for_current_env = False

        self._build_ui()
        self._configure_env_monitoring()
        self._update_mode_button()
        self._refresh_lots_table()
        self._sync_env_state(offer_if_available=True)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(18)

        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 12, 12, 12)
        header_layout.setSpacing(8)

        title_label = QLabel("Configurez votre orchestration en quelques clics")
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        header_layout.addWidget(title_label)

        self._jar_label = QLabel(self._format_jar_label())
        self._jar_label.setWordWrap(True)
        header_layout.addWidget(self._jar_label)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        choose_jar_btn = QPushButton("Choisir .jar")
        choose_jar_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        choose_jar_btn.setToolTip("Sélectionner le fichier jar à exécuter")
        choose_jar_btn.clicked.connect(self._choose_jar)
        buttons_layout.addWidget(choose_jar_btn)

        self._env_button = QPushButton("Gérer .env")
        self._env_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        self._env_button.setToolTip("Consulter ou modifier le fichier .env associé")
        self._env_button.clicked.connect(self._open_env_file)
        buttons_layout.addWidget(self._env_button)

        args_button = QPushButton("Arguments JVM & App")
        args_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        args_button.setToolTip("Modifier les paramètres JVM et les arguments de l'application")
        args_button.clicked.connect(self._edit_arguments)
        buttons_layout.addWidget(args_button)

        load_yaml_btn = QPushButton("Charger YAML")
        load_yaml_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        load_yaml_btn.setToolTip("Importer une configuration enregistrée")
        load_yaml_btn.clicked.connect(self._load_yaml)
        buttons_layout.addWidget(load_yaml_btn)

        save_yaml_btn = QPushButton("Enregistrer YAML")
        save_yaml_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        save_yaml_btn.setToolTip("Sauvegarder la configuration actuelle")
        save_yaml_btn.clicked.connect(self._save_yaml)
        buttons_layout.addWidget(save_yaml_btn)

        self._mode_button = QPushButton()
        self._mode_button.setCheckable(True)
        self._mode_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self._mode_button.setToolTip("Basculer entre l'exécution automatique et manuelle des lots")
        self._mode_button.clicked.connect(self._toggle_mode)
        buttons_layout.addWidget(self._mode_button)

        buttons_layout.addStretch()

        self._start_button = QPushButton("Démarrer")
        self._start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self._start_button.setIconSize(QSize(28, 28))
        self._start_button.setToolTip("Lancer l'orchestration avec les paramètres actuels")
        self._start_button.clicked.connect(self._start_execution)
        buttons_layout.addWidget(self._start_button)

        self._stop_button = QPushButton("Arrêter")
        self._stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self._stop_button.setIconSize(QSize(28, 28))
        self._stop_button.setToolTip("Arrêter tous les traitements en cours")
        self._stop_button.clicked.connect(self._stop_execution)
        self._stop_button.setEnabled(False)
        buttons_layout.addWidget(self._stop_button)

        header_layout.addLayout(buttons_layout)
        root_layout.addWidget(header_frame)

        self._dashboard = DashboardWidget()
        self._lots_table = self._dashboard.table_widget()

        lot_buttons_layout = QHBoxLayout()
        lot_buttons_layout.setSpacing(6)

        add_lot_btn = QPushButton("Ajouter")
        add_lot_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        add_lot_btn.setToolTip("Créer un nouveau lot")
        add_lot_btn.clicked.connect(self._add_lot)

        edit_lot_btn = QPushButton("Éditer")
        edit_lot_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        edit_lot_btn.setToolTip("Modifier le lot sélectionné")
        edit_lot_btn.clicked.connect(self._edit_lot)

        remove_lot_btn = QPushButton("Supprimer")
        remove_lot_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogDiscardButton))
        remove_lot_btn.setToolTip("Retirer le lot sélectionné")
        remove_lot_btn.clicked.connect(self._remove_lot)

        up_btn = QPushButton("Monter")
        up_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        up_btn.setToolTip("Monter le lot dans la liste")
        up_btn.clicked.connect(lambda: self._move_lot(-1))

        down_btn = QPushButton("Descendre")
        down_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        down_btn.setToolTip("Descendre le lot dans la liste")
        down_btn.clicked.connect(lambda: self._move_lot(1))

        for btn in (add_lot_btn, edit_lot_btn, remove_lot_btn, up_btn, down_btn):
            lot_buttons_layout.addWidget(btn)
        lot_buttons_layout.addStretch()

        overview_container = QFrame()
        overview_container.setFrameShape(QFrame.StyledPanel)
        overview_layout = QVBoxLayout(overview_container)
        overview_layout.setContentsMargins(12, 12, 12, 12)
        overview_layout.setSpacing(8)
        overview_layout.addWidget(self._dashboard)
        overview_layout.addLayout(lot_buttons_layout)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(overview_container)

        self._run_tabs = RunTabsWidget()
        self._run_tabs.stop_requested.connect(self._stop_single_task)
        splitter.addWidget(self._run_tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        root_layout.addWidget(splitter, stretch=1)

        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(12, 8, 12, 8)
        status_layout.setSpacing(10)
        status_frame.setFrameShape(QFrame.StyledPanel)

        self._status_icon = QLabel()
        status_layout.addWidget(self._status_icon)

        self._status_label = QLabel()
        self._status_label.setObjectName("statusLabel")
        self._status_label.setStyleSheet("font-weight: 500;")
        status_layout.addWidget(self._status_label)
        status_layout.addStretch()

        root_layout.addWidget(status_frame)

        self._update_status("Prêt", QStyle.SP_MessageBoxInformation)

    def _format_jar_label(self) -> str:
        return f"Jar sélectionné : {self._jar_path or 'Aucun'}"

    def _update_status(self, message: str, icon: QStyle.StandardPixmap = QStyle.SP_MessageBoxInformation) -> None:
        self._status_label.setText(message)
        self._status_icon.setPixmap(self.style().standardIcon(icon).pixmap(20, 20))

    def _update_mode_button(self) -> None:
        self._mode_button.setChecked(self._auto_mode)
        if self._auto_mode:
            self._mode_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
            self._mode_button.setText("Mode Auto")
        else:
            self._mode_button.setIcon(self.style().standardIcon(QStyle.SP_CommandLink))
            self._mode_button.setText("Mode Manuel")

    def _choose_jar(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir le jar",
            self._jar_path or str(Path.home()),
            "Java Archive (*.jar)",
        )
        if path:
            self._jar_path = path
            self._jar_label.setText(self._format_jar_label())
            self._settings_manager.save_jar_path(path)
            self._env_prompted_for_current_env = False
            self._configure_env_monitoring()
            self._sync_env_state(warn_if_missing=True, offer_if_available=True)
            self._update_status("Jar mis à jour", QStyle.SP_DialogApplyButton)

    def _configure_env_monitoring(self) -> None:
        for existing in list(self._env_watcher.files()):
            self._env_watcher.removePath(existing)
        for existing in list(self._env_watcher.directories()):
            self._env_watcher.removePath(existing)
        env_path = self._current_env_path()
        if not env_path:
            self._env_last_known_exists = False
            return
        if env_path.parent.exists():
            self._env_watcher.addPath(str(env_path.parent))
        if env_path.exists():
            self._env_watcher.addPath(str(env_path))
            self._env_last_known_exists = True
        else:
            self._env_last_known_exists = False

    def _sync_env_state(self, warn_if_missing: bool = False, offer_if_available: bool = False) -> None:
        env_path = self._current_env_path()
        has_jar = env_path is not None
        env_exists = env_path.exists() if env_path else False
        previous_exists = self._env_last_known_exists
        self._env_button.setEnabled(has_jar)
        if env_path and env_path.parent.exists():
            self._ensure_env_directory_watched(env_path.parent)
        if env_exists:
            self._ensure_env_file_watched(env_path)
            if offer_if_available and (not self._env_prompted_for_current_env or not previous_exists):
                self._prompt_open_env(env_path)
        else:
            if warn_if_missing:
                QMessageBox.warning(
                    self,
                    "Fichier .env manquant",
                    "Aucun fichier .env n'a été trouvé dans le même dossier que le jar sélectionné.",
                )
            self._env_prompted_for_current_env = False
        self._env_last_known_exists = env_exists

    def _ensure_env_directory_watched(self, directory: Path) -> None:
        dir_path = str(directory)
        if dir_path not in self._env_watcher.directories():
            self._env_watcher.addPath(dir_path)

    def _ensure_env_file_watched(self, env_path: Path) -> None:
        path_str = str(env_path)
        if path_str not in self._env_watcher.files() and env_path.exists():
            self._env_watcher.addPath(path_str)

    def _current_env_path(self) -> Path | None:
        if not self._jar_path:
            return None
        try:
            return Path(self._jar_path).parent / ".env"
        except Exception:
            return None

    def _prompt_open_env(self, env_path: Path) -> None:
        self._env_prompted_for_current_env = True
        reply = QMessageBox.question(
            self,
            "Fichier .env détecté",
            "Un fichier .env a été détecté. Souhaitez-vous le consulter ou l'éditer ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self._open_env_file()

    def _open_env_file(self) -> None:
        env_path = self._current_env_path()
        if not env_path:
            QMessageBox.warning(self, "Jar manquant", "Veuillez sélectionner un fichier jar avant d'éditer le .env.")
            return
        entries: List[Tuple[str, str]]
        if env_path.exists():
            try:
                entries = self._read_env_file(env_path)
            except Exception as exc:  # pragma: no cover
                QMessageBox.critical(self, "Erreur", f"Impossible de lire le fichier .env : {exc}")
                return
        else:
            create = QMessageBox.question(
                self,
                "Créer .env",
                "Le fichier .env est introuvable. Souhaitez-vous le créer maintenant ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if create != QMessageBox.Yes:
                return
            entries = []
        dialog = EnvEditorDialog(entries, self)
        if dialog.exec() == QDialog.Accepted:
            new_entries = dialog.get_entries()
            try:
                self._write_env_file(env_path, new_entries)
            except Exception as exc:  # pragma: no cover
                QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer le fichier .env : {exc}")
                return
            self._update_status(".env mis à jour", QStyle.SP_DialogApplyButton)
            self._ensure_env_file_watched(env_path)
            self._env_last_known_exists = True
            self._env_prompted_for_current_env = True

    def _read_env_file(self, env_path: Path) -> List[Tuple[str, str]]:
        entries: List[Tuple[str, str]] = []
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
            else:
                key, value = line, ""
            entries.append((key.strip(), value.strip()))
        return entries

    def _write_env_file(self, env_path: Path, entries: List[Tuple[str, str]]) -> None:
        lines = [f"{key}={value}" for key, value in entries]
        text = "\n".join(lines)
        if lines:
            text += "\n"
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(text, encoding="utf-8")

    def _on_env_fs_event(self, _path: str) -> None:
        previous_exists = self._env_last_known_exists
        self._sync_env_state(offer_if_available=not previous_exists)
        if not self._env_last_known_exists:
            self._env_prompted_for_current_env = False

    def _edit_arguments(self) -> None:
        dialog = ArgsEditorDialog(self._command_args.jvm_properties, self._command_args.app_arguments, self)
        if dialog.exec() == QDialog.Accepted:
            jvm_props, app_args = dialog.get_values()
            self._command_args.jvm_properties = jvm_props
            self._command_args.app_arguments = app_args
            self._settings_manager.save_jvm_properties(jvm_props)
            self._settings_manager.save_app_arguments(app_args)

    def _load_yaml(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Charger configuration YAML",
            str(Path.home()),
            "YAML (*.yaml *.yml)",
        )
        if path:
            try:
                lots = load_lots_from_yaml(path)
            except Exception as exc:  # pragma: no cover
                QMessageBox.critical(self, "Erreur", f"Impossible de charger le fichier : {exc}")
                return
            self._lots = lots
            self._refresh_lots_table()
            self._update_status("Configuration chargée", QStyle.SP_DialogApplyButton)

    def _save_yaml(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer configuration",
            str(Path.home()),
            "YAML (*.yaml *.yml)",
        )
        if path:
            save_lots_to_yaml(path, self._lots)
            QMessageBox.information(self, "Enregistré", "Configuration sauvegardée")
            self._update_status("Configuration enregistrée", QStyle.SP_DialogSaveButton)

    def _add_lot(self) -> None:
        dialog = LotEditorDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._lots.append(dialog.get_lot())
            self._refresh_lots_table()
            self._update_status("Lot ajouté", QStyle.SP_FileDialogNewFolder)

    def _edit_lot(self) -> None:
        row = self._lots_table.currentRow()
        if row < 0 or row >= len(self._lots):
            return
        dialog = LotEditorDialog(self._lots[row], self)
        if dialog.exec() == QDialog.Accepted:
            self._lots[row] = dialog.get_lot()
            self._refresh_lots_table()
            self._update_status("Lot mis à jour", QStyle.SP_FileDialogContentsView)

    def _remove_lot(self) -> None:
        row = self._lots_table.currentRow()
        if row >= 0 and row < len(self._lots):
            self._lots.pop(row)
            self._refresh_lots_table()
            self._update_status("Lot supprimé", QStyle.SP_DialogDiscardButton)

    def _move_lot(self, offset: int) -> None:
        row = self._lots_table.currentRow()
        if row < 0:
            return
        new_row = row + offset
        if 0 <= new_row < len(self._lots):
            self._lots[row], self._lots[new_row] = self._lots[new_row], self._lots[row]
            self._refresh_lots_table()
            self._lots_table.selectRow(new_row)
            self._update_status("Ordre mis à jour", QStyle.SP_ArrowUp if offset < 0 else QStyle.SP_ArrowDown)

    def _refresh_lots_table(self) -> None:
        previous_row = self._lots_table.currentRow()
        self._dashboard.set_lots(self._lots)
        if 0 <= previous_row < len(self._lots):
            self._lots_table.selectRow(previous_row)

    def _toggle_mode(self) -> None:
        self._auto_mode = not self._auto_mode
        self._settings_manager.save_auto_mode(self._auto_mode)
        self._update_mode_button()
        self._update_status(
            "Mode mis à jour",
            QStyle.SP_BrowserReload if self._auto_mode else QStyle.SP_CommandLink,
        )

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
        self._run_tabs.reset()
        self._dashboard.prepare_for_run()
        self._start_button.setEnabled(False)
        self._stop_button.setEnabled(True)
        self._update_status("Initialisation...", QStyle.SP_BrowserReload)
        self._orchestrator.start(settings)

    def _stop_execution(self) -> None:
        self._orchestrator.stop_all()
        self._update_status("Arrêt demandé", QStyle.SP_MediaStop)

    def _stop_single_task(self, task) -> None:
        self._orchestrator.stop_task(task)

    def _on_lot_started(self, lot: LotConfig) -> None:
        self._update_status(f"Lot en cours : {lot.name}", QStyle.SP_MediaPlay)
        self._run_tabs.mark_lot_started(lot.name)
        self._dashboard.mark_lot_started(lot)

    def _on_lot_finished(self, lot: LotConfig) -> None:
        self._update_status(f"Lot terminé : {lot.name}", QStyle.SP_DialogApplyButton)
        self._run_tabs.mark_lot_finished(lot.name)
        self._dashboard.mark_lot_finished(lot)

    def _on_lot_skipped(self, lot: LotConfig, reason: str) -> None:
        QMessageBox.information(self, "Lot ignoré", f"{lot.name} : {reason}")
        self._run_tabs.mark_lot_skipped(lot.name, reason)
        self._dashboard.mark_lot_skipped(lot, reason)

    def _on_task_started(self, task, command: str) -> None:
        self._run_tabs.start_task(task, command)
        self._dashboard.mark_task_started(task)

    def _on_task_output(self, task, text: str, is_error: bool) -> None:
        self._run_tabs.append_output(task, text, is_error)

    def _on_task_finished(self, task, status: ExecutionStatus, exit_code: int) -> None:
        self._run_tabs.finish_task(task, status)
        self._dashboard.mark_task_finished(task, status)

    def _on_task_error(self, task, message: str) -> None:
        QMessageBox.critical(self, "Erreur", f"{task.display_name()} : {message}")

    def _on_all_finished(self) -> None:
        self._start_button.setEnabled(True)
        self._stop_button.setEnabled(False)
        self._update_status("Prêt", QStyle.SP_MessageBoxInformation)
        self._dashboard.mark_run_completed()

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
        self._update_status("Prêt", QStyle.SP_MessageBoxWarning)


def create_app() -> QApplication:
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    return app
