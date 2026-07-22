from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from text_sandbox_editor_api.api import create_app
from text_sandbox_editor_api.service import EditorService


ROOT = Path(__file__).resolve().parents[1]
MEDIEVAL_ROOT = ROOT / "examples" / "medieval_town"


class PhaseNineLowCodeE2ETests(unittest.TestCase):
    def test_structured_authoring_to_isolated_playtest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "town"
            shutil.copytree(MEDIEVAL_ROOT, workspace)
            original_world_state = (workspace / "world_state.json").read_bytes()
            service = EditorService()
            client = TestClient(create_app(service))
            self.assertEqual(client.post("/api/workspaces/open", json={"root": str(workspace)}).status_code, 200)

            references = client.get("/api/metadata/references").json()["references"]
            actors = {item["label"]: item["id"] for item in references if item["type"] == "actor" and item["valid"]}
            locations = {item["label"]: item["id"] for item in references if item["type"] == "location" and item["valid"]}
            quests = {item["id"] for item in references if item["type"] == "quest" and item["valid"]}
            self.assertIn("actor.osric", actors.values())
            self.assertIn("location.west_gate", locations.values())
            self.assertIn("quest.bread_delivery", quests)

            preview = client.post("/api/content/scenes/from-template", json={
                "name": "守卫委托",
                "namespace": "greybrook",
                "slug": "guard_request",
                "location": locations["西门"],
                "template": "npc_dialogue",
                "repeat_policy": "once",
                "priority": 99,
                "preview": True,
            }).json()
            self.assertTrue(preview["passed"])
            document = preview["document"]
            document["conditions"] = [{"rule": "actor.is_present", "args": ["actor.osric"]}]
            document["choices"] = [
                {
                    "text": "接受守卫的请求",
                    "effects": [
                        {"effect": "quest.set_stage", "args": ["quest.bread_delivery", "accepted"]},
                        {"effect": "social.adjust_trust", "args": ["actor.osric", 1]},
                    ],
                },
                {"text": "暂时拒绝", "effects": []},
            ]
            created = client.post("/api/content/scenes/from-template", json={
                "name": "守卫委托",
                "namespace": "greybrook",
                "slug": "guard_request",
                "location": locations["西门"],
                "template": "npc_dialogue",
                "repeat_policy": "once",
                "priority": 99,
                "preview": False,
            }).json()
            # Replace the template draft through the same revision-safe save API used by the form.
            record = created["scene"]
            record["document"] = document
            saved = client.put(
                f"/api/content/scenes/{record['id']}",
                json={"document": document, "revision": record["revision"]},
            )
            self.assertEqual(saved.status_code, 200)
            self.assertTrue(client.post("/api/validation/content").json()["passed"])

            session = client.post("/api/runtime/sessions").json()
            actions = client.get(f"/api/runtime/sessions/{session['session_id']}/actions").json()
            choice = next(action for action in actions["actions"] if action["kind"] == "choice" and action["command"]["target"] == record["id"])
            result = client.post(f"/api/runtime/sessions/{session['session_id']}/commands", json={"command": choice["command"]}).json()
            self.assertTrue(result["summary"]["headline"].startswith("操作成功"))
            self.assertEqual(result["state"]["globals"]["quests"]["quest.bread_delivery"]["stage"], "accepted")
            self.assertEqual(result["state"]["entities"]["actor.osric"]["components"]["relationship"]["trust"], 1)
            self.assertEqual((workspace / "world_state.json").read_bytes(), original_world_state)


if __name__ == "__main__":
    unittest.main()
