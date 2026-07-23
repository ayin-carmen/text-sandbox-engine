"""Workspace, content, runtime, and diagnostic services for the editor."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

from text_sandbox_engine.builtins import register_builtins
from text_sandbox_engine.content import ContentRepository
from text_sandbox_engine.debug import changed_by_report, replay_commands, scene_candidate_report
from text_sandbox_engine.diagnostics import state_diff, to_plain_data
from text_sandbox_engine.engines import RuleEngine
from text_sandbox_engine.models import Command, RuleRef
from text_sandbox_engine.persistence import load_world_state
from text_sandbox_engine.registry import Registry
from text_sandbox_engine.runtime import Runtime


class RevisionConflict(ValueError):
    """Raised when a file changed after the client read it."""


class EditorService:
    def __init__(self) -> None:
        self.workspace_root: Path | None = None
        self.content_root: Path | None = None
        self.state_path: Path | None = None
        self._sessions: dict[str, dict[str, Any]] = {}

    def open_workspace(self, root: str | Path) -> dict[str, Any]:
        workspace = Path(root).expanduser().resolve()
        if not workspace.exists() or not workspace.is_dir():
            raise ValueError(f"workspace does not exist: {workspace}")
        content_root = workspace / "content"
        if not content_root.exists():
            content_root = workspace
        state_path = workspace / "world_state.json"
        if not state_path.exists():
            candidates = sorted(workspace.glob("*.json"))
            state_path = candidates[0] if candidates else None
        if state_path is None:
            raise ValueError("workspace does not contain a world_state JSON file")
        self.workspace_root = workspace
        self.content_root = content_root
        self.state_path = state_path
        self._sessions.clear()
        return self.current_workspace()

    def current_workspace(self) -> dict[str, Any]:
        self._require_workspace()
        return {
            "root": str(self.workspace_root),
            "content_root": str(self.content_root),
            "state_path": str(self.state_path),
            "scene_count": len(self._scene_records()),
        }

    def tree(self) -> dict[str, Any]:
        self._require_workspace()
        assert self.workspace_root is not None
        entries = []
        for path in sorted(self.workspace_root.rglob("*")):
            if not path.is_file() or any(part in {"__pycache__", ".git"} for part in path.parts):
                continue
            relative = path.relative_to(self.workspace_root).as_posix()
            entries.append({
                "path": relative,
                "kind": self._file_kind(path),
                "revision": _revision(path),
            })
        schema_root = self._schema_root()
        if schema_root and schema_root.exists() and schema_root != self.workspace_root:
            for path in sorted(schema_root.rglob("*.json")):
                entries.append({
                    "path": f"../{schema_root.name}/{path.relative_to(schema_root).as_posix()}",
                    "kind": "schema",
                    "revision": _revision(path),
                })
        return {"root": str(self.workspace_root), "entries": entries}

    def refresh(self) -> dict[str, Any]:
        return self.tree()

    def source_state(self) -> dict[str, Any]:
        self._require_workspace()
        assert self.state_path is not None
        return {"state": load_world_state(self.state_path), "path": str(self.state_path), "revision": _revision(self.state_path)}

    def entity_types(self) -> dict[str, Any]:
        return {"types": [dict(item) for item in _ENTITY_TYPES]}

    def entity_templates(self) -> dict[str, Any]:
        return {"templates": [dict(item) for item in _ENTITY_TEMPLATES]}

    def entities(self, entity_type: str | None = None, query: str | None = None) -> dict[str, Any]:
        self._require_workspace()
        assert self.state_path is not None
        state = load_world_state(self.state_path)
        normalized_query = query.strip().casefold() if query else ""
        result: list[dict[str, Any]] = []
        for entity_id, document in state.get("entities", {}).items():
            if not isinstance(document, dict):
                continue
            kind = str(document.get("type", ""))
            if entity_type and kind != entity_type:
                continue
            label = _entity_label(document, entity_id)
            tags = [str(tag) for tag in document.get("tags", []) if isinstance(tag, str)]
            haystack = " ".join([entity_id, label, *tags]).casefold()
            if normalized_query and normalized_query not in haystack:
                continue
            result.append({
                "id": entity_id,
                "type": kind,
                "label": label,
                "tags": tags,
                "path": f"{self._source_label(self.state_path)}#/entities/{entity_id}",
                "revision": _revision(self.state_path),
                "diagnostic_count": len(self._validate_entity_document(document, state, entity_id)),
            })
        return {"entities": sorted(result, key=lambda item: (item["type"], item["label"], item["id"]))}

    def entity(self, entity_id: str) -> dict[str, Any]:
        self._require_workspace()
        assert self.state_path is not None
        state = load_world_state(self.state_path)
        document = state.get("entities", {}).get(entity_id)
        if not isinstance(document, dict):
            raise KeyError(f"entity not found: {entity_id}")
        return {
            "id": entity_id,
            "type": document.get("type"),
            "path": f"{self._source_label(self.state_path)}#/entities/{entity_id}",
            "revision": _revision(self.state_path),
            "document": document,
        }

    def entity_from_template(
        self,
        *,
        entity_type: str,
        namespace: str,
        slug: str,
        name: str,
        tags: list[str],
        location: str | None = None,
        template_id: str = "basic",
        preview: bool = False,
    ) -> dict[str, Any]:
        self._require_workspace()
        template = next((item for item in _ENTITY_TEMPLATES if item["id"] == template_id and item["type"] == entity_type), None)
        if template is None:
            raise ValueError(f"unknown entity template: {entity_type}/{template_id}")
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", namespace):
            raise ValueError("namespace must contain lowercase letters, digits, underscores, or hyphens")
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", slug):
            raise ValueError("slug must start with a lowercase letter and contain only lowercase letters, digits, underscores, or hyphens")
        entity_id = f"{entity_type}.{namespace}.{slug}"
        assert self.state_path is not None
        state = load_world_state(self.state_path)
        if entity_id in state.get("entities", {}):
            raise ValueError(f"entity id already exists: {entity_id}")
        document = deepcopy(template["document"])
        document["id"] = entity_id
        document["tags"] = list(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))
        if name.strip():
            _set_entity_name(document, name.strip())
        if entity_type == "actor" and location:
            document.setdefault("components", {}).setdefault("location", {})["current"] = location
        if entity_type == "location" and location:
            document.setdefault("components", {}).setdefault("map_node", {})["connections"] = [location]
        report = self.validate_world_state({**state, "entities": {**state.get("entities", {}), entity_id: document}})
        entity_issues = [issue for issue in report["issues"] if issue.get("json_path", "").startswith(f'$.entities["{entity_id}"]')]
        result = {
            "id": entity_id,
            "requested_id": entity_id,
            "template": template_id,
            "document": document,
            "issues": entity_issues,
            "passed": not entity_issues,
            "conflict_resolved": False,
        }
        if preview:
            return result
        if entity_issues:
            raise ValueError(json.dumps({"passed": False, "issues": entity_issues}, ensure_ascii=False))
        return {**result, "entity": self.create_entity(document)}

    def create_entity(self, document: dict[str, Any]) -> dict[str, Any]:
        self._require_workspace()
        assert self.state_path is not None
        state = load_world_state(self.state_path)
        entity_id = str(document.get("id", ""))
        if entity_id in state.get("entities", {}):
            raise ValueError(f"entity id already exists: {entity_id}")
        next_state = deepcopy(state)
        next_state.setdefault("entities", {})[entity_id] = deepcopy(document)
        report = self.validate_world_state(next_state)
        if report["issues"]:
            raise ValueError(json.dumps(report, ensure_ascii=False))
        _atomic_json_write(self.state_path, next_state)
        return self.entity(entity_id)

    def save_entity(self, entity_id: str, document: dict[str, Any], revision: str) -> dict[str, Any]:
        self._require_workspace()
        assert self.state_path is not None
        self._assert_revision(self.state_path, revision)
        state = load_world_state(self.state_path)
        current = state.get("entities", {}).get(entity_id)
        if not isinstance(current, dict):
            raise KeyError(f"entity not found: {entity_id}")
        if document.get("id") != entity_id:
            raise ValueError("entity id cannot be changed through the save endpoint")
        if document.get("type") != current.get("type"):
            raise ValueError("entity type cannot be changed through the save endpoint")
        next_state = deepcopy(state)
        next_state["entities"][entity_id] = deepcopy(document)
        report = self.validate_world_state(next_state)
        if report["issues"]:
            raise ValueError(json.dumps(report, ensure_ascii=False))
        _atomic_json_write(self.state_path, next_state)
        return self.entity(entity_id)

    def delete_entity(self, entity_id: str, revision: str) -> dict[str, Any]:
        self._require_workspace()
        assert self.state_path is not None
        self._assert_revision(self.state_path, revision)
        state = load_world_state(self.state_path)
        if entity_id not in state.get("entities", {}):
            raise KeyError(f"entity not found: {entity_id}")
        usages = self.entity_usages(entity_id)["usages"]
        if usages:
            raise RevisionConflict(json.dumps({"entity_id": entity_id, "usages": usages}, ensure_ascii=False))
        next_state = deepcopy(state)
        del next_state["entities"][entity_id]
        report = self.validate_world_state(next_state)
        if report["issues"]:
            raise ValueError(json.dumps(report, ensure_ascii=False))
        _atomic_json_write(self.state_path, next_state)
        return {"deleted": entity_id}

    def validate_world_state(self, state: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require_workspace()
        assert self.state_path is not None
        current = deepcopy(state) if state is not None else load_world_state(self.state_path)
        issues: list[dict[str, Any]] = []
        entities = current.get("entities")
        if not isinstance(entities, dict):
            return {"passed": False, "issues": [_issue("world.schema_violation", "entities 必须是对象", self.state_path, "$.entities")]}
        for entity_id, document in entities.items():
            issues.extend(self._validate_entity_document(document, current, str(entity_id)))
        known = {str(key): value.get("type") for key, value in entities.items() if isinstance(value, dict)}
        for entity_id, document in entities.items():
            if not isinstance(document, dict):
                continue
            components = document.get("components", {})
            if not isinstance(components, dict):
                continue
            location = components.get("location", {}).get("current") if isinstance(components.get("location"), dict) else None
            if location and known.get(location) != "location":
                issues.append(_issue("reference.missing_target", f"找不到地点引用：{location}", self.state_path, _entity_json_path(str(entity_id), "components.location.current"), str(entity_id), "请选择已有地点。"))
            items = components.get("inventory", {}).get("items", []) if isinstance(components.get("inventory"), dict) else []
            if isinstance(items, list):
                for index, item_id in enumerate(items):
                    if isinstance(item_id, str) and known.get(item_id) not in {"item", None}:
                        issues.append(_issue("reference.missing_target", f"找不到物品引用：{item_id}", self.state_path, _entity_json_path(str(entity_id), f"components.inventory.items[{index}]"), str(entity_id), "请选择已有物品。"))
            connections = components.get("map_node", {}).get("connections", []) if isinstance(components.get("map_node"), dict) else []
            if isinstance(connections, list):
                for index, target in enumerate(connections):
                    if isinstance(target, str) and known.get(target) != "location":
                        issues.append(_issue("reference.missing_target", f"找不到相邻地点：{target}", self.state_path, _entity_json_path(str(entity_id), f"components.map_node.connections[{index}]"), str(entity_id), "请选择已有地点。"))
        return {"passed": not issues, "issues": issues}

    def _validate_entity_document(self, document: Any, state: dict[str, Any], entity_id: str) -> list[dict[str, Any]]:
        assert self.state_path is not None
        base = f'$.entities["{entity_id}"]'
        issues: list[dict[str, Any]] = []
        if not isinstance(document, dict):
            return [_issue("world.entity_schema_violation", "实体必须是对象", self.state_path, base, entity_id)]
        if document.get("id") != entity_id:
            issues.append(_issue("world.entity_id_mismatch", "实体 id 必须与 entities key 一致", self.state_path, f"{base}.id", entity_id, "请保持实体 ID 与列表中的稳定 ID 一致。"))
        entity_type = document.get("type")
        if entity_type not in {item["id"] for item in _ENTITY_TYPES}:
            issues.append(_issue("world.unsupported_entity_type", f"暂不支持的实体类型：{entity_type}", self.state_path, f"{base}.type", entity_id, "请选择角色、地点或物品。"))
        elif not re.fullmatch(rf"{re.escape(str(entity_type))}(\.[a-z][a-z0-9_]*)+", entity_id):
            issues.append(_issue("world.invalid_entity_id", f"{entity_type} 的 ID 格式无效：{entity_id}", self.state_path, base, entity_id, f"请使用 {entity_type}.namespace.slug 格式。"))
        if not isinstance(document.get("components"), dict) or not document.get("components"):
            issues.append(_issue("world.entity_schema_violation", "实体 components 必须是非空对象", self.state_path, f"{base}.components", entity_id, "请使用实体模板创建基础组件。"))
        if not isinstance(document.get("tags", []), list) or not all(isinstance(tag, str) and tag.strip() for tag in document.get("tags", [])):
            issues.append(_issue("world.entity_schema_violation", "实体 tags 必须是字符串数组", self.state_path, f"{base}.tags", entity_id))
        return issues

    def entity_usages(self, entity_id: str) -> dict[str, Any]:
        self._require_workspace()
        assert self.state_path is not None
        state = load_world_state(self.state_path)
        usages: list[dict[str, Any]] = []
        for owner_id, document in state.get("entities", {}).items():
            if not isinstance(document, dict):
                continue
            components = document.get("components", {})
            if not isinstance(components, dict):
                continue
            if components.get("location", {}).get("current") == entity_id:
                usages.append({"source": self._source_label(self.state_path), "json_path": _entity_json_path(str(owner_id), "components.location.current"), "kind": "entity", "description": f"{owner_id} 的当前地点"})
            items = components.get("inventory", {}).get("items", [])
            if isinstance(items, list):
                for index, value in enumerate(items):
                    if value == entity_id:
                        usages.append({"source": self._source_label(self.state_path), "json_path": _entity_json_path(str(owner_id), f"components.inventory.items[{index}]"), "kind": "entity", "description": f"{owner_id} 的背包物品"})
            connections = components.get("map_node", {}).get("connections", [])
            if isinstance(connections, list):
                for index, value in enumerate(connections):
                    if value == entity_id:
                        usages.append({"source": self._source_label(self.state_path), "json_path": _entity_json_path(str(owner_id), f"components.map_node.connections[{index}]"), "kind": "entity", "description": f"{owner_id} 的相邻地点"})
        for record in self._scene_records():
            document = record["document"]
            if document.get("scope", {}).get("location") == entity_id:
                usages.append({"source": self._source_label(Path(record["path"])), "json_path": "$.scope.location", "kind": "scene", "description": f"场景 {record['id']} 的所属地点"})
            for kind, type_id, args, json_path in _scene_argument_paths(document, self._registry()):
                for index, value in enumerate(args):
                    if value == entity_id:
                        usages.append({"source": self._source_label(Path(record["path"])), "json_path": f"{json_path}[{index}]", "kind": kind, "description": f"场景 {record['id']} 的 {type_id} 引用"})
        return {"entity_id": entity_id, "usages": usages}

    def scenes(self) -> list[dict[str, Any]]:
        return self._scene_records()

    def scene(self, scene_id: str) -> dict[str, Any]:
        for record in self._scene_records():
            if record["id"] == scene_id:
                return record
        raise KeyError(f"scene not found: {scene_id}")

    def save_scene(self, scene_id: str, document: dict[str, Any], revision: str) -> dict[str, Any]:
        record = self.scene(scene_id)
        path = Path(record["path"])
        self._assert_revision(path, revision)
        issues = self.validate_document(document, path)
        if issues["issues"]:
            raise ValueError(json.dumps(issues, ensure_ascii=False))
        if document.get("id") != scene_id:
            raise ValueError("scene id cannot be changed through the save endpoint")
        _atomic_json_write(path, document)
        return self.scene(scene_id)

    def create_scene(self, document: dict[str, Any]) -> dict[str, Any]:
        self._require_workspace()
        scene_id = str(document.get("id", ""))
        if not scene_id or any(item["id"] == scene_id for item in self._scene_records()):
            raise ValueError("scene id is missing or already exists")
        issues = self.validate_document(document, None)
        if issues["issues"]:
            raise ValueError(json.dumps(issues, ensure_ascii=False))
        path = self._scene_path_for_id(scene_id)
        if path.exists():
            raise ValueError(f"scene file already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_json_write(path, document)
        return self.scene(scene_id)

    def scene_templates(self) -> dict[str, Any]:
        return {"templates": [dict(template) for template in _SCENE_TEMPLATES]}

    def scene_from_template(
        self,
        *,
        name: str,
        namespace: str,
        slug: str,
        location: str,
        template_id: str,
        repeat_policy: str,
        priority: int,
        preview: bool = False,
    ) -> dict[str, Any]:
        self._require_workspace()
        template = next((item for item in _SCENE_TEMPLATES if item["id"] == template_id), None)
        if template is None:
            raise ValueError(f"unknown scene template: {template_id}")
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", namespace):
            raise ValueError("namespace must contain lowercase letters, digits, underscores, or hyphens")
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", slug):
            raise ValueError("slug must start with a lowercase letter and contain only lowercase letters, digits, underscores, or hyphens")
        if repeat_policy not in {"always", "once", "cooldown"}:
            raise ValueError("repeat_policy must be always, once, or cooldown")
        valid_locations = {item["id"] for item in self.references("location")["references"] if item["valid"]}
        if location not in valid_locations:
            raise ValueError(f"unknown location reference: {location}")
        base_id = f"scene.{namespace}.{slug}"
        scene_id = self._unique_scene_id(base_id)
        document = deepcopy(template["document"])
        document.update({
            "id": scene_id,
            "scope": {"location": location},
            "priority": priority,
            "repeat_policy": repeat_policy,
        })
        if name.strip():
            document["text"] = f"{name.strip()}\n\n{document['text']}"
        report = self.validate_document(document, None)
        result = {
            "id": scene_id,
            "requested_id": base_id,
            "template": template_id,
            "document": document,
            "issues": report["issues"],
            "passed": report["passed"],
            "conflict_resolved": scene_id != base_id,
        }
        if preview:
            return result
        if report["issues"]:
            raise ValueError(json.dumps(report, ensure_ascii=False))
        return {**result, "scene": self.create_scene(document)}

    def duplicate_scene(self, scene_id: str, new_scene_id: str, revision: str) -> dict[str, Any]:
        source = self.scene(scene_id)
        self._assert_revision(Path(source["path"]), revision)
        document = deepcopy(source["document"])
        document["id"] = new_scene_id
        return self.create_scene(document)

    def rename_scene(self, scene_id: str, new_scene_id: str, revision: str) -> dict[str, Any]:
        record = self.scene(scene_id)
        self._assert_revision(Path(record["path"]), revision)
        references = [edge for edge in self.graph()["edges"] if edge["target"] == scene_id]
        if references:
            raise RevisionConflict(json.dumps({"references": references}, ensure_ascii=False))
        document = deepcopy(record["document"])
        document["id"] = new_scene_id
        new_record = self.create_scene(document)
        Path(record["path"]).unlink()
        return new_record

    def delete_scene(self, scene_id: str, revision: str) -> dict[str, Any]:
        record = self.scene(scene_id)
        self._assert_revision(Path(record["path"]), revision)
        references = [edge for edge in self.graph()["edges"] if edge["target"] == scene_id]
        if references:
            raise RevisionConflict(json.dumps({"references": references}, ensure_ascii=False))
        Path(record["path"]).unlink()
        return {"deleted": scene_id}

    def validate_content(self) -> dict[str, Any]:
        self._require_workspace()
        registry = self._registry()
        issues: list[dict[str, Any]] = []
        seen_ids: dict[str, Path] = {}
        assert self.content_root is not None
        for path in _scene_files(self.content_root):
            try:
                document = _load_json(path)
            except (OSError, json.JSONDecodeError) as exc:
                issues.append(_issue("content.invalid_json", str(exc), path, "$"))
                continue
            scene_id = document.get("id")
            if isinstance(scene_id, str) and scene_id in seen_ids:
                issues.append(_issue("content.duplicate_id", f"duplicate scene id: {scene_id}", path, "$.id", scene_id))
            elif isinstance(scene_id, str):
                seen_ids[scene_id] = path
            issues.extend(self.validate_document(document, path)["issues"])
        return {
            "passed": not issues,
            "issues": issues,
            "scene_count": len(self._scene_records()),
        }

    def validate_document(self, document: dict[str, Any], path: Path | None) -> dict[str, Any]:
        registry = self._registry()
        issues: list[dict[str, Any]] = []
        if not isinstance(document, dict):
            issues.append(_issue("content.schema_violation", "document must be an object", path, "$"))
            return {"passed": False, "issues": issues}
        scene_id = document.get("id", "document")
        required = ["id", "scope", "priority", "conditions", "text", "choices"]
        for field_name in required:
            if field_name not in document:
                issues.append(_issue(
                    "content.schema_violation",
                    f"missing required field: {field_name}",
                    path,
                    f"$.{field_name}",
                    scene_id,
                ))
        if not isinstance(document.get("id"), str) or not str(document.get("id", "")).startswith("scene."):
            issues.append(_issue("content.schema_violation", "scene id must start with scene.", path, "$.id", scene_id))
        seen = set()
        scene_report = ContentRepository([document]).validate(registry=registry)
        for item in scene_report.issues:
            code = "registry.unknown_rule" if "unknown rule" in item.message else "registry.unknown_effect" if "unknown effect" in item.message else "content.schema_violation"
            if code == "content.schema_violation" and "duplicate" in item.message:
                code = "content.duplicate_id"
            json_path = _guess_json_path(item.path, item.message)
            if json_path in seen:
                continue
            seen.add(json_path)
            issues.append(_issue(code, item.message, path, json_path, scene_id))
        for choice_index, choice in enumerate(document.get("choices", []) if isinstance(document.get("choices", []), list) else []):
            for rule_index, rule in enumerate(choice.get("visible_if", []) if isinstance(choice, dict) else []):
                if isinstance(rule, dict) and rule.get("rule") not in _rule_ids(registry):
                    issues.append(_issue("registry.unknown_rule", f"unknown rule: {rule.get('rule')}", path, f"$.choices[{choice_index}].visible_if[{rule_index}].rule", scene_id))
            for effect_index, effect in enumerate(choice.get("effects", []) if isinstance(choice, dict) else []):
                if isinstance(effect, dict) and effect.get("effect") not in _effect_ids(registry):
                    issues.append(_issue("registry.unknown_effect", f"unknown effect: {effect.get('effect')}", path, f"$.choices[{choice_index}].effects[{effect_index}].effect", scene_id))

        existing_issue_keys = {(item["code"], item["json_path"]) for item in issues}
        known_references = {}
        if self.workspace_root is not None:
            known_references = {
                (item["type"], item["id"]): item
                for item in self.references()["references"]
            }

        def add_precise(code: str, message: str, json_path: str, suggestion: str | None = None) -> None:
            key = (code, json_path)
            if key in existing_issue_keys:
                return
            existing_issue_keys.add(key)
            issues.append(_issue(code, message, path, json_path, scene_id, suggestion=suggestion))

        def check_reference(reference_type: str | None, value: Any, json_path: str) -> None:
            if not reference_type or not isinstance(value, str) or reference_type == "item":
                return
            target = known_references.get((reference_type, value))
            if target is None or not target.get("valid", False):
                add_precise(
                    "reference.missing_target",
                    f"找不到{_REFERENCE_LABELS.get(reference_type, reference_type)}引用：{value}",
                    json_path,
                    f"请选择已有的{_REFERENCE_LABELS.get(reference_type, reference_type)}。",
                )

        def check_arguments(kind: str, type_id: Any, args: Any, json_path: str) -> None:
            if not isinstance(args, list):
                add_precise("content.schema_violation", "参数必须是数组", json_path, "请使用结构化参数控件或 JSON 数组。")
                return
            item = next((entry for entry in registry.metadata() if entry.get("kind") == kind and entry.get("type_id") == type_id), None)
            if item is None:
                return
            for index, parameter in enumerate(item.get("parameters", [])):
                parameter_path = f"{json_path}[{index}]"
                if parameter.get("required") and index >= len(args):
                    add_precise("content.missing_parameter", f"缺少参数：{parameter.get('label', parameter.get('name'))}", parameter_path, "请补充该参数。")
                    continue
                if index < len(args):
                    check_reference(parameter.get("reference_type"), args[index], parameter_path)

        check_reference("location", document.get("scope", {}).get("location"), "$.scope.location")
        for index, condition in enumerate(document.get("conditions", []) if isinstance(document.get("conditions"), list) else []):
            if isinstance(condition, dict):
                rule_id = condition.get("rule")
                if rule_id not in _rule_ids(registry):
                    add_precise("registry.unknown_rule", f"未知规则：{rule_id}", f"$.conditions[{index}].rule", "请选择 Registry 中已有的规则。")
                check_arguments("rule", rule_id, condition.get("args", []), f"$.conditions[{index}].args")
        for choice_index, choice in enumerate(document.get("choices", []) if isinstance(document.get("choices"), list) else []):
            if not isinstance(choice, dict):
                continue
            for rule_index, condition in enumerate(choice.get("visible_if", []) if isinstance(choice.get("visible_if"), list) else []):
                if isinstance(condition, dict):
                    rule_id = condition.get("rule")
                    base_path = f"$.choices[{choice_index}].visible_if[{rule_index}]"
                    if rule_id not in _rule_ids(registry):
                        add_precise("registry.unknown_rule", f"未知规则：{rule_id}", f"{base_path}.rule", "请选择 Registry 中已有的规则。")
                    check_arguments("rule", rule_id, condition.get("args", []), f"{base_path}.args")
            for effect_index, effect in enumerate(choice.get("effects", []) if isinstance(choice.get("effects"), list) else []):
                if isinstance(effect, dict):
                    effect_id = effect.get("effect")
                    base_path = f"$.choices[{choice_index}].effects[{effect_index}]"
                    if effect_id not in _effect_ids(registry):
                        add_precise("registry.unknown_effect", f"未知效果：{effect_id}", f"{base_path}.effect", "请选择 Registry 中已有的效果。")
                    check_arguments("effect", effect_id, effect.get("args", []), f"{base_path}.args")
        return {"passed": not issues, "issues": issues}

    def registry_metadata(self) -> dict[str, Any]:
        return {"items": self._registry().metadata()}

    def references(self, reference_type: str | None = None) -> dict[str, Any]:
        """Build low-code reference choices from the open workspace."""
        self._require_workspace()
        assert self.state_path is not None
        state = load_world_state(self.state_path)
        records = self._scene_records()
        source_path = self._source_label(self.state_path)
        known: dict[str, set[str]] = {kind: set() for kind in _REFERENCE_TYPES}
        entries: dict[tuple[str, str], dict[str, Any]] = {}

        def add(kind: str, ref_id: str, label: str, source: str, valid: bool = True) -> None:
            if kind not in _REFERENCE_TYPES or not isinstance(ref_id, str) or not ref_id:
                return
            if reference_type and kind != reference_type:
                return
            key = (kind, ref_id)
            current = entries.get(key)
            candidate = {
                "id": ref_id,
                "type": kind,
                "label": label or ref_id,
                "source": source,
                "valid": valid,
            }
            if current is None or (not current["valid"] and valid):
                entries[key] = candidate

        for entity_id, entity in state.get("entities", {}).items():
            if not isinstance(entity, dict):
                continue
            kind = entity.get("type")
            if kind not in {"actor", "location", "item", "quest"}:
                continue
            known[kind].add(entity_id)
            components = entity.get("components", {})
            profile = components.get("profile", {}) if isinstance(components, dict) else {}
            description = components.get("description", {}) if isinstance(components, dict) else {}
            label = profile.get("name") or description.get("name") or entity_id
            add(kind, entity_id, str(label), source_path)

        quests = state.get("globals", {}).get("quests", {})
        if isinstance(quests, dict):
            for quest_id, quest in quests.items():
                known["quest"].add(quest_id)
                label = quest.get("name") if isinstance(quest, dict) else None
                add("quest", quest_id, str(label or quest_id), source_path)

        flags = state.get("flags", {})
        if isinstance(flags, dict):
            for flag_id in flags:
                known["flag"].add(flag_id)
                add("flag", flag_id, flag_id, source_path)

        for record in records:
            scene_id = record["id"]
            known["scene"].add(scene_id)
            add("scene", scene_id, str(record["document"].get("title") or scene_id), self._source_label(Path(record["path"])))

        metadata = {(item["kind"], item["type_id"]): item for item in self._registry().metadata()}
        for record in records:
            document = record["document"]
            source = self._source_label(Path(record["path"]))
            location = document.get("scope", {}).get("location")
            if isinstance(location, str):
                add("location", location, location, source, location in known["location"])
            for kind, references in _document_reference_values(document):
                item = metadata.get((kind, references[0]))
                if item is None:
                    continue
                args = references[1]
                for index, parameter in enumerate(item.get("parameters", [])):
                    target_type = parameter.get("reference_type")
                    if target_type and index < len(args) and isinstance(args[index], str):
                        ref_id = args[index]
                        valid = ref_id in known[target_type]
                        if target_type == "item" and not valid:
                            # Item definitions are not separate documents yet; existing content refs form the first index.
                            known[target_type].add(ref_id)
                            valid = True
                        add(target_type, ref_id, ref_id, source, valid)

        return {"references": sorted(entries.values(), key=lambda item: (item["type"], item["label"], item["id"]))}

    def schemas(self) -> dict[str, Any]:
        self._require_workspace()
        assert self.workspace_root is not None
        schema_root = self._schema_root()
        result = []
        if schema_root and schema_root.exists():
            for path in sorted(schema_root.rglob("*.json")):
                result.append({"path": str(path), "document": _load_json(path)})
        return {"schemas": result}

    def graph(self) -> dict[str, Any]:
        self._require_workspace()
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        for record in self._scene_records():
            scene = record["document"]
            scene_id = record["id"]
            nodes[scene_id] = {"id": scene_id, "type": "scene", "label": scene_id, "path": record["path"]}
            location = scene.get("scope", {}).get("location")
            if location:
                self._node(nodes, location, "location", location)
                edges.append(_edge(scene_id, location, "requires", f"$.scope.location", record["path"]))
            for index, rule in enumerate(scene.get("conditions", [])):
                if not isinstance(rule, dict):
                    continue
                rule_id = f"rule:{rule.get('rule')}"
                self._node(nodes, rule_id, "rule", str(rule.get("rule")))
                edges.append(_edge(scene_id, rule_id, "reads", f"$.conditions[{index}]", record["path"]))
                self._reference_edges(nodes, edges, scene_id, rule.get("args", []), "requires", record["path"], f"$.conditions[{index}].args")
            for choice_index, choice in enumerate(scene.get("choices", [])):
                if not isinstance(choice, dict):
                    continue
                for rule_index, rule in enumerate(choice.get("visible_if", [])):
                    if isinstance(rule, dict):
                        rule_id = f"rule:{rule.get('rule')}"
                        self._node(nodes, rule_id, "rule", str(rule.get("rule")))
                        edges.append(_edge(scene_id, rule_id, "reads", f"$.choices[{choice_index}].visible_if[{rule_index}]", record["path"]))
                for effect_index, effect in enumerate(choice.get("effects", [])):
                    if not isinstance(effect, dict):
                        continue
                    effect_id = f"effect:{effect.get('effect')}"
                    self._node(nodes, effect_id, "effect", str(effect.get("effect")))
                    edges.append(_edge(scene_id, effect_id, "modifies", f"$.choices[{choice_index}].effects[{effect_index}]", record["path"]))
                    self._reference_edges(nodes, edges, scene_id, effect.get("args", []), "modifies", record["path"], f"$.choices[{choice_index}].effects[{effect_index}].args")
        return {"nodes": list(nodes.values()), "edges": edges}

    def create_session(self) -> dict[str, Any]:
        self._require_workspace()
        assert self.state_path is not None and self.content_root is not None
        session_id = f"session.{uuid.uuid4().hex[:12]}"
        runtime = Runtime.from_file(self.state_path, content_path=self.content_root)
        self._sessions[session_id] = {"runtime": runtime, "traces": [], "source_revision": _revision(self.state_path)}
        return {
            "session_id": session_id,
            "state": runtime.snapshot(),
            "traces": [],
            "actions": self.session_actions(session_id),
        }

    def session_command(self, session_id: str, command: dict[str, Any]) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        before = session["runtime"].snapshot()
        result = session["runtime"].execute(command)
        trace = to_plain_data(result.trace)
        session["traces"].append(trace)
        return {
            "status": result.status,
            "trace": trace,
            "state": result.state,
            "traces": session["traces"],
            "summary": self._command_summary(command, trace, before, result.state),
        }

    def session_state(self, session_id: str) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        return {"state": session["runtime"].snapshot(), "traces": session["traces"]}

    def reset_session(self, session_id: str) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        assert self.state_path is not None and self.content_root is not None
        session["runtime"] = Runtime.from_file(self.state_path, content_path=self.content_root)
        session["traces"] = []
        session["source_revision"] = _revision(self.state_path)
        return {"session_id": session_id, "state": session["runtime"].snapshot(), "traces": []}

    def session_actions(self, session_id: str, actor: str = "actor.player") -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        state = session["runtime"].snapshot()
        actor_state = state.get("entities", {}).get(actor, {})
        components = actor_state.get("components", {}) if isinstance(actor_state, dict) else {}
        current_location = components.get("location", {}).get("current") if isinstance(components, dict) else None
        labels = {(item["type"], item["id"]): item["label"] for item in self.references()["references"]}
        actions: list[dict[str, Any]] = []
        locations: list[dict[str, Any]] = []
        current_entity = state.get("entities", {}).get(current_location, {})
        connections = current_entity.get("components", {}).get("map_node", {}).get("connections", []) if isinstance(current_entity, dict) else []
        for location in connections if isinstance(connections, list) else []:
            location_id = str(location)
            location_label = labels.get(("location", location_id), location_id)
            location_action = {
                "id": f"travel:{location_id}",
                "kind": "travel",
                "label": f"前往：{location_label}",
                "description": location_id,
                "enabled": True,
                "command": {"type": "space.travel_to", "actor": actor, "target": location_id, "args": {}},
            }
            locations.append({"id": location_id, "label": location_label, "action_id": location_action["id"]})
            actions.append(location_action)

        candidate_report = self.candidate_report(session_id, actor)
        selected_id = candidate_report.get("selected")
        scene_summary: dict[str, Any] | None = None
        if selected_id:
            scene = self.scene(selected_id)["document"]
            repository = ContentRepository.from_path(self.content_root, registry=self._registry())
            rule_engine = RuleEngine(self._registry())
            context = {"command": Command(type="diagnostic.scene_report", actor=actor), "content_repository": repository}
            choices: list[dict[str, Any]] = []
            for index, choice in enumerate(scene.get("choices", [])):
                visible = True
                reason = "显示条件满足"
                for rule in choice.get("visible_if", []) if isinstance(choice, dict) else []:
                    if not isinstance(rule, dict):
                        continue
                    result = rule_engine.evaluate(RuleRef(str(rule.get("rule")), list(rule.get("args", []))), state, context)
                    if not result.passed:
                        visible = False
                        reason = result.reason
                        break
                choice_data = {"index": index, "text": choice.get("text", f"选项 {index + 1}"), "visible": visible, "reason": reason}
                choices.append(choice_data)
                if visible:
                    actions.append({
                        "id": f"choice:{selected_id}:{index}",
                        "kind": "choice",
                        "label": str(choice_data["text"]),
                        "description": f"{selected_id} · 选项 {index + 1}",
                        "enabled": True,
                        "command": {"type": "narrative.choose", "actor": actor, "target": selected_id, "args": {"choice_index": index}},
                    })
            scene_summary = {"id": selected_id, "text": scene.get("text", ""), "choices": choices}

        clock = state.get("globals", {}).get("clock", {})
        return {
            "actor": {"id": actor, "label": labels.get(("actor", actor), actor)},
            "location": {"id": current_location, "label": labels.get(("location", current_location), current_location)},
            "time": {"day": clock.get("day"), "period": clock.get("period"), "tick": clock.get("tick")},
            "scene": scene_summary,
            "available_locations": locations,
            "actions": actions,
        }

    def _command_summary(self, command: dict[str, Any], trace: dict[str, Any], before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        if trace.get("status") != "succeeded":
            reason = trace.get("failure_reason") or "引擎拒绝了该操作"
            return {"headline": "操作失败", "lines": [str(reason)], "changes": []}
        command_type = str(command.get("type", "操作"))
        headline = "操作成功"
        if command_type == "narrative.choose":
            scene_id = str(command.get("target") or command.get("args", {}).get("scene_id", ""))
            choice_index = int(command.get("args", {}).get("choice_index", 0))
            try:
                choice = self.scene(scene_id)["document"].get("choices", [])[choice_index]
                headline = f"操作成功：{choice.get('text', f'选择 {choice_index + 1}') }"
            except (IndexError, KeyError, TypeError):
                headline = "操作成功：选择场景选项"
        elif command_type == "space.travel_to":
            target = str(command.get("target", ""))
            label = next((item["label"] for item in self.references("location")["references"] if item["id"] == target), target)
            headline = f"操作成功：前往 {label}"
        lines: list[str] = []
        changes: list[dict[str, Any]] = []
        for change in trace.get("changeset", {}).get("changes", []):
            path = change.get("path", [])
            path_text = ".".join(str(part) for part in path)
            line = _human_change(path, change.get("before"), change.get("after"), self.references()["references"])
            lines.append(line)
            changes.append({"path": path_text, "before": change.get("before"), "after": change.get("after"), "label": line})
        return {"headline": headline, "lines": lines, "changes": changes}

    def candidate_report(self, session_id: str | None = None, actor: str = "actor.player") -> dict[str, Any]:
        if session_id:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"session not found: {session_id}")
            assert self.content_root is not None
            registry = self._registry()
            repository = ContentRepository.from_path(self.content_root, registry=registry)
            from text_sandbox_engine.scene import SceneOrchestrator
            from text_sandbox_engine.models import Command
            presentation = SceneOrchestrator(repository, registry).select(
                session["runtime"].snapshot(),
                {"command_id": "diagnostic.scene_report", "command": Command(type="diagnostic.scene_report", actor=actor), "content_repository": repository},
            )
            return presentation.scene_candidate_report
        assert self.state_path is not None and self.content_root is not None
        return scene_candidate_report(self.state_path, self.content_root, actor=actor)

    def state_diff(self, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        return state_diff(before, after)

    def changed_by(self, trace: dict[str, Any], path: str) -> list[dict[str, Any]]:
        return changed_by_report(trace, path)

    def _scene_records(self) -> list[dict[str, Any]]:
        self._require_workspace()
        assert self.content_root is not None
        records = []
        for path in _scene_files(self.content_root):
            try:
                document = _load_json(path)
            except (OSError, json.JSONDecodeError):
                continue
            records.append({"id": document.get("id", path.stem), "path": str(path), "revision": _revision(path), "document": document})
        return records

    def _scene_path_for_id(self, scene_id: str) -> Path:
        assert self.content_root is not None
        return self.content_root / "scenes" / (scene_id.replace(".", "_") + ".json")

    def _unique_scene_id(self, base_id: str) -> str:
        existing = {item["id"] for item in self._scene_records()}
        if base_id not in existing and not self._scene_path_for_id(base_id).exists():
            return base_id
        suffix = 2
        while f"{base_id}_{suffix}" in existing or self._scene_path_for_id(f"{base_id}_{suffix}").exists():
            suffix += 1
        return f"{base_id}_{suffix}"

    def _registry(self) -> Registry:
        registry = Registry()
        register_builtins(registry)
        return registry

    def _assert_revision(self, path: Path, expected: str) -> None:
        actual = _revision(path)
        if actual != expected:
            raise RevisionConflict(json.dumps({"path": str(path), "expected": expected, "actual": actual}, ensure_ascii=False))

    def _require_workspace(self) -> None:
        if self.workspace_root is None or self.content_root is None or self.state_path is None:
            raise ValueError("no workspace is open")

    def _source_label(self, path: Path) -> str:
        assert self.workspace_root is not None
        try:
            return path.relative_to(self.workspace_root).as_posix()
        except ValueError:
            return str(path)

    def _schema_root(self) -> Path | None:
        assert self.workspace_root is not None
        candidates = [
            self.workspace_root / "schemas",
            self.workspace_root.parent / "schemas",
            self.workspace_root.parent.parent / "schemas",
        ]
        return next((path for path in candidates if path.exists()), None)

    @staticmethod
    def _file_kind(path: Path) -> str:
        if path.name == "world_state.json":
            return "world_state"
        if "scenes" in path.parts:
            return "scene"
        if "commands" in path.parts:
            return "commands"
        if "schemas" in path.parts:
            return "schema"
        return "file"

    @staticmethod
    def _node(nodes: dict[str, dict[str, Any]], node_id: str, node_type: str, label: str) -> None:
        nodes.setdefault(node_id, {"id": node_id, "type": node_type, "label": label})

    def _reference_edges(
        self,
        nodes: dict[str, dict[str, Any]],
        edges: list[dict[str, Any]],
        source: str,
        args: list[Any],
        relation: str,
        path: str,
        json_path: str,
    ) -> None:
        for index, value in enumerate(args):
            if not isinstance(value, str) or "." not in value:
                continue
            if value.startswith("actor."):
                node_type = "actor"
            elif value.startswith("location."):
                node_type = "location"
            elif value.startswith("scene."):
                node_type = "scene"
            elif value.startswith("quest."):
                node_type = "quest"
            elif value.startswith("item."):
                node_type = "item"
            else:
                node_type = "state"
            self._node(nodes, value, node_type, value)
            edges.append(_edge(source, value, relation, f"{json_path}[{index}]", path))


def _scene_files(root: Path) -> list[Path]:
    scene_root = root / "scenes"
    return sorted((scene_root if scene_root.exists() else root).rglob("*.json"))


_REFERENCE_TYPES = {"actor", "location", "item", "quest", "scene", "flag"}
_REFERENCE_LABELS = {"actor": "角色", "location": "地点", "item": "物品", "quest": "任务", "scene": "场景", "flag": "Flag"}

_ENTITY_TYPES = [
    {"id": "actor", "label": "角色", "description": "可以移动、对话、持有物品并参与规则判断的世界实体。"},
    {"id": "location", "label": "地点", "description": "地图上的可到达地点，包含描述、连接和访问限制。"},
    {"id": "item", "label": "物品", "description": "可以被角色持有并被场景效果引用的物品实体。"},
]

_ENTITY_TEMPLATES = [
    {
        "id": "basic",
        "type": "actor",
        "label": "普通角色",
        "description": "包含名称、当前位置和空背包的角色。",
        "document": {"id": "actor.new_actor", "type": "actor", "tags": [], "components": {"profile": {"name": "新角色"}, "location": {"current": "location.west_gate"}, "inventory": {"items": []}}, "metadata": {}},
    },
    {
        "id": "basic",
        "type": "location",
        "label": "普通地点",
        "description": "包含名称、描述、区域和空连接的地点。",
        "document": {"id": "location.new_location", "type": "location", "tags": [], "components": {"description": {"name": "新地点", "text": ""}, "map_node": {"region": "greybrook", "connections": []}}, "metadata": {}},
    },
    {
        "id": "basic",
        "type": "item",
        "label": "普通物品",
        "description": "包含名称、描述和基础物品属性的物品。",
        "document": {"id": "item.new_item", "type": "item", "tags": [], "components": {"description": {"name": "新物品", "text": ""}, "item": {"kind": "misc", "stackable": False, "max_stack": 1}}, "metadata": {}},
    },
]

_SCENE_TEMPLATES = [
    {
        "id": "blank",
        "label": "空白场景",
        "description": "只包含一个继续选项的最小场景。",
        "document": {"conditions": [], "text": "在这里写下场景正文。", "choices": [{"text": "继续", "effects": []}], "repeat_policy": "always"},
    },
    {
        "id": "narrative",
        "label": "普通叙事",
        "description": "适合描述一段剧情并提供两个选择。",
        "document": {"conditions": [], "text": "新的叙事片段从这里开始。", "choices": [{"text": "继续观察", "effects": []}, {"text": "暂时离开", "effects": []}], "repeat_policy": "always"},
    },
    {
        "id": "npc_dialogue",
        "label": "NPC 对话",
        "description": "适合与当前地点的角色交谈。",
        "document": {"conditions": [{"rule": "actor.is_present", "args": ["actor.player"]}], "text": "角色向你打招呼。", "choices": [{"text": "回应", "effects": []}, {"text": "告别", "effects": []}], "repeat_policy": "always"},
    },
    {
        "id": "quest_offer",
        "label": "接取任务",
        "description": "提供接受任务的基础选项。",
        "document": {"conditions": [], "text": "有人向你提出一项任务。", "choices": [{"text": "接受任务", "effects": [{"effect": "quest.set_stage", "args": ["quest.bread_delivery", "accepted"]}]}, {"text": "拒绝任务", "effects": []}], "repeat_policy": "once"},
    },
    {
        "id": "item_delivery",
        "label": "交付物品",
        "description": "适合从玩家背包移除物品并完成交付。",
        "document": {"conditions": [], "text": "你把准备好的物品交给对方。", "choices": [{"text": "完成交付", "effects": [{"effect": "inventory.remove_item", "args": ["actor.player", "item.bread_basket"]}]}, {"text": "稍后再来", "effects": []}], "repeat_policy": "once"},
    },
    {
        "id": "arrival_event",
        "label": "到达地点事件",
        "description": "适合玩家到达地点后触发的事件。",
        "document": {"conditions": [{"rule": "actor.is_present", "args": ["actor.player"]}], "text": "你抵达了这里，一件新鲜事正在发生。", "choices": [{"text": "介入事件", "effects": []}], "repeat_policy": "once"},
    },
]


def _document_reference_values(document: dict[str, Any]) -> list[tuple[str, tuple[str, list[Any]]]]:
    values: list[tuple[str, tuple[str, list[Any]]]] = []
    for rule in document.get("conditions", []):
        if isinstance(rule, dict) and isinstance(rule.get("args"), list):
            values.append(("rule", (str(rule.get("rule", "")), rule["args"])))
    for choice in document.get("choices", []):
        if not isinstance(choice, dict):
            continue
        for rule in choice.get("visible_if", []):
            if isinstance(rule, dict) and isinstance(rule.get("args"), list):
                values.append(("rule", (str(rule.get("rule", "")), rule["args"])))
        for effect in choice.get("effects", []):
            if isinstance(effect, dict) and isinstance(effect.get("args"), list):
                values.append(("effect", (str(effect.get("effect", "")), effect["args"])))
    return values


def _scene_argument_paths(document: dict[str, Any], registry: Registry) -> list[tuple[str, str, list[Any], str]]:
    metadata = {(item["kind"], item["type_id"]): item for item in registry.metadata()}
    result: list[tuple[str, str, list[Any], str]] = []
    for index, condition in enumerate(document.get("conditions", [])):
        if isinstance(condition, dict) and isinstance(condition.get("args"), list):
            result.append(("rule", str(condition.get("rule", "")), condition["args"], f"$.conditions[{index}].args"))
    for choice_index, choice in enumerate(document.get("choices", [])):
        if not isinstance(choice, dict):
            continue
        for condition_index, condition in enumerate(choice.get("visible_if", [])):
            if isinstance(condition, dict) and isinstance(condition.get("args"), list):
                result.append(("rule", str(condition.get("rule", "")), condition["args"], f"$.choices[{choice_index}].visible_if[{condition_index}].args"))
        for effect_index, effect in enumerate(choice.get("effects", [])):
            if isinstance(effect, dict) and isinstance(effect.get("args"), list):
                result.append(("effect", str(effect.get("effect", "")), effect["args"], f"$.choices[{choice_index}].effects[{effect_index}].args"))
    return result


def _entity_label(document: dict[str, Any], fallback: str) -> str:
    components = document.get("components", {}) if isinstance(document, dict) else {}
    if isinstance(components, dict):
        for component_name in ("profile", "description"):
            component = components.get(component_name)
            if isinstance(component, dict) and component.get("name"):
                return str(component["name"])
    return fallback


def _set_entity_name(document: dict[str, Any], name: str) -> None:
    components = document.setdefault("components", {})
    component_name = "profile" if document.get("type") == "actor" else "description"
    components.setdefault(component_name, {})["name"] = name


def _entity_json_path(entity_id: str, suffix: str) -> str:
    return f'$.entities["{entity_id}"].{suffix}'


def _human_change(path: list[Any], before: Any, after: Any, references: list[dict[str, Any]]) -> str:
    labels = {(item["type"], item["id"]): item["label"] for item in references}
    if len(path) >= 2 and path[0] == "flags":
        return f"Flag {path[1]}：{_display_value(before)} → {_display_value(after)}"
    if len(path) >= 5 and path[0] == "entities" and path[2:5] == ["components", "location", "current"]:
        return f"当前地点：{labels.get(('location', after), after)}"
    if len(path) >= 5 and path[0] == "entities" and path[2:4] == ["components", "relationship"]:
        return f"{labels.get(('actor', path[1]), path[1])}的信任度：{before} → {after}"
    if len(path) >= 4 and path[0] == "globals" and path[1] == "quests" and path[3] == "stage":
        return f"任务 {labels.get(('quest', path[2]), path[2])} 阶段：{before} → {after}"
    if path[:3] == ["globals", "narrative", "seen_scenes"]:
        return "当前场景已记录为看过"
    if len(path) >= 5 and path[0] == "entities" and path[2:4] == ["components", "inventory"]:
        return "玩家物品清单已更新"
    return f"状态变化：{'.'.join(str(part) for part in path)}：{_display_value(before)} → {_display_value(after)}"


def _display_value(value: Any) -> str:
    if value is True:
        return "是"
    if value is False:
        return "否"
    if value is None:
        return "空"
    return str(value)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _revision(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _atomic_json_write(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = path.with_suffix(path.suffix + ".bak")
    if path.exists():
        shutil.copy2(path, backup)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            json.dump(document, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _issue(code: str, message: str, path: Path | None, json_path: str, scene_id: str | None = None, suggestion: str | None = None) -> dict[str, Any]:
    item = {"severity": "error", "code": code, "message": message, "file": str(path) if path else None, "json_path": json_path}
    if scene_id:
        item["scene_id"] = scene_id
    if suggestion:
        item["suggestion"] = suggestion
    return item


def _guess_json_path(path: str, message: str) -> str:
    if "conditions" in path:
        return "$.conditions"
    if "choices" in path:
        return "$.choices"
    if "rule" in message:
        return "$.conditions"
    if "effect" in message:
        return "$.choices"
    return "$"


def _rule_ids(registry: Registry) -> set[str]:
    return {item["type_id"] for item in registry.metadata() if item.get("kind") == "rule"}


def _effect_ids(registry: Registry) -> set[str]:
    return {item["type_id"] for item in registry.metadata() if item.get("kind") == "effect"}


def _edge(source: str, target: str, relation: str, json_path: str, path: str) -> dict[str, Any]:
    return {"id": f"{source}->{target}:{json_path}", "source": source, "target": target, "relation": relation, "json_path": json_path, "path": path}
