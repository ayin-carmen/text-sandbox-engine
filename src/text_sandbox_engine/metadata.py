"""Editor-facing metadata for built-in commands, rules, and effects."""

from __future__ import annotations

from typing import Any

from .registry import Registry


def register_builtin_metadata(registry: Registry) -> None:
    definitions: list[dict[str, Any]] = [
        _command("space.travel_to", "移动实体到相邻地点", [
            _param("actor", "entity", True, "actor.player"),
            _param("target", "location", True, "location.market_square"),
        ]),
        _command("narrative.choose", "执行场景选项", [
            _param("actor", "entity", True, "actor.player"),
            _param("target", "scene", True, "scene.greybrook.market_baker"),
            _param("choice_index", "integer", True, 0),
        ]),
        _rule("actor.is_present", "角色与命令执行者处于同一地点", [
            _param("actor", "actor", True, "actor.elda"),
        ], reads=["entities.*.components.location.current"]),
        _rule("flag.is_false", "旗标必须为 false", [
            _param("flag", "string", True, "accepted_bread_delivery"),
        ], reads=["flags.*"]),
        _rule("inventory.has_item", "角色拥有物品", [
            _param("actor", "actor", True, "actor.player"),
            _param("item", "item", True, "item.bread_basket"),
        ], reads=["entities.*.components.inventory.items"]),
        _rule("social.trust_at_least", "角色信任度达到阈值", [
            _param("actor", "actor", True, "actor.elda"),
            _param("minimum", "integer", True, 1),
        ], reads=["entities.*.components.relationship.trust"]),
        _rule("quest.stage_is", "任务处于指定阶段", [
            _param("quest", "quest", True, "quest.bread_delivery"),
            _param("stage", "string", True, "accepted"),
        ], reads=["globals.quests.*.stage"]),
        _rule("space.location_connected", "目标地点与当前地点相连", [
            _param("actor", "actor", True, "actor.player"),
            _param("target", "location", True, "location.market_square"),
        ], reads=["entities.*.components.location.current", "entities.*.components.map_node.connections"]),
        _rule("space.location_accessible", "地点允许进入", [
            _param("location", "location", True, "location.lord_keep"),
        ], reads=["entities.*.components.access"]),
        _rule("time.period_in", "当前时间段属于允许集合", [
            _param("period", "string", True, "morning"),
        ], reads=["globals.clock.period"]),
        _rule("narrative.scene_not_seen", "场景尚未被看过", [
            _param("scene", "scene", True, "scene.greybrook.market_baker"),
        ], reads=["globals.narrative.seen_scenes"]),
        _effect("flag.set", "设置旗标", [
            _param("flag", "string", True, "accepted_bread_delivery"),
            _param("value", "boolean", True, True),
        ], writes=["flags.*"]),
        _effect("inventory.add_item", "向角色背包添加物品", [
            _param("actor", "actor", True, "actor.player"),
            _param("item", "item", True, "item.bread_basket"),
        ], writes=["entities.*.components.inventory.items"]),
        _effect("inventory.remove_item", "从角色背包移除物品", [
            _param("actor", "actor", True, "actor.player"),
            _param("item", "item", True, "item.bread_basket"),
        ], writes=["entities.*.components.inventory.items"]),
        _effect("social.adjust_trust", "调整角色信任度", [
            _param("actor", "actor", True, "actor.elda"),
            _param("amount", "integer", True, 1),
        ], writes=["entities.*.components.relationship.trust"]),
        _effect("quest.set_stage", "设置任务阶段", [
            _param("quest", "quest", True, "quest.bread_delivery"),
            _param("stage", "string", True, "accepted"),
        ], writes=["globals.quests.*.stage"]),
        _effect("quest.complete", "完成任务", [
            _param("quest", "quest", True, "quest.bread_delivery"),
        ], writes=["globals.quests.*.stage", "globals.quests.*.completed"]),
        _effect("space.move_entity", "移动实体", [
            _param("actor", "actor", True, "actor.player"),
            _param("location", "location", True, "location.market_square"),
        ], writes=["entities.*.components.location.current"]),
        _effect("time.advance", "推进时间刻度", [
            _param("amount", "integer", True, 1),
        ], writes=["globals.clock.tick"]),
        _effect("narrative.mark_scene_seen", "记录场景已查看", [
            _param("scene", "scene", True, "scene.greybrook.market_baker"),
        ], writes=["globals.narrative.seen_scenes"]),
    ]
    for definition in definitions:
        kind = definition["kind"]
        type_id = definition["type_id"]
        if kind == "command":
            registry._set_metadata(kind, type_id, definition)
        elif kind == "rule":
            registry._set_metadata(kind, type_id, definition)
        else:
            registry._set_metadata(kind, type_id, definition)


def _param(name: str, data_type: str, required: bool, default: Any) -> dict[str, Any]:
    return {"name": name, "data_type": data_type, "required": required, "default": default}


def _base(kind: str, type_id: str, description: str, parameters: list[dict[str, Any]]) -> dict[str, Any]:
    return {"kind": kind, "type_id": type_id, "description": description, "parameters": parameters}


def _command(type_id: str, description: str, parameters: list[dict[str, Any]]) -> dict[str, Any]:
    return _base("command", type_id, description, parameters)


def _rule(type_id: str, description: str, parameters: list[dict[str, Any]], reads: list[str]) -> dict[str, Any]:
    result = _base("rule", type_id, description, parameters)
    result["reads"] = reads
    return result


def _effect(type_id: str, description: str, parameters: list[dict[str, Any]], writes: list[str]) -> dict[str, Any]:
    result = _base("effect", type_id, description, parameters)
    result["writes"] = writes
    return result
