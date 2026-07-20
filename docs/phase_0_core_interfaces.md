# Phase 0 Core Interface Draft

This draft freezes the smallest shared vocabulary needed before the first Python prototype.

The goal is not to finalize every gameplay system. The goal is to define stable boundaries so that the first runtime can execute commands, check rules, apply effects, persist state, and explain what happened.

## Runtime Boundary

`Runtime` is the public entry point used by a CLI, test harness, or future UI.

Required responsibilities:

1. Create a new world from content.
2. Restore a world from a save file.
3. Execute a command.
4. Return a structured result with presentation data and diagnostics.

Draft shape:

```python
class Runtime:
    def new_game(self, content_path: str, seed: int) -> "WorldState":
        ...

    def load_game(self, save_path: str) -> "WorldState":
        ...

    def execute(self, command: "Command") -> "CommandResult":
        ...

    def save_game(self, save_path: str) -> "SaveReport":
        ...
```

## StateStore

`StateStore` is the only source of truth for world state.

Required responsibilities:

1. Read entities and globals.
2. Apply committed changesets.
3. Expose immutable snapshots for rules and scene selection.
4. Maintain deterministic runtime metadata such as seed and command index.

Draft shape:

```python
class StateStore:
    def snapshot(self) -> "WorldState":
        ...

    def get_entity(self, entity_id: str) -> "Entity":
        ...

    def apply_changeset(self, changeset: "ChangeSet") -> None:
        ...
```

## Registry

`Registry` stores all extension points provided by core and modules.

Required registries:

1. Component schemas.
2. Command handlers.
3. Rule handlers.
4. Effect handlers.
5. Content validators.
6. Migrations.

Draft shape:

```python
class Registry:
    def register_rule(self, rule_type: str, handler: "RuleHandler") -> None:
        ...

    def register_effect(self, effect_type: str, handler: "EffectHandler") -> None:
        ...

    def get_rule(self, rule_type: str) -> "RuleHandler":
        ...

    def get_effect(self, effect_type: str) -> "EffectHandler":
        ...
```

## CommandPipeline

`CommandPipeline` owns the command lifecycle.

Required flow:

1. Normalize command.
2. Build execution context.
3. Validate rules.
4. Build transaction.
5. Apply effects.
6. Commit changes.
7. Select presentation.
8. Return trace.

Draft shape:

```python
class CommandPipeline:
    def execute(self, command: "Command") -> "CommandResult":
        ...
```

## RuleEngine

Rules are read-only checks. They must not change state.

Rule result fields:

1. `passed`
2. `rule_type`
3. `args`
4. `reason`
5. `observed`

Draft shape:

```python
class RuleEngine:
    def evaluate(self, rule_ref: "RuleRef", context: "CommandContext") -> "RuleResult":
        ...
```

## EffectEngine

Effects describe state changes. They must run inside a transaction.

Effect result fields:

1. `applied`
2. `effect_type`
3. `args`
4. `changes`
5. `reason`

Draft shape:

```python
class EffectEngine:
    def apply(self, effect_ref: "EffectRef", transaction: "Transaction") -> "EffectResult":
        ...
```

## TransactionManager

Transactions make state changes atomic and traceable.

Required responsibilities:

1. Collect changes before commit.
2. Reject invalid or conflicting changes.
3. Commit all accepted changes together.
4. Produce a `ChangeSet`.

Draft shape:

```python
class Transaction:
    def set_component_value(self, entity_id: str, component: str, path: str, value: object) -> None:
        ...

    def set_global_value(self, path: str, value: object) -> None:
        ...

    def changeset(self) -> "ChangeSet":
        ...
```

## ContentRepository

`ContentRepository` loads, validates, indexes, and exposes content data.

Required responsibilities:

1. Load JSON or YAML content files.
2. Validate schemas.
3. Validate references.
4. Report unknown rules and effects.
5. Query scenes by scope, tags, and conditions.

## SceneOrchestrator

`SceneOrchestrator` decides what the player sees after state changes.

Required responsibilities:

1. Build scene context from state.
2. Collect candidate scenes.
3. Evaluate scene conditions.
4. Apply priority and repeat policy.
5. Return selected scene and candidate report.

## Persistence

Persistence must be versioned from the first prototype.

Required save metadata:

1. `engine_version`
2. `schema_version`
3. `enabled_modules`
4. `module_versions`
5. `world_state`
6. `random_state`
7. `migration_history`

## Diagnostics

Diagnostics must explain command execution, not only report errors.

Minimum reports:

1. `CommandTrace`
2. `RuleTrace`
3. `EffectTrace`
4. `ChangeSet`
5. `SceneCandidateReport`
6. `ContentValidationReport`

## First Prototype Acceptance Criteria

The first Python prototype should pass these checks:

1. A command can be executed through `Runtime.execute`.
2. A failed rule produces no state changes.
3. A successful command produces a `ChangeSet`.
4. The selected scene is determined after the state commit.
5. The command result includes a readable trace.
6. A save/load roundtrip preserves world state.
