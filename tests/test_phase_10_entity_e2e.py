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


class PhaseTenEntityApiE2ETests(unittest.TestCase):
    def test_actor_location_item_creation_and_reference_protection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "town"
            shutil.copytree(MEDIEVAL_ROOT, workspace)
            world_state = workspace / "world_state.json"
            original = world_state.read_bytes()
            client = TestClient(create_app(EditorService()))

            opened = client.post("/api/workspaces/open", json={"root": str(workspace)})
            self.assertEqual(opened.status_code, 200)
            self.assertEqual({item["id"] for item in client.get("/api/metadata/entity-types").json()["types"]}, {"actor", "location", "item"})

            actor_preview = client.post("/api/world/entities/from-template", json={
                "type": "actor", "namespace": "greybrook", "slug": "ferryman", "name": "摆渡人",
                "tags": ["npc"], "location": "location.west_gate", "preview": True,
            }).json()
            self.assertTrue(actor_preview["passed"])
            actor = client.post("/api/world/entities/from-template", json={
                "type": "actor", "namespace": "greybrook", "slug": "ferryman", "name": "摆渡人",
                "tags": ["npc"], "location": "location.west_gate", "preview": False,
            }).json()["entity"]
            self.assertEqual(actor["id"], "actor.greybrook.ferryman")

            location = client.post("/api/world/entities/from-template", json={
                "type": "location", "namespace": "greybrook", "slug": "riverside", "name": "河岸",
                "tags": ["public"], "location": "location.west_gate", "preview": False,
            }).json()["entity"]
            item = client.post("/api/world/entities/from-template", json={
                "type": "item", "namespace": "greybrook", "slug": "river_token", "name": "渡船凭证",
                "tags": ["quest"], "preview": False,
            }).json()["entity"]
            self.assertEqual(location["type"], "location")
            self.assertEqual(item["type"], "item")

            listed = client.get("/api/world/entities", params={"type": "item", "query": "凭证"}).json()["entities"]
            self.assertEqual([entry["id"] for entry in listed], ["item.greybrook.river_token"])
            self.assertTrue(any(entry["id"] == "item.greybrook.river_token" and entry["valid"] for entry in client.get("/api/metadata/references", params={"type": "item"}).json()["references"]))
            graph = client.get("/api/graph/content").json()
            self.assertIn("actor.greybrook.ferryman", {node["id"] for node in graph["nodes"]})
            self.assertTrue(any(edge["relation"] == "located_at" for edge in graph["edges"]))

            current_actor = client.get(f"/api/world/entities/{actor['id']}").json()
            revision = current_actor["revision"]
            actor_document = current_actor["document"]
            actor_document["tags"].append("ferryman")
            saved = client.put(f"/api/world/entities/{actor['id']}", json={"document": actor_document, "revision": revision})
            self.assertEqual(saved.status_code, 200)
            self.assertIn("ferryman", saved.json()["document"]["tags"])
            actor_document["components"]["location"]["current"] = "location.missing"
            invalid = client.post(f"/api/validation/entity?entity_id={actor['id']}", json={"document": actor_document})
            self.assertFalse(invalid.json()["passed"])
            self.assertIn("$.entities[\"actor.greybrook.ferryman\"].components.location.current", {issue["json_path"] for issue in invalid.json()["issues"]})

            usages = client.get("/api/world/entities/location.west_gate/usages")
            self.assertEqual(usages.status_code, 200)
            self.assertTrue(usages.json()["usages"])
            blocked = client.delete(f"/api/world/entities/location.west_gate", params={"revision": saved.json()["revision"]})
            self.assertEqual(blocked.status_code, 409)
            self.assertTrue(world_state.read_bytes() != original)
            self.assertTrue(world_state.with_suffix(".json.bak").exists())


if __name__ == "__main__":
    unittest.main()
