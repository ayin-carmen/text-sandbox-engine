"""Registry for command, rule, and effect handlers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

CommandHandler = Callable[[Any, dict[str, Any]], Any]
RuleHandler = Callable[[dict[str, Any], list[Any], dict[str, Any]], Any]
EffectHandler = Callable[[Any, list[Any], dict[str, Any]], Any]


class Registry:
    def __init__(self) -> None:
        self._commands: dict[str, CommandHandler] = {}
        self._rules: dict[str, RuleHandler] = {}
        self._effects: dict[str, EffectHandler] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def register_command(
        self,
        command_type: str,
        handler: CommandHandler,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._commands[command_type] = handler
        self._set_metadata("command", command_type, metadata)

    def register_rule(
        self,
        rule_type: str,
        handler: RuleHandler,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._rules[rule_type] = handler
        self._set_metadata("rule", rule_type, metadata)

    def register_effect(
        self,
        effect_type: str,
        handler: EffectHandler,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._effects[effect_type] = handler
        self._set_metadata("effect", effect_type, metadata)

    def metadata(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._metadata.values()]

    def _set_metadata(
        self,
        kind: str,
        type_id: str,
        metadata: dict[str, Any] | None,
    ) -> None:
        item = dict(metadata or {})
        item.setdefault("kind", kind)
        item.setdefault("type_id", type_id)
        item.setdefault("module", type_id.split(".", 1)[0])
        item.setdefault("module_version", "1.0")
        item.setdefault("description", type_id)
        item.setdefault("parameters", [])
        item.setdefault("reads", [])
        item.setdefault("writes", [])
        self._metadata[f"{kind}:{type_id}"] = item

    def get_command(self, command_type: str) -> CommandHandler:
        try:
            return self._commands[command_type]
        except KeyError as exc:
            raise KeyError(f"unknown command: {command_type}") from exc

    def get_rule(self, rule_type: str) -> RuleHandler:
        try:
            return self._rules[rule_type]
        except KeyError as exc:
            raise KeyError(f"unknown rule: {rule_type}") from exc

    def get_effect(self, effect_type: str) -> EffectHandler:
        try:
            return self._effects[effect_type]
        except KeyError as exc:
            raise KeyError(f"unknown effect: {effect_type}") from exc

    def has_rule(self, rule_type: str) -> bool:
        return rule_type in self._rules

    def has_effect(self, effect_type: str) -> bool:
        return effect_type in self._effects
