"""Space module: locations, travel commands, and movement effects."""

from __future__ import annotations

from typing import Any

from ..models import CommandPlan, EffectRef, EffectResult, RuleRef, RuleResult
from ..transaction import Transaction


def register_space_module(registry: Any) -> None:
    registry.register_command("space.travel_to", plan_travel_to)
    registry.register_rule("space.location_connected", rule_location_connected)
    registry.register_rule("space.location_accessible", rule_location_accessible)
    registry.register_effect("space.move_entity", effect_move_entity)


def plan_travel_to(command: Any, context: dict[str, Any]) -> CommandPlan:
    if not command.actor:
        raise ValueError("space.travel_to requires an actor")
    if not command.target:
        raise ValueError("space.travel_to requires a target")

    return CommandPlan(
        rules=[
            RuleRef("space.location_connected", [command.actor, command.target]),
            RuleRef("space.location_accessible", [command.target]),
        ],
        effects=[
            EffectRef("space.move_entity", [command.actor, command.target]),
            EffectRef("time.advance", [1]),
        ],
    )


def rule_location_connected(state: dict[str, Any], args: list[Any], context: dict[str, Any]) -> RuleResult:
    actor_id, target_id = args
    actor = state.get("entities", {}).get(actor_id)
    if actor is None:
        return RuleResult(False, "space.location_connected", args, "actor not found")

    current_location = actor.get("components", {}).get("location", {}).get("current")
    current_entity = state.get("entities", {}).get(current_location)
    connections = (
        current_entity.get("components", {}).get("map_node", {}).get("connections", [])
        if current_entity
        else []
    )

    passed = target_id in connections
    reason = "target is connected" if passed else "target is not connected"
    return RuleResult(
        passed=passed,
        rule_type="space.location_connected",
        args=args,
        reason=reason,
        observed={
            "current_location": current_location,
            "connections": connections,
        },
    )


def rule_location_accessible(state: dict[str, Any], args: list[Any], context: dict[str, Any]) -> RuleResult:
    target_id = args[0]
    target = state.get("entities", {}).get(target_id)
    if target is None:
        return RuleResult(False, "space.location_accessible", args, "target not found")

    blocked = bool(target.get("components", {}).get("access", {}).get("blocked", False))
    return RuleResult(
        passed=not blocked,
        rule_type="space.location_accessible",
        args=args,
        reason="target is accessible" if not blocked else "target is blocked",
        observed={"blocked": blocked},
    )


def effect_move_entity(transaction: Transaction, args: list[Any], context: dict[str, Any]) -> EffectResult:
    actor_id, target_id = args
    path = ["entities", actor_id, "components", "location", "current"]
    transaction.set_value(path, target_id)
    return EffectResult(
        applied=True,
        effect_type="space.move_entity",
        args=args,
        reason="entity moved",
        changes=transaction.changes_since_last_effect(),
    )
