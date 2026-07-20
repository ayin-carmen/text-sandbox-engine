"""Scene selection and candidate reporting."""

from __future__ import annotations

from typing import Any

from .content import ContentRepository, rule_refs_from_scene
from .engines import RuleEngine
from .models import Presentation
from .registry import Registry


class SceneOrchestrator:
    def __init__(
        self,
        content_repository: ContentRepository | None = None,
        registry: Registry | None = None,
    ) -> None:
        self._content_repository = content_repository or ContentRepository()
        self._rule_engine = RuleEngine(registry) if registry else None

    def select(self, state: dict[str, Any], context: dict[str, Any]) -> Presentation:
        candidates: list[dict[str, Any]] = []
        filtered: list[dict[str, Any]] = []

        for scene in self._content_repository.all_scenes():
            scene_id = scene["id"]
            scope_result = _scope_matches(scene, state, context)
            if not scope_result["matched"]:
                filtered.append(
                    {
                        "scene": scene_id,
                        "eligible": False,
                        "reason": scope_result["reason"],
                    }
                )
                continue

            repeat_result = _repeat_policy_allows(scene, state)
            if not repeat_result["matched"]:
                filtered.append(
                    {
                        "scene": scene_id,
                        "eligible": False,
                        "reason": repeat_result["reason"],
                    }
                )
                continue

            rule_results = []
            if self._rule_engine:
                rule_results = [
                    self._rule_engine.evaluate(rule_ref, state, context)
                    for rule_ref in rule_refs_from_scene(scene)
                ]
            failed_rules = [result for result in rule_results if not result.passed]
            if failed_rules:
                filtered.append(
                    {
                        "scene": scene_id,
                        "eligible": False,
                        "reason": failed_rules[0].reason,
                        "rules": [_rule_report(result) for result in rule_results],
                    }
                )
                continue

            candidates.append(
                {
                    "scene": scene_id,
                    "eligible": True,
                    "priority": int(scene.get("priority", 0)),
                    "reason": "scope and conditions matched",
                    "rules": [_rule_report(result) for result in rule_results],
                }
            )

        candidates.sort(key=lambda item: (-int(item["priority"]), str(item["scene"])))
        selected = candidates[0]["scene"] if candidates else None
        selected_scene = _find_scene(self._content_repository.all_scenes(), selected)
        return Presentation(
            selected_scene=selected,
            scene=selected_scene,
            scene_candidate_report={
                "selected": selected,
                "candidates": candidates,
                "filtered": filtered,
                "reason": "selected highest-priority eligible scene"
                if selected
                else "no eligible scene",
            },
        )


def _scope_matches(scene: dict[str, Any], state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    scope = scene.get("scope", {})
    command = context.get("command")
    actor_id = getattr(command, "actor", None)
    actor = state.get("entities", {}).get(actor_id, {}) if actor_id else {}
    current_location = (
        actor.get("components", {})
        .get("location", {})
        .get("current")
    )

    expected_location = scope.get("location")
    if expected_location and expected_location != current_location:
        return {
            "matched": False,
            "reason": f"location mismatch: expected {expected_location}, got {current_location}",
        }

    expected_actor = scope.get("actor")
    if expected_actor and expected_actor != actor_id:
        return {
            "matched": False,
            "reason": f"actor mismatch: expected {expected_actor}, got {actor_id}",
        }

    return {"matched": True, "reason": "scope matched"}


def _repeat_policy_allows(scene: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    if scene.get("repeat_policy") != "once":
        return {"matched": True, "reason": "repeat policy allows scene"}
    seen_scenes = state.get("globals", {}).get("narrative", {}).get("seen_scenes", [])
    if scene["id"] in seen_scenes:
        return {"matched": False, "reason": "scene has already been seen"}
    return {"matched": True, "reason": "scene has not been seen"}


def _rule_report(result: Any) -> dict[str, Any]:
    return {
        "rule": result.rule_type,
        "args": result.args,
        "passed": result.passed,
        "reason": result.reason,
        "observed": result.observed,
    }


def _find_scene(scenes: list[dict[str, Any]], scene_id: str | None) -> dict[str, Any] | None:
    if scene_id is None:
        return None
    for scene in scenes:
        if scene["id"] == scene_id:
            return scene
    return None
