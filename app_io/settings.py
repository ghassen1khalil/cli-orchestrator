from __future__ import annotations

from PySide6.QtCore import QSettings


class SettingsManager:
    ORGANIZATION = "cli-orchestrator"
    APPLICATION = "fsada"

    def __init__(self) -> None:
        self._settings = QSettings(self.ORGANIZATION, self.APPLICATION)

    def load_jar_path(self) -> str:
        return self._settings.value("jar_path", "")

    def save_jar_path(self, path: str) -> None:
        self._settings.setValue("jar_path", path)

    def clear_jar_path(self) -> None:
        self._settings.remove("jar_path")

    def load_auto_mode(self) -> bool:
        return self._settings.value("auto_mode", True, type=bool)

    def save_auto_mode(self, value: bool) -> None:
        self._settings.setValue("auto_mode", value)

