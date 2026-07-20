"""Actor module: basic player and NPC presence rules."""

from __future__ import annotations

from typing import Any

from ..models import RuleResult


def register_actor_module(registry: Any) -> None:
    registry.register_rule("actor.is_present", rule_actor_is_present)


def rule_actor_is_present(state: dict[str, Any], args: list[Any], context: dict[str, Any]) -> RuleResult:
    npc_id = str(args[0])
    command = context.get("command")
    actor_id = getattr(command, "actor", None)
    player_location = _entity_location(state, actor_id)
    npc_location = _entity_location(state, npc_id)
    passed = bool(player_location and npc_location and player_location == npc_location)
    return RuleResult(
        passed=passed,
        rule_type="actor.is_present",
        args=args,
        reason="actor is present" if passed else "actor is not present",
        observed={
            "actor": actor_id,
            "actor_location": player_location,
            "npc": npc_id,
            "npc_location": npc_location,
        },
    )


def _entity_location(state: dict[str, Any], entity_id: str | None) -> str | None:
    if not entity_id:
        return None
    entity = state.get("entities", {}).get(entity_id, {})
    return entity.get("components", {}).get("location", {}).get("current")
