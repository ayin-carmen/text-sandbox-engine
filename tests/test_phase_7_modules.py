from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from text_sandbox_engine import Runtime

MEDIEVAL_ROOT = ROOT / "examples" / "medieval_town"
MEDIEVAL_STATE = MEDIEVAL_ROOT / "world_state.json"
MEDIEVAL_CONTENT = MEDIEVAL_ROOT / "content"


class Phase7ModuleTests(unittest.TestCase):
    def test_inventory_social_and_quest_effects_are_traceable(self) -> None:
        runtime = Runtime.from_file(MEDIEVAL_STATE, content_path=MEDIEVAL_CONTENT)
        runtime.execute(
            {
                "type": "space.travel_to",
                "actor": "actor.player",
                "target": "location.market_square",
                "args": {},
            }
        )

        result = runtime.execute(
            {
                "type": "narrative.choose",
                "actor": "actor.player",
                "target": "scene.greybrook.market_baker",
                "args": {"choice_index": 0},
            }
        )

        effect_types = [effect.effect_type for effect in result.trace.effect_results]
        self.assertIn("inventory.add_item", effect_types)
        self.assertIn("quest.set_stage", effect_types)
        self.assertIn("social.adjust_trust", effect_types)
        self.assertIn("item.bread_basket", result.state["entities"]["actor.player"]["components"]["inventory"]["items"])
        self.assertEqual(result.state["globals"]["quests"]["quest.bread_delivery"]["stage"], "accepted")
        self.assertEqual(result.state["entities"]["actor.elda"]["components"]["relationship"]["trust"], 1)

    def test_repeat_policy_once_filters_seen_scene(self) -> None:
        runtime = Runtime.from_file(MEDIEVAL_STATE, content_path=MEDIEVAL_CONTENT)
        first = runtime.execute(
            {
                "type": "narrative.choose",
                "actor": "actor.player",
                "target": "scene.greybrook.west_gate_guard",
                "args": {"choice_index": 0},
            }
        )

        second = runtime.execute(
            {
                "type": "narrative.choose",
                "actor": "actor.player",
                "target": "scene.greybrook.west_gate_guard",
                "args": {"choice_index": 0},
            }
        )

        self.assertEqual(first.status, "succeeded")
        self.assertIn("scene.greybrook.west_gate_guard", first.state["globals"]["narrative"]["seen_scenes"])
        self.assertEqual(second.status, "failed")
        self.assertEqual(second.trace.failure_reason, "scene has already been seen")

    def test_dynamic_access_allows_keep_after_permission_flag(self) -> None:
        runtime = Runtime.from_file(MEDIEVAL_STATE, content_path=MEDIEVAL_CONTENT)
        runtime.execute(
            {
                "type": "space.travel_to",
                "actor": "actor.player",
                "target": "location.market_square",
                "args": {},
            }
        )
        runtime.state_store.set_value(["flags", "has_keep_pass"], True)

        result = runtime.execute(
            {
                "type": "space.travel_to",
                "actor": "actor.player",
                "target": "location.lord_keep",
                "args": {},
            }
        )

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(
            result.state["entities"]["actor.player"]["components"]["location"]["current"],
            "location.lord_keep",
        )


if __name__ == "__main__":
    unittest.main()
