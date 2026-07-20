"""Runtime entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .builtins import register_builtins
from .models import Command, CommandResult
from .persistence import load_world_state, save_world_state
from .pipeline import CommandPipeline
from .registry import Registry
from .scene import SceneOrchestrator
from .state import StateStore


class Runtime:
    def __init__(
        self,
        world_state: dict[str, Any],
        registry: Registry | None = None,
        scene_orchestrator: SceneOrchestrator | None = None,
    ) -> None:
        self.registry = registry or Registry()
        register_builtins(self.registry)
        self.state_store = StateStore(world_state)
        self.pipeline = CommandPipeline(
            self.state_store,
            self.registry,
            scene_orchestrator=scene_orchestrator,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "Runtime":
        return cls(load_world_state(path))

    def execute(self, command: Command | dict[str, Any]) -> CommandResult:
        return self.pipeline.execute(command)

    def snapshot(self) -> dict[str, Any]:
        return self.state_store.snapshot()

    def save_game(self, path: str | Path) -> None:
        save_world_state(path, self.snapshot())

    @classmethod
    def load_game(cls, path: str | Path) -> "Runtime":
        return cls.from_file(path)
