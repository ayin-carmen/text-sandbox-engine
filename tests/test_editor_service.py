from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from text_sandbox_editor_api.service import EditorService, RevisionConflict


ROOT = Path(__file__).resolve().parents[1]
MEDIEVAL_ROOT = ROOT / "examples" / "medieval_town"


class EditorServiceTests(unittest.TestCase):
    def test_opens_real_workspace_and_builds_reference_graph(self) -> None:
        service = EditorService()
        workspace = service.open_workspace(MEDIEVAL_ROOT)

        self.assertGreaterEqual(workspace["scene_count"], 5)
        self.assertGreater(len(service.tree()["entries"]), 5)
        graph = service.graph()
        self.assertIn("scene.greybrook.market_baker", {node["id"] for node in graph["nodes"]})
        self.assertTrue(any(edge["relation"] == "modifies" for edge in graph["edges"]))

    def test_session_replay_is_isolated_from_source_state(self) -> None:
        service = EditorService()
        service.open_workspace(MEDIEVAL_ROOT)
        source_before = (MEDIEVAL_ROOT / "world_state.json").read_bytes()
        session = service.create_session()

        result = service.session_command(
            session["session_id"],
            {"type": "space.travel_to", "actor": "actor.player", "target": "location.market_square", "args": {}},
        )

        self.assertEqual(result["status"], "succeeded")
        self.assertTrue(result["trace"]["changeset"]["changes"])
        self.assertEqual(source_before, (MEDIEVAL_ROOT / "world_state.json").read_bytes())

    def test_save_requires_revision_and_keeps_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "town"
            shutil.copytree(MEDIEVAL_ROOT, workspace)
            service = EditorService()
            service.open_workspace(workspace)
            record = service.scene("scene.greybrook.market_baker")
            document = json.loads(json.dumps(record["document"], ensure_ascii=False))
            document["priority"] = 42

            saved = service.save_scene(record["id"], document, record["revision"])
            self.assertEqual(saved["document"]["priority"], 42)
            self.assertTrue(Path(record["path"] + ".bak").exists())

            with self.assertRaises(RevisionConflict):
                service.save_scene(record["id"], document, record["revision"])

    def test_invalid_reference_has_stable_diagnostic(self) -> None:
        service = EditorService()
        service.open_workspace(MEDIEVAL_ROOT)
        record = service.scene("scene.greybrook.market_baker")
        document = json.loads(json.dumps(record["document"], ensure_ascii=False))
        document["conditions"][0]["rule"] = "unknown.rule"

        report = service.validate_document(document, Path(record["path"]))

        self.assertFalse(report["passed"])
        self.assertIn("registry.unknown_rule", {issue["code"] for issue in report["issues"]})
        self.assertTrue(all(issue["json_path"].startswith("$") for issue in report["issues"]))

    def test_source_state_and_registry_metadata_are_editor_dtos(self) -> None:
        service = EditorService()
        service.open_workspace(MEDIEVAL_ROOT)

        source = service.source_state()
        metadata = service.registry_metadata()

        self.assertEqual(source["state"]["schema_version"], 1)
        self.assertTrue(source["revision"])
        self.assertIn("flag.set", {item["type_id"] for item in metadata["items"]})

    def test_low_code_metadata_and_reference_index(self) -> None:
        service = EditorService()
        service.open_workspace(MEDIEVAL_ROOT)

        metadata = {item["type_id"]: item for item in service.registry_metadata()["items"]}
        flag_set = metadata["flag.set"]
        self.assertEqual(flag_set["label"], "设置 Flag")
        self.assertEqual(flag_set["category"], "状态")
        self.assertEqual(flag_set["parameters"][0]["widget"], "reference_select")
        self.assertEqual(flag_set["parameters"][0]["reference_type"], "flag")

        references = service.references()["references"]
        by_key = {(item["type"], item["id"]): item for item in references}
        self.assertEqual(by_key[("actor", "actor.elda")]["label"], "艾尔达")
        self.assertTrue(by_key[("location", "location.market_square")]["valid"])
        self.assertTrue(by_key[("item", "item.bread_basket")]["valid"])
        self.assertEqual(
            {item["type"] for item in service.references("actor")["references"]},
            {"actor"},
        )

    def test_reference_index_marks_missing_actor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "town"
            shutil.copytree(MEDIEVAL_ROOT, workspace)
            scene_path = workspace / "content" / "scenes" / "market_baker.json"
            document = json.loads(scene_path.read_text(encoding="utf-8"))
            document["conditions"][0]["args"][0] = "actor.missing"
            scene_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")

            service = EditorService()
            service.open_workspace(workspace)
            references = service.references("actor")["references"]

            missing = next(item for item in references if item["id"] == "actor.missing")
            self.assertFalse(missing["valid"])
            self.assertEqual(missing["source"], "content/scenes/market_baker.json")

    def test_document_validation_locates_missing_reference_parameter(self) -> None:
        service = EditorService()
        service.open_workspace(MEDIEVAL_ROOT)
        document = json.loads(json.dumps(service.scene("scene.greybrook.market_baker")["document"], ensure_ascii=False))
        document["scope"]["location"] = "location.missing"
        document["conditions"][0]["args"][0] = "actor.missing"

        report = service.validate_document(document, None)
        issues = {item["json_path"]: item for item in report["issues"]}
        self.assertEqual(issues["$.scope.location"]["code"], "reference.missing_target")
        self.assertEqual(issues["$.conditions[0].args[0]"]["code"], "reference.missing_target")
        self.assertTrue(issues["$.conditions[0].args[0]"]["suggestion"])

    def test_session_actions_summary_and_reset(self) -> None:
        service = EditorService()
        service.open_workspace(MEDIEVAL_ROOT)
        session = service.create_session()

        self.assertEqual(session["actions"]["location"]["id"], "location.west_gate")
        self.assertTrue(any(action["kind"] == "travel" for action in session["actions"]["actions"]))
        actions = service.session_actions(session["session_id"])
        self.assertEqual(actions["location"]["id"], "location.west_gate")
        self.assertTrue(any(action["kind"] == "choice" for action in actions["actions"]))
        choice = next(action for action in actions["actions"] if action["kind"] == "choice")
        result = service.session_command(session["session_id"], choice["command"])
        self.assertIn("操作成功", result["summary"]["headline"])
        self.assertTrue(any("met_guard" in line for line in result["summary"]["lines"]))

        reset = service.reset_session(session["session_id"])
        self.assertEqual(reset["traces"], [])
        self.assertFalse(reset["state"]["flags"]["met_guard"])

    def test_scene_templates_preview_and_conflict_safe_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "town"
            shutil.copytree(MEDIEVAL_ROOT, workspace)
            service = EditorService()
            service.open_workspace(workspace)

            templates = service.scene_templates()["templates"]
            self.assertIn("npc_dialogue", {item["id"] for item in templates})
            preview = service.scene_from_template(
                name="集市问候",
                namespace="greybrook",
                slug="market_baker",
                location="location.market_square",
                template_id="narrative",
                repeat_policy="once",
                priority=4,
                preview=True,
            )
            self.assertTrue(preview["passed"])
            self.assertTrue(preview["conflict_resolved"])
            self.assertEqual(preview["id"], "scene.greybrook.market_baker_2")
            self.assertFalse((workspace / "content" / "scenes" / "market_baker_2.json").exists())

            created = service.scene_from_template(
                name="新的守卫对话",
                namespace="greybrook",
                slug="new_guard_dialogue",
                location="location.west_gate",
                template_id="npc_dialogue",
                repeat_policy="always",
                priority=1,
            )
            self.assertEqual(created["scene"]["id"], "scene.greybrook.new_guard_dialogue")
            self.assertTrue(Path(created["scene"]["path"]).exists())


if __name__ == "__main__":
    unittest.main()
