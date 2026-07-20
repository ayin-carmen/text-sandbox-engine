"""Versioned JSON persistence for world state."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .migrations import (
    CURRENT_SAVE_SCHEMA_VERSION,
    MigrationReport,
    MigrationStep,
    build_default_migration_registry,
)
from .modules import DEFAULT_MODULE_VERSIONS

ENGINE_VERSION = "0.4.0"


@dataclass(frozen=True)
class SaveMetadata:
    engine_version: str
    save_schema_version: int
    world_schema_version: int
    enabled_modules: list[str]
    module_versions: dict[str, str]
    component_schema_versions: dict[str, int]
    random_state: dict[str, Any]
    history_summary: dict[str, Any]
    migration_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class SaveReport:
    path: str
    metadata: SaveMetadata


@dataclass(frozen=True)
class LoadedSave:
    world_state: dict[str, Any]
    metadata: SaveMetadata
    migration_report: MigrationReport


def load_world_state(path: str | Path) -> dict[str, Any]:
    return load_save(path).world_state


def save_world_state(path: str | Path, state: dict[str, Any]) -> SaveReport:
    metadata = build_save_metadata(state)
    save_data = {
        "save_metadata": asdict(metadata),
        "world_state": state,
    }
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(save_data, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return SaveReport(str(path), metadata)


def load_save(
    path: str | Path,
    known_modules: dict[str, str] | None = None,
) -> LoadedSave:
    with Path(path).open("r", encoding="utf-8") as file:
        raw_data = json.load(file)
    if not isinstance(raw_data, dict):
        raise ValueError("save file must contain a JSON object")

    save_data, initial_report = _normalize_save_data(raw_data)
    registry = build_default_migration_registry()
    migrated_data, migration_report = registry.migrate_save(save_data)
    combined_report = MigrationReport(initial_report.steps + migration_report.steps)

    metadata = _metadata_from_mapping(migrated_data["save_metadata"])
    _validate_modules(
        metadata,
        DEFAULT_MODULE_VERSIONS if known_modules is None else known_modules,
    )
    return LoadedSave(
        world_state=migrated_data["world_state"],
        metadata=metadata,
        migration_report=combined_report,
    )


def build_save_metadata(state: dict[str, Any]) -> SaveMetadata:
    module_versions = dict(DEFAULT_MODULE_VERSIONS)
    return SaveMetadata(
        engine_version=ENGINE_VERSION,
        save_schema_version=CURRENT_SAVE_SCHEMA_VERSION,
        world_schema_version=int(state.get("schema_version", 1)),
        enabled_modules=sorted(module_versions),
        module_versions=module_versions,
        component_schema_versions=collect_component_schema_versions(state),
        random_state={"seed": state.get("seed")},
        history_summary={"entries": len(state.get("history", []))},
        migration_history=[],
    )


def collect_component_schema_versions(state: dict[str, Any]) -> dict[str, int]:
    versions: dict[str, int] = {}
    for entity in state.get("entities", {}).values():
        for component_name, component_data in entity.get("components", {}).items():
            version = 1
            if isinstance(component_data, dict):
                version = int(component_data.get("schema_version", 1))
            versions[component_name] = max(versions.get(component_name, 0), version)
    return dict(sorted(versions.items()))


def _normalize_save_data(raw_data: dict[str, Any]) -> tuple[dict[str, Any], MigrationReport]:
    if "save_metadata" in raw_data and "world_state" in raw_data:
        return raw_data, MigrationReport()

    metadata = asdict(build_save_metadata(raw_data))
    metadata["save_schema_version"] = 1
    save_data = {
        "save_metadata": metadata,
        "world_state": raw_data,
    }
    report = MigrationReport(
        [
            MigrationStep(
                name="bare_world_state_to_save_envelope",
                from_version=0,
                to_version=1,
                message="wrapped legacy bare world state in a versioned save envelope",
            )
        ]
    )
    return save_data, report


def _metadata_from_mapping(data: dict[str, Any]) -> SaveMetadata:
    return SaveMetadata(
        engine_version=str(data["engine_version"]),
        save_schema_version=int(data["save_schema_version"]),
        world_schema_version=int(data["world_schema_version"]),
        enabled_modules=list(data.get("enabled_modules", [])),
        module_versions=dict(data.get("module_versions", {})),
        component_schema_versions={
            str(key): int(value)
            for key, value in data.get("component_schema_versions", {}).items()
        },
        random_state=dict(data.get("random_state", {})),
        history_summary=dict(data.get("history_summary", {})),
        migration_history=list(data.get("migration_history", [])),
    )


def _validate_modules(metadata: SaveMetadata, known_modules: dict[str, str]) -> None:
    missing = [
        module_id
        for module_id in metadata.enabled_modules
        if module_id not in known_modules
    ]
    if missing:
        raise ValueError(f"save requires missing modules: {', '.join(sorted(missing))}")

    incompatible = [
        f"{module_id} saved={metadata.module_versions[module_id]} current={known_modules[module_id]}"
        for module_id in metadata.enabled_modules
        if module_id in metadata.module_versions
        and module_id in known_modules
        and metadata.module_versions[module_id] != known_modules[module_id]
    ]
    if incompatible:
        raise ValueError(f"save module version mismatch: {', '.join(incompatible)}")
