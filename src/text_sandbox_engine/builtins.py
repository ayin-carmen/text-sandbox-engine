"""Built-in module registration for the runtime prototype."""

from __future__ import annotations

from typing import Any

from .models import EffectResult, RuleResult
from .modules import register_default_modules
from .registry import Registry
from .transaction import Transaction


def register_builtins(registry: Registry) -> None:
    register_default_modules(registry)
    registry.register_rule("flag.is_false", rule_flag_is_false)
    registry.register_effect("flag.set", effect_set_flag)


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
