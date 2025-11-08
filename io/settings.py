from __future__ import annotations

from typing import List, Tuple

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

    def load_auto_mode(self) -> bool:
        return self._settings.value("auto_mode", True, type=bool)

    def save_auto_mode(self, value: bool) -> None:
        self._settings.setValue("auto_mode", value)

    def load_jvm_properties(self) -> List[Tuple[str, str]]:
        stored = self._settings.value("jvm_properties", [])
        if not isinstance(stored, list):
            return []
        result: List[Tuple[str, str]] = []
        for item in stored:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                result.append((str(item[0]), str(item[1])))
            elif isinstance(item, dict) and "key" in item:
                result.append((str(item.get("key", "")), str(item.get("value", ""))))
        return result

    def save_jvm_properties(self, properties: List[Tuple[str, str]]) -> None:
        self._settings.setValue("jvm_properties", list(properties))

    def load_app_arguments(self) -> List[str]:
        stored = self._settings.value("app_arguments", [])
        if isinstance(stored, list):
            return [str(item) for item in stored]
        return []

    def save_app_arguments(self, args: List[str]) -> None:
        self._settings.setValue("app_arguments", list(args))
