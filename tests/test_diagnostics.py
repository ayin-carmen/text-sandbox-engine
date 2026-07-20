from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from text_sandbox_engine.cli import main as cli_main
from text_sandbox_engine.debug import changed_by_report, diff_state_files, replay_commands, scene_candidate_report
from text_sandbox_engine.persistence import load_world_state, save_world_state

EXAMPLE_STATE = ROOT / "examples" / "minimal_world_state.json"
EXAMPLE_CONTENT = ROOT / "examples" / "content"
EXAMPLE_COMMANDS = ROOT / "examples" / "commands" / "playable_loop.json"


class DiagnosticsTests(unittest.TestCase):
    def test_replay_commands_reports_traces_and_state_changes(self) -> None:
        report = replay_commands(EXAMPLE_STATE, EXAMPLE_COMMANDS, content_path=EXAMPLE_CONTENT)

        self.assertEqual(report["status"], "succeeded")
        self.assertEqual(report["command_count"], 3)
        changed_paths = {change["path"] for change in report["state_diff"]["changes"]}
        self.assertIn("flags.met_market", changed_paths)
        self.assertIn("flags.talked_to_mara", changed_paths)
        self.assertIn("globals.clock.tick", changed_paths)

    def test_changed_by_report_finds_command_that_modified_path(self) -> None:
        report = replay_commands(EXAMPLE_STATE, EXAMPLE_COMMANDS, content_path=EXAMPLE_CONTENT)

        matches = changed_by_report(report["traces"][0], "entities.actor.player.components.location.current")

        self.assertEqual(matches[0]["command_type"], "space.travel_to")
        self.assertEqual(matches[0]["after"], "location.market")

    def test_scene_candidate_report_explains_filtered_scenes(self) -> None:
        report = scene_candidate_report(EXAMPLE_STATE, EXAMPLE_CONTENT)

        self.assertIsNone(report["selected"])
        self.assertEqual(len(report["filtered"]), 2)
        self.assertTrue(all("location mismatch" in item["reason"] for item in report["filtered"]))

    def test_state_diff_compares_two_saved_snapshots(self) -> None:
        before = load_world_state(EXAMPLE_STATE)
        after = dict(before)
        after["flags"] = dict(before["flags"])
        after["flags"]["met_market"] = True

        with tempfile.TemporaryDirectory() as tmpdir:
            before_path = Path(tmpdir) / "before.json"
            after_path = Path(tmpdir) / "after.json"
            save_world_state(before_path, before)
            save_world_state(after_path, after)
            report = diff_state_files(before_path, after_path)

        self.assertEqual(
            report["changes"],
            [
                {
                    "path": "flags.met_market",
                    "status": "changed",
                    "before": False,
                    "after": True,
                }
            ],
        )

    def test_state_diff_reads_utf8_bom_json(self) -> None:
        before = load_world_state(EXAMPLE_STATE)
        after = dict(before)
        after["flags"] = dict(before["flags"])
        after["flags"]["met_market"] = True

        with tempfile.TemporaryDirectory() as tmpdir:
            before_path = Path(tmpdir) / "before.json"
            after_path = Path(tmpdir) / "after.json"
            before_path.write_text(json.dumps(before), encoding="utf-8-sig")
            after_path.write_text(json.dumps(after), encoding="utf-8-sig")
            report = diff_state_files(before_path, after_path)

        self.assertEqual(report["changes"][0]["path"], "flags.met_market")

    def test_cli_content_validate_outputs_json(self) -> None:
        code, payload = self.run_cli(["content-validate", "--content", str(EXAMPLE_CONTENT)])

        self.assertEqual(code, 0)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["scene_count"], 2)

    def test_cli_replay_outputs_command_trace_report(self) -> None:
        code, payload = self.run_cli(
            [
                "replay",
                "--state",
                str(EXAMPLE_STATE),
                "--content",
                str(EXAMPLE_CONTENT),
                "--commands",
                str(EXAMPLE_COMMANDS),
            ]
        )

        self.assertEqual(code, 0)
        self.assertEqual(payload["command_count"], 3)
        self.assertEqual(payload["traces"][0]["command"]["type"], "space.travel_to")

    def test_cli_scene_report_outputs_candidate_report(self) -> None:
        code, payload = self.run_cli(
            [
                "scene-report",
                "--state",
                str(EXAMPLE_STATE),
                "--content",
                str(EXAMPLE_CONTENT),
            ]
        )

        self.assertEqual(code, 0)
        self.assertIsNone(payload["selected"])
        self.assertEqual(len(payload["filtered"]), 2)

    def test_cli_state_diff_outputs_changes(self) -> None:
        before = load_world_state(EXAMPLE_STATE)
        after = dict(before)
        after["flags"] = dict(before["flags"])
        after["flags"]["talked_to_mara"] = True

        with tempfile.TemporaryDirectory() as tmpdir:
            before_path = Path(tmpdir) / "before.json"
            after_path = Path(tmpdir) / "after.json"
            save_world_state(before_path, before)
            save_world_state(after_path, after)
            code, payload = self.run_cli(
                [
                    "state-diff",
                    "--before",
                    str(before_path),
                    "--after",
                    str(after_path),
                ]
            )

        self.assertEqual(code, 0)
        self.assertEqual(payload["changes"][0]["path"], "flags.talked_to_mara")

    def test_cli_changed_by_outputs_matching_command(self) -> None:
        replay_report = replay_commands(EXAMPLE_STATE, EXAMPLE_COMMANDS, content_path=EXAMPLE_CONTENT)

        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "trace.json"
            trace_path.write_text(
                json.dumps(replay_report["traces"][0]),
                encoding="utf-8",
            )
            code, payload = self.run_cli(
                [
                    "changed-by",
                    "--trace",
                    str(trace_path),
                    "--path",
                    "entities.actor.player.components.location.current",
                ]
            )

        self.assertEqual(code, 0)
        self.assertEqual(payload["matches"][0]["command_type"], "space.travel_to")

    def run_cli(self, argv: list[str]) -> tuple[int, dict]:
        output = StringIO()
        with redirect_stdout(output):
            code = cli_main(argv)
        return code, json.loads(output.getvalue())


if __name__ == "__main__":
    unittest.main()
