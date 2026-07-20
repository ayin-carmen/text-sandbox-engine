"""World state storage."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Sequence

from .models import ChangeSet


class StateStore:
    def __init__(self, world_state: dict[str, Any]) -> None:
        self._state = deepcopy(world_state)

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._state)

    def get_entity(self, entity_id: str) -> dict[str, Any]:
        return deepcopy(self._state["entities"][entity_id])

    def read_value(self, path: Sequence[str]) -> Any:
        return deepcopy(_read_path(self._state, path))

    def set_value(self, path: Sequence[str], value: Any) -> None:
        _write_path(self._state, path, value)

    def apply_changeset(self, changeset: ChangeSet) -> None:
        for change in changeset.changes:
            _write_path(self._state, change.path, change.after)


def _read_path(root: dict[str, Any], path: Sequence[str]) -> Any:
    node: Any = root
    for part in path:
        node = node[part]
    return node


def _write_path(root: dict[str, Any], path: Sequence[str], value: Any) -> None:
    if not path:
        raise ValueError("path cannot be empty")

    node: Any = root
    for part in path[:-1]:
        if part not in node or not isinstance(node[part], dict):
            node[part] = {}
        node = node[part]
    node[path[-1]] = deepcopy(value)
