"""Built-in command, rule, and effect handlers for the phase 1 prototype."""

from __future__ import annotations

from typing import Any

from .models import CommandPlan, EffectRef, EffectResult, RuleRef, RuleResult
from .registry import Registry
from .transaction import Transaction


def register_builtins(registry: Registry) -> None:
    registry.register_command("space.travel_to", plan_travel_to)
    registry.register_rule("space.location_connected", rule_location_connected)
    registry.register_rule("space.location_accessible", rule_location_accessible)
    registry.register_rule("flag.is_false", rule_flag_is_false)
    registry.register_rule("time.period_in", rule_time_period_in)
    registry.register_effect("space.move_entity", effect_move_entity)
    registry.register_effect("time.advance", effect_advance_time)
    registry.register_effect("flag.set", effect_set_flag)


def plan_travel_to(command: Any, context: Any) -> CommandPlan:
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


def rule_location_connected(state: dict[str, Any], args: list[Any], context: Any) -> RuleResult:
    actor_id, target_id = args
    actor = state.get("entities", {}).get(actor_id)
    if actor is None:
        return RuleResult(False, "space.location_connected", args, "actor not found")

    current_location = (
        actor.get("components", {})
        .get("location", {})
        .get("current")
    )
    current_entity = state.get("entities", {}).get(current_location)
    connections = (
        current_entity.get("components", {})
        .get("map_node", {})
        .get("connections", [])
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


def rule_location_accessible(state: dict[str, Any], args: list[Any], context: Any) -> RuleResult:
    target_id = args[0]
    target = state.get("entities", {}).get(target_id)
    if target is None:
        return RuleResult(False, "space.location_accessible", args, "target not found")

    blocked = bool(
        target.get("components", {})
        .get("access", {})
        .get("blocked", False)
    )
    return RuleResult(
        passed=not blocked,
        rule_type="space.location_accessible",
        args=args,
        reason="target is accessible" if not blocked else "target is blocked",
        observed={"blocked": blocked},
    )


def rule_flag_is_false(state: dict[str, Any], args: list[Any], context: Any) -> RuleResult:
    flag_name = args[0]
    value = bool(state.get("flags", {}).get(flag_name, False))
    return RuleResult(
        passed=not value,
        rule_type="flag.is_false",
        args=args,
        reason="flag is false" if not value else "flag is true",
        observed={"value": value},
    )


def rule_time_period_in(state: dict[str, Any], args: list[Any], context: Any) -> RuleResult:
    current_period = state.get("globals", {}).get("clock", {}).get("period")
    allowed = [str(item) for item in args]
    passed = current_period in allowed
    return RuleResult(
        passed=passed,
        rule_type="time.period_in",
        args=args,
        reason="time period is allowed" if passed else "time period is not allowed",
        observed={"current_period": current_period, "allowed": allowed},
    )


def effect_move_entity(transaction: Transaction, args: list[Any], context: Any) -> EffectResult:
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


def effect_advance_time(transaction: Transaction, args: list[Any], context: Any) -> EffectResult:
    amount = int(args[0])
    path = ["globals", "clock", "tick"]
    current = int(transaction.read_value(path))
    transaction.set_value(path, current + amount)
    return EffectResult(
        applied=True,
        effect_type="time.advance",
        args=args,
        reason="time advanced",
        changes=transaction.changes_since_last_effect(),
    )


def effect_set_flag(transaction: Transaction, args: list[Any], context: Any) -> EffectResult:
    flag_name, value = args
    transaction.set_value(["flags", str(flag_name)], bool(value))
    return EffectResult(
        applied=True,
        effect_type="flag.set",
        args=args,
        reason="flag updated",
        changes=transaction.changes_since_last_effect(),
    )
