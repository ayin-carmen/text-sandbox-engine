"""Command execution pipeline."""

from __future__ import annotations

from typing import Any

from .engines import EffectEngine, RuleEngine
from .models import ChangeSet, Command, CommandResult, CommandTrace, Presentation
from .registry import Registry
from .scene import SceneOrchestrator
from .state import StateStore
from .transaction import Transaction


class CommandPipeline:
    def __init__(
        self,
        state_store: StateStore,
        registry: Registry,
        scene_orchestrator: SceneOrchestrator | None = None,
        content_repository: object | None = None,
    ) -> None:
        self._state_store = state_store
        self._registry = registry
        self._rule_engine = RuleEngine(registry)
        self._effect_engine = EffectEngine(registry)
        self._scene_orchestrator = scene_orchestrator or SceneOrchestrator()
        self._content_repository = content_repository

    def execute(self, command: Command | dict[str, Any]) -> CommandResult:
        normalized = command if isinstance(command, Command) else Command.from_mapping(command)
        command_id = normalized.id or self._next_command_id()
        context = {
            "command_id": command_id,
            "command": normalized,
            "content_repository": self._content_repository,
        }

        try:
            handler = self._registry.get_command(normalized.type)
            plan = handler(normalized, context)
        except Exception as exc:
            return self._failed_result(command_id, normalized, f"command planning failed: {exc}")

        state_snapshot = self._state_store.snapshot()
        rule_results = [
            self._rule_engine.evaluate(rule_ref, state_snapshot, context)
            for rule_ref in plan.rules
        ]
        failed_rules = [result for result in rule_results if not result.passed]
        if failed_rules:
            trace = CommandTrace(
                command_id=command_id,
                command=normalized,
                status="failed",
                rule_results=rule_results,
                failure_reason=failed_rules[0].reason,
            )
            return CommandResult("failed", trace, self._state_store.snapshot())

        transaction = Transaction(self._state_store.snapshot())
        effect_results = []
        try:
            for effect_ref in plan.effects:
                result = self._effect_engine.apply(effect_ref, transaction, context)
                effect_results.append(result)
                if not result.applied:
                    trace = CommandTrace(
                        command_id=command_id,
                        command=normalized,
                        status="failed",
                        rule_results=rule_results,
                        effect_results=effect_results,
                        failure_reason=result.reason,
                    )
                    return CommandResult("failed", trace, self._state_store.snapshot())
        except Exception as exc:
            trace = CommandTrace(
                command_id=command_id,
                command=normalized,
                status="failed",
                rule_results=rule_results,
                effect_results=effect_results,
                failure_reason=f"effect execution failed: {exc}",
            )
            return CommandResult("failed", trace, self._state_store.snapshot())

        changeset = transaction.changeset()
        self._state_store.apply_changeset(changeset)
        self._increment_command_index()
        presentation = self._scene_orchestrator.select(self._state_store.snapshot(), context)
        trace = CommandTrace(
            command_id=command_id,
            command=normalized,
            status="succeeded",
            rule_results=rule_results,
            effect_results=effect_results,
            changeset=changeset,
            presentation=presentation,
        )
        return CommandResult("succeeded", trace, self._state_store.snapshot())

    def _failed_result(self, command_id: str, command: Command, reason: str) -> CommandResult:
        trace = CommandTrace(
            command_id=command_id,
            command=command,
            status="failed",
            failure_reason=reason,
        )
        return CommandResult("failed", trace, self._state_store.snapshot())

    def _next_command_id(self) -> str:
        state = self._state_store.snapshot()
        current = int(state.get("diagnostics_state", {}).get("command_index", 0))
        return f"cmd.{current + 1:06d}"

    def _increment_command_index(self) -> None:
        state = self._state_store.snapshot()
        current = int(state.get("diagnostics_state", {}).get("command_index", 0))
        self._state_store.set_value(["diagnostics_state", "command_index"], current + 1)
