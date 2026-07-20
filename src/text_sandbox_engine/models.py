"""Shared data models for the phase 1 runtime prototype."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class Command:
    type: str
    actor: str | None = None
    target: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    source: str = "player"
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "Command":
        return cls(
            type=data["type"],
            actor=data.get("actor"),
            target=data.get("target"),
            args=dict(data.get("args", {})),
            source=data.get("source", "player"),
            metadata=dict(data.get("metadata", {})),
            id=data.get("id"),
        )


@dataclass(frozen=True)
class RuleRef:
    rule: str
    args: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EffectRef:
    effect: str
    args: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandPlan:
    rules: list[RuleRef] = field(default_factory=list)
    effects: list[EffectRef] = field(default_factory=list)


@dataclass(frozen=True)
class RuleResult:
    passed: bool
    rule_type: str
    args: list[Any] = field(default_factory=list)
    reason: str = ""
    observed: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Change:
    path: list[str]
    before: Any
    after: Any

    @property
    def path_text(self) -> str:
        return ".".join(self.path)


@dataclass(frozen=True)
class ChangeSet:
    changes: list[Change] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.changes


@dataclass(frozen=True)
class EffectResult:
    applied: bool
    effect_type: str
    args: list[Any] = field(default_factory=list)
    reason: str = ""
    changes: list[Change] = field(default_factory=list)


@dataclass(frozen=True)
class Presentation:
    selected_scene: str | None = None
    scene: dict[str, Any] | None = None
    scene_candidate_report: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandTrace:
    command_id: str
    command: Command
    status: Literal["succeeded", "failed"]
    rule_results: list[RuleResult] = field(default_factory=list)
    effect_results: list[EffectResult] = field(default_factory=list)
    changeset: ChangeSet = field(default_factory=ChangeSet)
    presentation: Presentation = field(default_factory=Presentation)
    failure_reason: str | None = None


@dataclass(frozen=True)
class CommandResult:
    status: Literal["succeeded", "failed"]
    trace: CommandTrace
    state: dict[str, Any]
