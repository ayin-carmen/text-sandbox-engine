"""Content loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import EffectRef, RuleRef
from .registry import Registry


@dataclass(frozen=True)
class ContentValidationIssue:
    path: str
    message: str


@dataclass(frozen=True)
class ContentValidationReport:
    issues: list[ContentValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.issues


class ContentRepository:
    def __init__(self, scenes: list[dict[str, Any]] | None = None) -> None:
        self._scenes = list(scenes or [])

    @classmethod
    def from_path(cls, path: str | Path, registry: Registry | None = None) -> "ContentRepository":
        root = Path(path)
        scene_files = _scene_files(root)
        scenes = [_load_json(scene_file) for scene_file in scene_files]
        repository = cls(scenes=scenes)
        report = repository.validate(registry=registry)
        if not report.passed:
            messages = "; ".join(f"{issue.path}: {issue.message}" for issue in report.issues)
            raise ValueError(f"content validation failed: {messages}")
        return repository

    def all_scenes(self) -> list[dict[str, Any]]:
        return [dict(scene) for scene in self._scenes]

    def get_scene(self, scene_id: str) -> dict[str, Any] | None:
        for scene in self._scenes:
            if scene.get("id") == scene_id:
                return dict(scene)
        return None

    def validate(self, registry: Registry | None = None) -> ContentValidationReport:
        issues: list[ContentValidationIssue] = []
        seen_ids: set[str] = set()

        for index, scene in enumerate(self._scenes):
            path = scene.get("id", f"scene[{index}]")
            required = ["id", "scope", "priority", "conditions", "text", "choices"]
            for field_name in required:
                if field_name not in scene:
                    issues.append(ContentValidationIssue(path, f"missing required field: {field_name}"))

            scene_id = scene.get("id")
            if isinstance(scene_id, str):
                if scene_id in seen_ids:
                    issues.append(ContentValidationIssue(scene_id, "duplicate scene id"))
                seen_ids.add(scene_id)

            if not isinstance(scene.get("conditions", []), list):
                issues.append(ContentValidationIssue(path, "conditions must be a list"))
                continue

            for rule in scene.get("conditions", []):
                _validate_rule_ref(path, rule, issues, registry)

            choices = scene.get("choices", [])
            if not isinstance(choices, list) or not choices:
                issues.append(ContentValidationIssue(path, "choices must be a non-empty list"))
                continue

            for choice_index, choice in enumerate(choices):
                choice_path = f"{path}.choices[{choice_index}]"
                if "text" not in choice:
                    issues.append(ContentValidationIssue(choice_path, "missing choice text"))
                for rule in choice.get("visible_if", []):
                    _validate_rule_ref(choice_path, rule, issues, registry)
                for effect in choice.get("effects", []):
                    _validate_effect_ref(choice_path, effect, issues, registry)

        return ContentValidationReport(issues)


def rule_refs_from_scene(scene: dict[str, Any]) -> list[RuleRef]:
    return [
        RuleRef(
            rule=item["rule"],
            args=list(item.get("args", [])),
            metadata=dict(item.get("metadata", {})),
        )
        for item in scene.get("conditions", [])
    ]


def rule_refs_from_choice(choice: dict[str, Any]) -> list[RuleRef]:
    return [
        RuleRef(
            rule=item["rule"],
            args=list(item.get("args", [])),
            metadata=dict(item.get("metadata", {})),
        )
        for item in choice.get("visible_if", [])
    ]


def effect_refs_from_choice(choice: dict[str, Any]) -> list[EffectRef]:
    return [
        EffectRef(
            effect=item["effect"],
            args=list(item.get("args", [])),
            metadata=dict(item.get("metadata", {})),
        )
        for item in choice.get("effects", [])
    ]


def _scene_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    scene_root = root / "scenes"
    if scene_root.exists():
        return sorted(scene_root.rglob("*.json"))
    return sorted(root.rglob("*.json"))


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _validate_rule_ref(
    path: str,
    value: Any,
    issues: list[ContentValidationIssue],
    registry: Registry | None,
) -> None:
    if not isinstance(value, dict):
        issues.append(ContentValidationIssue(path, "rule reference must be an object"))
        return
    rule_type = value.get("rule")
    if not isinstance(rule_type, str) or not rule_type:
        issues.append(ContentValidationIssue(path, "rule reference requires rule"))
        return
    if registry and not registry.has_rule(rule_type):
        issues.append(ContentValidationIssue(path, f"unknown rule: {rule_type}"))
    if not isinstance(value.get("args", []), list):
        issues.append(ContentValidationIssue(path, "rule args must be a list"))


def _validate_effect_ref(
    path: str,
    value: Any,
    issues: list[ContentValidationIssue],
    registry: Registry | None,
) -> None:
    if not isinstance(value, dict):
        issues.append(ContentValidationIssue(path, "effect reference must be an object"))
        return
    effect_type = value.get("effect")
    if not isinstance(effect_type, str) or not effect_type:
        issues.append(ContentValidationIssue(path, "effect reference requires effect"))
        return
    if registry and not registry.has_effect(effect_type):
        issues.append(ContentValidationIssue(path, f"unknown effect: {effect_type}"))
    if not isinstance(value.get("args", []), list):
        issues.append(ContentValidationIssue(path, "effect args must be a list"))
