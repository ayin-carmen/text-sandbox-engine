"""JSON persistence for world state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_world_state(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def save_world_state(path: str | Path, state: dict[str, Any]) -> None:
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)
        file.write("\n")
