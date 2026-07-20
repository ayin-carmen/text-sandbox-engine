"""Helpers that format runtime diagnostics."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from .models import CommandResult, CommandTrace


def to_plain_data(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_plain_data(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {key: to_plain_data(item) for key, item in value.items()}
    return value


def command_trace_report(result: CommandResult) -> dict[str, Any]:
    return to_plain_data(result.trace)


def changed_by(trace: CommandTrace, path: str) -> list[dict[str, Any]]:
    matches = []
    for change in trace.changeset.changes:
        path_text = ".".join(change.path)
        if path_text == path:
            matches.append(
                {
                    "command_id": trace.command_id,
                    "command_type": trace.command.type,
                    "path": path_text,
                    "before": change.before,
                    "after": change.after,
                }
            )
    return matches


def state_diff(before: Any, after: Any) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    _diff_value([], before, after, changes)
    return {"changes": changes}


def _diff_value(path: list[str], before: Any, after: Any, changes: list[dict[str, Any]]) -> None:
    if isinstance(before, dict) and isinstance(after, dict):
        keys = sorted(set(before) | set(after))
        for key in keys:
            next_path = path + [str(key)]
            if key not in before:
                changes.append(
                    {
                        "path": ".".join(next_path),
                        "status": "added",
                        "before": None,
                        "after": after[key],
                    }
                )
            elif key not in after:
                changes.append(
                    {
                        "path": ".".join(next_path),
                        "status": "removed",
                        "before": before[key],
                        "after": None,
                    }
                )
            else:
                _diff_value(next_path, before[key], after[key], changes)
        return

    if isinstance(before, list) and isinstance(after, list):
        max_length = max(len(before), len(after))
        for index in range(max_length):
            next_path = path + [str(index)]
            if index >= len(before):
                changes.append(
                    {
                        "path": ".".join(next_path),
                        "status": "added",
                        "before": None,
                        "after": after[index],
                    }
                )
            elif index >= len(after):
                changes.append(
                    {
                        "path": ".".join(next_path),
                        "status": "removed",
                        "before": before[index],
                        "after": None,
                    }
                )
            else:
                _diff_value(next_path, before[index], after[index], changes)
        return

    if before != after:
        changes.append(
            {
                "path": ".".join(path),
                "status": "changed",
                "before": before,
                "after": after,
            }
        )
