"""Transactional state changes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Sequence

from .models import Change, ChangeSet
from .state import _read_path, _write_path

_MISSING = object()


class Transaction:
    def __init__(self, base_state: dict[str, Any]) -> None:
        self._working_state = deepcopy(base_state)
        self._changes: list[Change] = []
        self._effect_boundary = 0

    def mark_effect_boundary(self) -> None:
        self._effect_boundary = len(self._changes)

    def read_value(self, path: Sequence[str], default: Any = _MISSING) -> Any:
        try:
            return deepcopy(_read_path(self._working_state, path))
        except KeyError:
            if default is _MISSING:
                raise
            return deepcopy(default)

    def set_value(self, path: Sequence[str], value: Any) -> None:
        before = self.read_value(path, default=None)
        after = deepcopy(value)
        _write_path(self._working_state, path, after)
        self._changes.append(Change(list(path), before, after))

    def changes_since_last_effect(self) -> list[Change]:
        return list(self._changes[self._effect_boundary:])

    def changeset(self) -> ChangeSet:
        return ChangeSet(list(self._changes))
