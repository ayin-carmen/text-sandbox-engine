"""Quest module: quest state rules and effects."""

from __future__ import annotations

from typing import Any

from ..models import EffectResult, RuleResult
from ..transaction import Transaction


def register_quest_module(registry: Any) -> None:
    registry.register_rule("quest.stage_is", rule_stage_is)
    registry.register_effect("quest.set_stage", effect_set_stage)
    registry.register_effect("quest.complete", effect_complete)


def rule_stage_is(state: dict[str, Any], args: list[Any], context: dict[str, Any]) -> RuleResult:
    quest_id, expected_stage = str(args[0]), str(args[1])
    quest = _quest(state, quest_id)
    current_stage = quest.get("stage", "not_started")
    passed = current_stage == expected_stage
    return RuleResult(
        passed=passed,
        rule_type="quest.stage_is",
        args=args,
        reason="quest stage matched" if passed else "quest stage did not match",
        observed={"quest": quest_id, "current_stage": current_stage, "expected_stage": expected_stage},
    )


def effect_set_stage(transaction: Transaction, args: list[Any], context: dict[str, Any]) -> EffectResult:
    quest_id, stage = str(args[0]), str(args[1])
    path = ["globals", "quests", quest_id, "stage"]
    transaction.set_value(path, stage)
    return EffectResult(True, "quest.set_stage", args, "quest stage updated", transaction.changes_since_last_effect())


def effect_complete(transaction: Transaction, args: list[Any], context: dict[str, Any]) -> EffectResult:
    quest_id = str(args[0])
    transaction.set_value(["globals", "quests", quest_id, "stage"], "completed")
    transaction.set_value(["globals", "quests", quest_id, "completed"], True)
    return EffectResult(True, "quest.complete", args, "quest completed", transaction.changes_since_last_effect())


def _quest(state: dict[str, Any], quest_id: str) -> dict[str, Any]:
    return dict(state.get("globals", {}).get("quests", {}).get(quest_id, {}))
