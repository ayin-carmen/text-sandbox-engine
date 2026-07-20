"""Time module: time rules and time advancement effects."""

from __future__ import annotations

from typing import Any

from ..models import EffectResult, RuleResult
from ..transaction import Transaction


def register_time_module(registry: Any) -> None:
    registry.register_rule("time.period_in", rule_time_period_in)
    registry.register_effect("time.advance", effect_advance_time)


def rule_time_period_in(state: dict[str, Any], args: list[Any], context: dict[str, Any]) -> RuleResult:
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


def effect_advance_time(transaction: Transaction, args: list[Any], context: dict[str, Any]) -> EffectResult:
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
