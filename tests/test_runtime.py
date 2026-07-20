from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from text_sandbox_engine import Runtime
from text_sandbox_engine.builtins import register_builtins
from text_sandbox_engine.content import ContentRepository
from text_sandbox_engine.persistence import load_save
from text_sandbox_engine.registry import Registry

EXAMPLE_STATE = ROOT / "examples" / "minimal_world_state.json"
EXAMPLE_CONTENT = ROOT / "examples" / "content"


class RuntimeTests(unittest.TestCase):
    def load_runtime(self) -> Runtime:
        return Runtime.from_file(EXAMPLE_STATE)

    def test_travel_command_changes_state_and_returns_trace(self) -> None:
        runtime = self.load_runtime()

        result = runtime.execute(
            {
                "type": "space.travel_to",
                "actor": "actor.player",
                "target": "location.market",
                "args": {},
            }
        )

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(
            result.state["entities"]["actor.player"]["components"]["location"]["current"],
            "location.market",
        )
        self.assertEqual(result.state["globals"]["clock"]["tick"], 1)
        self.assertEqual(result.state["diagnostics_state"]["command_index"], 1)
        self.assertEqual(result.trace.command_id, "cmd.000001")
        self.assertTrue(all(rule.passed for rule in result.trace.rule_results))
        self.assertEqual(len(result.trace.effect_results), 2)
        self.assertEqual(len(result.trace.changeset.changes), 2)

    def test_travel_command_selects_matching_scene_from_content(self) -> None:
        runtime = Runtime.from_file(EXAMPLE_STATE, content_path=EXAMPLE_CONTENT)

        result = runtime.execute(
            {
                "type": "space.travel_to",
                "actor": "actor.player",
                "target": "location.market",
                "args": {},
            }
        )

        report = result.trace.presentation.scene_candidate_report
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.trace.presentation.selected_scene, "scene.market_intro")
        self.assertEqual(result.trace.presentation.scene["text"], "你第一次走进市场，空气里混着面包、湿羊毛和铜币的气味。")
        self.assertEqual(report["selected"], "scene.market_intro")
        self.assertEqual(report["filtered"], [])

    def test_playable_loop_applies_scene_choice_and_reveals_npc_scene(self) -> None:
        runtime = Runtime.from_file(EXAMPLE_STATE, content_path=EXAMPLE_CONTENT)
        travel = runtime.execute(
            {
                "type": "space.travel_to",
                "actor": "actor.player",
                "target": "location.market",
                "args": {},
            }
        )

        intro_choice = runtime.execute(
            {
                "type": "narrative.choose",
                "actor": "actor.player",
                "target": travel.trace.presentation.selected_scene,
                "args": {"choice_index": 0},
            }
        )

        self.assertEqual(intro_choice.status, "succeeded")
        self.assertTrue(intro_choice.state["flags"]["met_market"])
        self.assertEqual(intro_choice.state["globals"]["clock"]["tick"], 2)
        self.assertEqual(intro_choice.trace.presentation.selected_scene, "scene.market_vendor")
        vendor_rules = intro_choice.trace.presentation.scene_candidate_report["candidates"][0]["rules"]
        self.assertTrue(any(rule["rule"] == "actor.is_present" for rule in vendor_rules))

        vendor_choice = runtime.execute(
            {
                "type": "narrative.choose",
                "actor": "actor.player",
                "target": "scene.market_vendor",
                "args": {"choice_index": 0},
            }
        )

        self.assertEqual(vendor_choice.status, "succeeded")
        self.assertTrue(vendor_choice.state["flags"]["talked_to_mara"])
        self.assertEqual(vendor_choice.trace.effect_results[0].effect_type, "flag.set")

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "playable_loop_save.json"
            runtime.save_game(save_path)
            loaded = Runtime.load_game(save_path)

        self.assertEqual(loaded.snapshot(), runtime.snapshot())

    def test_failed_rule_produces_no_state_changes(self) -> None:
        runtime = self.load_runtime()
        before = runtime.snapshot()

        result = runtime.execute(
            {
                "type": "space.travel_to",
                "actor": "actor.player",
                "target": "location.nowhere",
                "args": {},
            }
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(runtime.snapshot(), before)
        self.assertTrue(result.trace.failure_reason)
        self.assertEqual(result.trace.changeset.changes, [])

    def test_save_load_roundtrip_preserves_state(self) -> None:
        runtime = self.load_runtime()
        runtime.execute(
            {
                "type": "space.travel_to",
                "actor": "actor.player",
                "target": "location.market",
                "args": {},
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "save.json"
            runtime.save_game(save_path)
            loaded = Runtime.load_game(save_path)

        self.assertEqual(loaded.snapshot(), runtime.snapshot())

    def test_save_file_records_metadata_versions(self) -> None:
        runtime = self.load_runtime()

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "save.json"
            report = runtime.save_game(save_path)
            with save_path.open("r", encoding="utf-8") as file:
                raw_save = json.load(file)
            loaded = load_save(save_path)

        self.assertIn("save_metadata", raw_save)
        self.assertIn("world_state", raw_save)
        self.assertEqual(report.metadata.save_schema_version, 2)
        self.assertEqual(loaded.metadata.engine_version, "0.4.0")
        self.assertEqual(loaded.metadata.enabled_modules, ["actor", "narrative", "space", "time"])
        self.assertEqual(loaded.metadata.module_versions["space"], "0.1.0")
        self.assertEqual(loaded.metadata.component_schema_versions["location"], 1)
        self.assertEqual(loaded.metadata.random_state["seed"], 17020)

    def test_legacy_world_state_loads_with_migration_report(self) -> None:
        with EXAMPLE_STATE.open("r", encoding="utf-8") as file:
            legacy_state = json.load(file)

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "legacy.json"
            with save_path.open("w", encoding="utf-8") as file:
                json.dump(legacy_state, file)
            runtime = Runtime.load_game(save_path)

        self.assertEqual(runtime.snapshot(), legacy_state)
        self.assertTrue(runtime.last_load_report.migrated)
        self.assertEqual(
            [step.name for step in runtime.last_load_report.steps],
            ["bare_world_state_to_save_envelope", "save_schema_1_to_2"],
        )

    def test_missing_module_in_save_reports_clear_error(self) -> None:
        runtime = self.load_runtime()

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "save.json"
            runtime.save_game(save_path)
            with save_path.open("r", encoding="utf-8") as file:
                save_data = json.load(file)
            save_data["save_metadata"]["enabled_modules"].append("missing.module")
            save_data["save_metadata"]["module_versions"]["missing.module"] = "0.1.0"
            with save_path.open("w", encoding="utf-8") as file:
                json.dump(save_data, file)

            with self.assertRaisesRegex(ValueError, "save requires missing modules: missing.module"):
                Runtime.load_game(save_path)

    def test_module_version_mismatch_reports_clear_error(self) -> None:
        runtime = self.load_runtime()

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "save.json"
            runtime.save_game(save_path)
            with save_path.open("r", encoding="utf-8") as file:
                save_data = json.load(file)
            save_data["save_metadata"]["module_versions"]["space"] = "9.9.9"
            with save_path.open("w", encoding="utf-8") as file:
                json.dump(save_data, file)

            with self.assertRaisesRegex(ValueError, "save module version mismatch"):
                Runtime.load_game(save_path)

    def test_loaded_versioned_save_can_continue_deterministically(self) -> None:
        runtime = self.load_runtime()

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "save.json"
            runtime.save_game(save_path)
            loaded = Runtime.load_game(save_path)
            result = loaded.execute(
                {
                    "type": "space.travel_to",
                    "actor": "actor.player",
                    "target": "location.market",
                    "args": {},
                }
            )

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.trace.command_id, "cmd.000001")
        self.assertEqual(result.state["globals"]["clock"]["tick"], 1)

    def test_example_state_is_valid_json(self) -> None:
        with EXAMPLE_STATE.open("r", encoding="utf-8") as file:
            self.assertIsInstance(json.load(file), dict)

    def test_content_validation_rejects_unknown_rule(self) -> None:
        registry = Registry()
        register_builtins(registry)
        repository = ContentRepository(
            scenes=[
                {
                    "id": "scene.invalid_rule",
                    "scope": {},
                    "priority": 1,
                    "conditions": [{"rule": "missing.rule", "args": []}],
                    "text": "invalid",
                    "choices": [{"text": "ok", "effects": []}],
                }
            ]
        )

        report = repository.validate(registry=registry)

        self.assertFalse(report.passed)
        self.assertIn("unknown rule: missing.rule", report.issues[0].message)


if __name__ == "__main__":
    unittest.main()
