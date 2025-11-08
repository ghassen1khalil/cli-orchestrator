from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import yaml

from core.models import CommandArguments, LotConfig


def load_lots_from_yaml(path: str) -> List[LotConfig]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(path)
    with file_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    lots_data = data.get("Lots", [])
    return [LotConfig.from_dict(item) for item in lots_data]


def save_lots_to_yaml(path: str, lots: Iterable[LotConfig]) -> None:
    file_path = Path(path)
    payload = {"Lots": [lot.to_dict() for lot in lots]}
    with file_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)
