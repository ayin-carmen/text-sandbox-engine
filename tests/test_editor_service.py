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

        self.assertEqual(workspace["scene_count"], 5)
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


if __name__ == "__main__":
    unittest.main()
