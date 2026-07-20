"""Narrative module: scene choice execution."""

from __future__ import annotations

from typing import Any

from ..content import effect_refs_from_choice, rule_refs_from_choice, rule_refs_from_scene
from ..models import CommandPlan


def register_narrative_module(registry: Any) -> None:
    registry.register_command("narrative.choose", plan_choose_scene_option)


def plan_choose_scene_option(command: Any, context: dict[str, Any]) -> CommandPlan:
    scene_id = command.args.get("scene_id") or command.target
    choice_index = int(command.args.get("choice_index", 0))
    content_repository = context.get("content_repository")
    if content_repository is None:
        raise ValueError("narrative.choose requires a content repository")

    scene = content_repository.get_scene(str(scene_id))
    if scene is None:
        raise ValueError(f"unknown scene: {scene_id}")

    choices = scene.get("choices", [])
    try:
        choice = choices[choice_index]
    except IndexError as exc:
        raise ValueError(f"unknown choice index {choice_index} for scene {scene_id}") from exc

    return CommandPlan(
        rules=rule_refs_from_scene(scene) + rule_refs_from_choice(choice),
        effects=effect_refs_from_choice(choice),
    )
