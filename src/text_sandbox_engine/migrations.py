"""Save migration registry and reports."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

CURRENT_SAVE_SCHEMA_VERSION = 2

SaveMigration = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class MigrationStep:
    name: str
    from_version: int
    to_version: int
    message: str


@dataclass(frozen=True)
class MigrationReport:
    steps: list[MigrationStep] = field(default_factory=list)

    @property
    def migrated(self) -> bool:
        return bool(self.steps)


class MigrationRegistry:
    def __init__(self) -> None:
        self._save_migrations: dict[int, tuple[int, str, SaveMigration]] = {}

    def register_save_migration(
        self,
        from_version: int,
        to_version: int,
        name: str,
        migration: SaveMigration,
    ) -> None:
        self._save_migrations[from_version] = (to_version, name, migration)

    def migrate_save(
        self,
        save_data: dict[str, Any],
        target_version: int = CURRENT_SAVE_SCHEMA_VERSION,
    ) -> tuple[dict[str, Any], MigrationReport]:
        current = int(save_data.get("save_metadata", {}).get("save_schema_version", 1))
        migrated = dict(save_data)
        steps: list[MigrationStep] = []

        while current < target_version:
            if current not in self._save_migrations:
                raise ValueError(f"no save migration registered from version {current}")
            next_version, name, migration = self._save_migrations[current]
            migrated = migration(migrated)
            steps.append(
                MigrationStep(
                    name=name,
                    from_version=current,
                    to_version=next_version,
                    message=f"migrated save schema from {current} to {next_version}",
                )
            )
            current = next_version

        if current > target_version:
            raise ValueError(
                f"save schema version {current} is newer than supported version {target_version}"
            )

        return migrated, MigrationReport(steps)


def build_default_migration_registry() -> MigrationRegistry:
    registry = MigrationRegistry()
    registry.register_save_migration(
        from_version=1,
        to_version=2,
        name="save_schema_1_to_2",
        migration=_save_schema_1_to_2,
    )
    return registry


def _save_schema_1_to_2(save_data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(save_data)
    metadata = dict(migrated.get("save_metadata", {}))
    metadata["save_schema_version"] = 2
    metadata.setdefault("component_schema_versions", {})
    metadata.setdefault("migration_history", [])
    migrated["save_metadata"] = metadata
    return migrated
