"""Inventory module: item possession rules and effects."""

from __future__ import annotations

from typing import Any

from ..models import EffectResult, RuleResult
from ..transaction import Transaction


def register_inventory_module(registry: Any) -> None:
    registry.register_rule("inventory.has_item", rule_has_item)
    registry.register_effect("inventory.add_item", effect_add_item)
    registry.register_effect("inventory.remove_item", effect_remove_item)


def rule_has_item(state: dict[str, Any], args: list[Any], context: dict[str, Any]) -> RuleResult:
    actor_id, item_id = str(args[0]), str(args[1])
    items = _items(state, actor_id)
    passed = item_id in items
    return RuleResult(
        passed=passed,
        rule_type="inventory.has_item",
        args=args,
        reason="item is present" if passed else "item is missing",
        observed={"actor": actor_id, "item": item_id, "items": items},
    )


def effect_add_item(transaction: Transaction, args: list[Any], context: dict[str, Any]) -> EffectResult:
    actor_id, item_id = str(args[0]), str(args[1])
    path = ["entities", actor_id, "components", "inventory", "items"]
    items = list(transaction.read_value(path, default=[]))
    if item_id not in items:
        items.append(item_id)
    transaction.set_value(path, items)
    return EffectResult(True, "inventory.add_item", args, "item added", transaction.changes_since_last_effect())


def effect_remove_item(transaction: Transaction, args: list[Any], context: dict[str, Any]) -> EffectResult:
    actor_id, item_id = str(args[0]), str(args[1])
    path = ["entities", actor_id, "components", "inventory", "items"]
    items = list(transaction.read_value(path, default=[]))
    if item_id in items:
        items.remove(item_id)
    transaction.set_value(path, items)
    return EffectResult(True, "inventory.remove_item", args, "item removed", transaction.changes_since_last_effect())


def _items(state: dict[str, Any], actor_id: str) -> list[str]:
    actor = state.get("entities", {}).get(actor_id, {})
    return list(actor.get("components", {}).get("inventory", {}).get("items", []))
