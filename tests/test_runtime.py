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
