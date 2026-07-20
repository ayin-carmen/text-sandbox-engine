"""Developer diagnostics for replay, scene reports, and state diffs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .builtins import register_builtins
from .content import ContentRepository
from .diagnostics import changed_by, command_trace_report, state_diff, to_plain_data
from .models import Command
from .persistence import load_world_state
from .registry import Registry
from .runtime import Runtime
from .scene import SceneOrchestrator


def validate_content(content_path: str | Path) -> dict[str, Any]:
    registry = Registry()
    register_builtins(registry)
    repository = ContentRepository.from_path(content_path)
    report = repository.validate(registry=registry)
    return {
        "passed": report.passed,
        "issues": to_plain_data(report.issues),
        "scene_count": len(repository.all_scenes()),
    }


def replay_commands(
    state_path: str | Path,
    commands_path: str | Path,
    content_path: str | Path | None = None,
) -> dict[str, Any]:
    initial_runtime = Runtime.from_file(state_path, content_path=content_path)
    before = initial_runtime.snapshot()
    runtime = Runtime.from_file(state_path, content_path=content_path)
    traces = []

    for command_data in _load_commands(commands_path):
        result = runtime.execute(command_data)
        traces.append(command_trace_report(result))
        if result.status == "failed":
            break

    after = runtime.snapshot()
    return {
        "status": traces[-1]["status"] if traces else "succeeded",
        "command_count": len(traces),
        "traces": traces,
        "state_diff": state_diff(before, after),
        "final_state": after,
    }


def scene_candidate_report(
    state_path: str | Path,
    content_path: str | Path,
    actor: str = "actor.player",
) -> dict[str, Any]:
    registry = Registry()
    register_builtins(registry)
    state = load_world_state(state_path)
    repository = ContentRepository.from_path(content_path, registry=registry)
    orchestrator = SceneOrchestrator(content_repository=repository, registry=registry)
    presentation = orchestrator.select(
        state,
        {
            "command_id": "diagnostic.scene_report",
            "command": Command(type="diagnostic.scene_report", actor=actor),
            "content_repository": repository,
        },
    )
    return presentation.scene_candidate_report


def diff_state_files(before_path: str | Path, after_path: str | Path) -> dict[str, Any]:
    return state_diff(load_world_state(before_path), load_world_state(after_path))


def changed_by_report(trace: dict[str, Any], path: str) -> list[dict[str, Any]]:
    command_trace = _trace_from_plain_data(trace)
    return changed_by(command_trace, path)


def _load_commands(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8-sig") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("commands file must contain a JSON array")
    return data


def _trace_from_plain_data(trace: dict[str, Any]) -> Any:
    from .models import Change, ChangeSet, CommandTrace

    changes = [
        Change(
            path=list(change["path"]) if isinstance(change["path"], list) else str(change["path"]).split("."),
            before=change.get("before"),
            after=change.get("after"),
        )
        for change in trace.get("changeset", {}).get("changes", [])
    ]
    command = Command.from_mapping(trace["command"])
    return CommandTrace(
        command_id=trace["command_id"],
        command=command,
        status=trace["status"],
        changeset=ChangeSet(changes),
    )
