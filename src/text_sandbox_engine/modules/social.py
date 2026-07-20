"""Social module: relationship and trust rules/effects."""

from __future__ import annotations

from typing import Any

from ..models import EffectResult, RuleResult
from ..transaction import Transaction


def register_social_module(registry: Any) -> None:
    registry.register_rule("social.trust_at_least", rule_trust_at_least)
    registry.register_effect("social.adjust_trust", effect_adjust_trust)


def rule_trust_at_least(state: dict[str, Any], args: list[Any], context: dict[str, Any]) -> RuleResult:
    actor_id, minimum = str(args[0]), int(args[1])
    trust = _trust(state, actor_id)
    passed = trust >= minimum
    return RuleResult(
        passed=passed,
        rule_type="social.trust_at_least",
        args=args,
        reason="trust threshold met" if passed else "trust threshold not met",
        observed={"actor": actor_id, "trust": trust, "minimum": minimum},
    )


def effect_adjust_trust(transaction: Transaction, args: list[Any], context: dict[str, Any]) -> EffectResult:
    actor_id, amount = str(args[0]), int(args[1])
    path = ["entities", actor_id, "components", "relationship", "trust"]
    current = int(transaction.read_value(path, default=0))
    transaction.set_value(path, current + amount)
    return EffectResult(
        True,
        "social.adjust_trust",
        args,
        "trust adjusted",
        transaction.changes_since_last_effect(),
    )


def _trust(state: dict[str, Any], actor_id: str) -> int:
    actor = state.get("entities", {}).get(actor_id, {})
    return int(actor.get("components", {}).get("relationship", {}).get("trust", 0))
