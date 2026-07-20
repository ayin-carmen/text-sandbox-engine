# Phase 0 Content Schema Draft

This document explains the first content shapes used by the engine. The concrete draft schemas live in `schemas/`.

The schema goal is deliberately small: enough to validate minimal entities, world state, scenes, rules, and effects before the Python prototype exists.

## Content Package Shape

Initial content packages should use this structure:

```text
content/
  entities/
    *.json
  scenes/
    *.json
```

The first prototype may load files directly from folders. A package manifest can be added later when module and dependency metadata becomes necessary.

## Entity Content

An entity is any world object with an identity.

Examples:

1. Player.
2. NPC.
3. Location.
4. Item.
5. Faction.
6. Quest.

Required fields:

1. `id`
2. `type`
3. `components`

Optional fields:

1. `tags`
2. `metadata`

Example:

```json
{
  "id": "location.market",
  "type": "location",
  "tags": ["public", "trade"],
  "components": {
    "description": {
      "name": "市场",
      "text": "石板路两旁挤满摊贩、布棚和讨价还价的人群。"
    },
    "map_node": {
      "region": "town",
      "connections": ["location.town_square"]
    }
  }
}
```

## World State

World state is runtime data, not authoring content.

It contains:

1. Runtime and schema versions.
2. Deterministic seed.
3. Entity state.
4. Global values.
5. Flags.
6. History and cooldowns.
7. Runtime diagnostics metadata.

State must be serializable to JSON without custom Python objects.

## Scene Content

A scene is an interactive presentation unit.

Required fields:

1. `id`
2. `scope`
3. `priority`
4. `conditions`
5. `text`
6. `choices`

Each choice can expose:

1. A label.
2. Optional visibility rules.
3. Effects.
4. Optional command forwarding in a later version.

Example:

```json
{
  "id": "scene.market_intro",
  "scope": {
    "location": "location.market"
  },
  "priority": 10,
  "conditions": [
    {
      "rule": "time.period_in",
      "args": ["morning", "afternoon"]
    },
    {
      "rule": "flag.is_false",
      "args": ["met_market"]
    }
  ],
  "text": "你第一次走进市场，空气里混着面包、湿羊毛和铜币的气味。",
  "choices": [
    {
      "text": "四处看看",
      "effects": [
        {
          "effect": "flag.set",
          "args": ["met_market", true]
        },
        {
          "effect": "time.advance",
          "args": [1]
        }
      ]
    }
  ]
}
```

## Rule Reference

Rule references are data records that call registered rule handlers.

Draft fields:

1. `rule`
2. `args`
3. `metadata`

Rules must be side-effect free.

## Effect Reference

Effect references are data records that call registered effect handlers.

Draft fields:

1. `effect`
2. `args`
3. `metadata`

Effects must produce explicit state changes through a transaction.

## Validation Rules

The first validator should check:

1. JSON syntax.
2. Required fields.
3. Unique entity and scene IDs.
4. Known component names.
5. Known rule names.
6. Known effect names.
7. Valid entity references.
8. Valid scene choice structure.

## Deferred Decisions

These are intentionally not finalized in phase 0:

1. Full module manifest format.
2. Full component schema language.
3. Localization file format.
4. Weighted random scene selection.
5. Content filtering policy details.
6. Editor tooling.
