from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from text_sandbox_engine import Runtime
from text_sandbox_engine.debug import replay_commands, validate_content

MEDIEVAL_ROOT = ROOT / "examples" / "medieval_town"
MEDIEVAL_STATE = MEDIEVAL_ROOT / "world_state.json"
MEDIEVAL_CONTENT = MEDIEVAL_ROOT / "content"
MEDIEVAL_COMMANDS = MEDIEVAL_ROOT / "commands" / "vertical_slice.json"


class MedievalVerticalSliceTests(unittest.TestCase):
    def test_medieval_content_package_validates(self) -> None:
        report = validate_content(MEDIEVAL_CONTENT)

        self.assertTrue(report["passed"])
        self.assertEqual(report["scene_count"], 5)

    def test_medieval_vertical_slice_replays_successfully(self) -> None:
        report = replay_commands(MEDIEVAL_STATE, MEDIEVAL_COMMANDS, content_path=MEDIEVAL_CONTENT)

        self.assertEqual(report["status"], "succeeded")
        self.assertEqual(report["command_count"], 8)
        self.assertTrue(report["final_state"]["flags"]["met_guard"])
        self.assertTrue(report["final_state"]["flags"]["heard_market_notice"])
        self.assertTrue(report["final_state"]["flags"]["accepted_bread_delivery"])
        self.assertTrue(report["final_state"]["flags"]["visited_chapel"])
        self.assertEqual(
            report["final_state"]["entities"]["actor.player"]["components"]["location"]["current"],
            "location.market_square",
        )
        self.assertEqual(
            report["final_state"]["globals"]["quests"]["quest.bread_delivery"]["stage"],
            "completed",
        )
        self.assertEqual(
            report["final_state"]["entities"]["actor.elda"]["components"]["relationship"]["trust"],
            3,
        )
        self.assertNotIn(
            "item.bread_basket",
            report["final_state"]["entities"]["actor.player"]["components"]["inventory"]["items"],
        )
        self.assertIn(
            "item.warm_bread",
            report["final_state"]["entities"]["actor.player"]["components"]["inventory"]["items"],
        )

    def test_restricted_keep_rejects_travel_without_state_change(self) -> None:
        runtime = Runtime.from_file(MEDIEVAL_STATE, content_path=MEDIEVAL_CONTENT)
        runtime.execute(
            {
                "type": "space.travel_to",
                "actor": "actor.player",
                "target": "location.market_square",
                "args": {},
            }
        )
        before = runtime.snapshot()

        result = runtime.execute(
            {
                "type": "space.travel_to",
                "actor": "actor.player",
                "target": "location.lord_keep",
                "args": {},
            }
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.trace.failure_reason, "required access flag is missing")
        self.assertEqual(runtime.snapshot(), before)

    def test_phase_6_report_documents_required_deliverables(self) -> None:
        required_docs = [
            ROOT / "docs" / "phase_6_medieval_vertical_slice_report.md",
            ROOT / "docs" / "phase_6_module_gap_list.md",
            ROOT / "docs" / "phase_6_data_format_revision_notes.md",
        ]

        for path in required_docs:
            self.assertTrue(path.exists(), path)
            self.assertGreater(len(path.read_text(encoding="utf-8")), 100)

    def test_medieval_json_files_parse(self) -> None:
        for path in MEDIEVAL_ROOT.rglob("*.json"):
            with path.open("r", encoding="utf-8") as file:
                self.assertIsNotNone(json.load(file), path)


if __name__ == "__main__":
    unittest.main()
