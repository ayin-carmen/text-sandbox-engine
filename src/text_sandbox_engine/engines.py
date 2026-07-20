"""Rule and effect execution engines."""

from __future__ import annotations

from .models import EffectRef, EffectResult, RuleRef, RuleResult
from .registry import Registry
from .transaction import Transaction


class RuleEngine:
    def __init__(self, registry: Registry) -> None:
        self._registry = registry

    def evaluate(self, rule_ref: RuleRef, state: dict, context: dict) -> RuleResult:
        handler = self._registry.get_rule(rule_ref.rule)
        return handler(state, list(rule_ref.args), context)


class EffectEngine:
    def __init__(self, registry: Registry) -> None:
        self._registry = registry

    def apply(self, effect_ref: EffectRef, transaction: Transaction, context: dict) -> EffectResult:
        handler = self._registry.get_effect(effect_ref.effect)
        transaction.mark_effect_boundary()
        return handler(transaction, list(effect_ref.args), context)
