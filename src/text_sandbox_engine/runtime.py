"""Runtime entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .builtins import register_builtins
from .content import ContentRepository
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
        content_repository: ContentRepository | None = None,
        scene_orchestrator: SceneOrchestrator | None = None,
    ) -> None:
        self.registry = registry or Registry()
        register_builtins(self.registry)
        self.content_repository = content_repository or ContentRepository()
        self.state_store = StateStore(world_state)
        scene_orchestrator = scene_orchestrator or SceneOrchestrator(
            content_repository=self.content_repository,
            registry=self.registry,
        )
        self.pipeline = CommandPipeline(
            self.state_store,
            self.registry,
            scene_orchestrator=scene_orchestrator,
            content_repository=self.content_repository,
        )

    @classmethod
    def from_file(cls, path: str | Path, content_path: str | Path | None = None) -> "Runtime":
        registry = Registry()
        register_builtins(registry)
        content_repository = (
            ContentRepository.from_path(content_path, registry=registry)
            if content_path
            else ContentRepository()
        )
        return cls(
            load_world_state(path),
            registry=registry,
            content_repository=content_repository,
        )

    def execute(self, command: Command | dict[str, Any]) -> CommandResult:
        return self.pipeline.execute(command)

    def snapshot(self) -> dict[str, Any]:
        return self.state_store.snapshot()

    def save_game(self, path: str | Path) -> None:
        save_world_state(path, self.snapshot())

    @classmethod
    def load_game(cls, path: str | Path) -> "Runtime":
        return cls.from_file(path)
