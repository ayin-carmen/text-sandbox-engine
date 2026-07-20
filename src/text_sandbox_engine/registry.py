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

    def register_command(self, command_type: str, handler: CommandHandler) -> None:
        self._commands[command_type] = handler

    def register_rule(self, rule_type: str, handler: RuleHandler) -> None:
        self._rules[rule_type] = handler

    def register_effect(self, effect_type: str, handler: EffectHandler) -> None:
        self._effects[effect_type] = handler

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
