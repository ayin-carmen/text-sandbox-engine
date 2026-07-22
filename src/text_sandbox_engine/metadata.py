"""Editor-facing metadata for built-in commands, rules, and effects."""

from __future__ import annotations

from typing import Any

from .registry import Registry


def register_builtin_metadata(registry: Registry) -> None:
    definitions: list[dict[str, Any]] = [
        _command("space.travel_to", "移动实体到相邻地点", [
            _param("actor", "entity", True, "actor.player", reference_type="actor"),
            _param("target", "location", True, "location.market_square"),
        ]),
        _command("narrative.choose", "执行场景选项", [
            _param("actor", "entity", True, "actor.player", reference_type="actor"),
            _param("target", "scene", True, "scene.greybrook.market_baker"),
            _param("choice_index", "integer", True, 0),
        ]),
        _rule("actor.is_present", "角色与命令执行者处于同一地点", [
            _param("actor", "actor", True, "actor.elda"),
        ], reads=["entities.*.components.location.current"]),
        _rule("flag.is_false", "旗标必须为 false", [
            _param("flag", "string", True, "accepted_bread_delivery", reference_type="flag"),
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
            _param("flag", "string", True, "accepted_bread_delivery", reference_type="flag"),
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


def _param(
    name: str,
    data_type: str,
    required: bool,
    default: Any,
    *,
    reference_type: str | None = None,
) -> dict[str, Any]:
    reference_type = reference_type or {
        "actor": "actor",
        "location": "location",
        "item": "item",
        "quest": "quest",
        "scene": "scene",
    }.get(data_type)
    widget = {
        "boolean": "boolean",
        "integer": "integer",
        "number": "number",
    }.get(data_type, "reference_select" if reference_type else "text")
    labels = {
        "actor": "角色",
        "amount": "数量",
        "flag": "Flag",
        "location": "地点",
        "minimum": "最低值",
        "period": "时间段",
        "item": "物品",
        "quest": "任务",
        "scene": "场景",
        "stage": "阶段",
        "target": "目标",
        "value": "值",
        "choice_index": "选项序号",
    }
    descriptions = {
        "actor": "执行操作或接收效果的角色",
        "amount": "要调整或推进的数量",
        "flag": "状态旗标名称",
        "location": "目标地点",
        "minimum": "要求达到的最低数值",
        "period": "允许的时间段名称",
        "item": "引用的物品",
        "quest": "引用的任务",
        "scene": "引用的场景",
        "stage": "任务阶段名称",
        "target": "操作目标",
        "value": "要写入的值",
        "choice_index": "从零开始计算的选项序号",
    }
    result: dict[str, Any] = {
        "name": name,
        "label": labels.get(name, name),
        "data_type": data_type,
        "widget": widget,
        "required": required,
        "default": default,
        "description": descriptions.get(name, f"参数：{name}"),
    }
    if reference_type:
        result["reference_type"] = reference_type
    return result


def _base(kind: str, type_id: str, description: str, parameters: list[dict[str, Any]]) -> dict[str, Any]:
    labels = {
        "space.travel_to": "移动到地点",
        "narrative.choose": "选择场景选项",
        "actor.is_present": "角色在场",
        "flag.is_false": "Flag 未设置",
        "inventory.has_item": "拥有物品",
        "social.trust_at_least": "信任度达到",
        "quest.stage_is": "任务处于阶段",
        "space.location_connected": "地点可通行",
        "space.location_accessible": "地点可进入",
        "time.period_in": "处于时间段",
        "narrative.scene_not_seen": "场景未查看",
        "flag.set": "设置 Flag",
        "inventory.add_item": "获得物品",
        "inventory.remove_item": "移除物品",
        "social.adjust_trust": "调整信任度",
        "quest.set_stage": "推进任务阶段",
        "quest.complete": "完成任务",
        "space.move_entity": "移动角色",
        "time.advance": "推进时间",
        "narrative.mark_scene_seen": "记录场景已查看",
    }
    categories = {
        "actor": "角色",
        "flag": "状态",
        "inventory": "物品",
        "social": "关系",
        "quest": "任务",
        "space": "地点",
        "time": "时间",
        "narrative": "叙事",
    }
    module = type_id.split(".", 1)[0]
    return {
        "kind": kind,
        "type_id": type_id,
        "label": labels.get(type_id, type_id),
        "category": categories.get(module, module),
        "description": description,
        "module": module,
        "module_version": "1.0.0",
        "parameters": parameters,
    }


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
