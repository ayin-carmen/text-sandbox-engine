"""Narrative module: scene choice execution."""

from __future__ import annotations

from typing import Any

from ..content import effect_refs_from_choice, rule_refs_from_choice, rule_refs_from_scene
from ..models import CommandPlan, EffectRef, RuleRef, EffectResult, RuleResult
from ..transaction import Transaction


def register_narrative_module(registry: Any) -> None:
    registry.register_command("narrative.choose", plan_choose_scene_option)
    registry.register_rule("narrative.scene_not_seen", rule_scene_not_seen)
    registry.register_effect("narrative.mark_scene_seen", effect_mark_scene_seen)


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

    effects = effect_refs_from_choice(choice)
    if scene.get("repeat_policy") == "once":
        effects.append(EffectRef("narrative.mark_scene_seen", [scene["id"]]))

    rules = rule_refs_from_scene(scene) + rule_refs_from_choice(choice)
    if scene.get("repeat_policy") == "once":
        rules = [RuleRef("narrative.scene_not_seen", [scene["id"]])] + rules

    return CommandPlan(
        rules=rules,
        effects=effects,
    )


def rule_scene_not_seen(state: dict[str, Any], args: list[Any], context: dict[str, Any]) -> RuleResult:
    scene_id = str(args[0])
    seen_scenes = list(state.get("globals", {}).get("narrative", {}).get("seen_scenes", []))
    passed = scene_id not in seen_scenes
    return RuleResult(
        passed=passed,
        rule_type="narrative.scene_not_seen",
        args=args,
        reason="scene has not been seen" if passed else "scene has already been seen",
        observed={"scene": scene_id, "seen_scenes": seen_scenes},
    )


def effect_mark_scene_seen(transaction: Transaction, args: list[Any], context: dict[str, Any]) -> EffectResult:
    scene_id = str(args[0])
    path = ["globals", "narrative", "seen_scenes"]
    seen_scenes = list(transaction.read_value(path, default=[]))
    if scene_id not in seen_scenes:
        seen_scenes.append(scene_id)
    transaction.set_value(path, seen_scenes)
    return EffectResult(
        True,
        "narrative.mark_scene_seen",
        args,
        "scene marked as seen",
        transaction.changes_since_last_effect(),
    )
