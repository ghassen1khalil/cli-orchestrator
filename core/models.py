from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


class ExecutionStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    STOPPED = auto()


@dataclass
class LotConfig:
    name: str
    databases_path: str
    pattern: str = "*.db"
    files: List[str] = field(default_factory=list)

    def iter_databases(self) -> List[Path]:
        base_path = Path(self.databases_path).expanduser()
        if self.files:
            return [Path(f).expanduser() for f in self.files]
        if not base_path.exists():
            return []
        return sorted(base_path.glob(self.pattern))

    def to_dict(self) -> dict:
        data = {
            "name": self.name,
            "databases_path": self.databases_path,
            "pattern": self.pattern,
        }
        if self.files:
            data["files"] = self.files
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "LotConfig":
        return cls(
            name=data.get("name", ""),
            databases_path=data.get("databases_path", ""),
            pattern=data.get("pattern", "*.db"),
            files=data.get("files", []) or [],
        )


@dataclass
class CommandArguments:
    jvm_properties: List[Tuple[str, str]] = field(default_factory=list)
    app_arguments: List[str] = field(default_factory=list)

    def build_jvm_args(self, db_path: Path) -> List[str]:
        args = []
        datasource_key = "spring.datasource.url"
        for key, value in self.jvm_properties:
            if key.strip():
                if value is None:
                    value = ""
                if key.strip() == datasource_key:
                    value = f"jdbc:sqlite:{db_path}"
                args.append(f"-D{key.strip()}={value}")
        if not any(k == datasource_key for k, _ in self.jvm_properties):
            args.append(f"-D{datasource_key}=jdbc:sqlite:{db_path}")
        return args

    def to_dict(self) -> dict:
        return {
            "jvm_properties": [{"key": k, "value": v} for k, v in self.jvm_properties],
            "app_arguments": list(self.app_arguments),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CommandArguments":
        jvm_props = [(item.get("key", ""), item.get("value", "")) for item in data.get("jvm_properties", [])]
        app_args = list(data.get("app_arguments", []))
        return cls(jvm_properties=jvm_props, app_arguments=app_args)


@dataclass
class AppSettings:
    jar_path: str = ""
    lots: List[LotConfig] = field(default_factory=list)
    command_args: CommandArguments = field(default_factory=CommandArguments)
    auto_mode: bool = True


@dataclass
class DatabaseTask:
    lot: LotConfig
    database: Path

    def id(self) -> str:
        return f"{self.lot.name}:{self.database}"

    def display_name(self) -> str:
        return self.database.name

    def __hash__(self) -> int:
        return hash((self.lot.name, str(self.database)))
