"""Command line diagnostics for the text sandbox engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .debug import (
    changed_by_report,
    diff_state_files,
    replay_commands,
    scene_candidate_report,
    validate_content,
)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report = args.func(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if isinstance(report, dict) and report.get("passed") is False:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="text-sandbox-engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    content_validate = subparsers.add_parser("content-validate")
    content_validate.add_argument("--content", required=True)
    content_validate.set_defaults(func=_content_validate)

    replay = subparsers.add_parser("replay")
    replay.add_argument("--state", required=True)
    replay.add_argument("--commands", required=True)
    replay.add_argument("--content")
    replay.set_defaults(func=_replay)

    scene_report = subparsers.add_parser("scene-report")
    scene_report.add_argument("--state", required=True)
    scene_report.add_argument("--content", required=True)
    scene_report.add_argument("--actor", default="actor.player")
    scene_report.set_defaults(func=_scene_report)

    state_diff = subparsers.add_parser("state-diff")
    state_diff.add_argument("--before", required=True)
    state_diff.add_argument("--after", required=True)
    state_diff.set_defaults(func=_state_diff)

    changed_by = subparsers.add_parser("changed-by")
    changed_by.add_argument("--trace", required=True)
    changed_by.add_argument("--path", required=True)
    changed_by.set_defaults(func=_changed_by)

    return parser


def _content_validate(args: argparse.Namespace) -> dict[str, Any]:
    return validate_content(args.content)


def _replay(args: argparse.Namespace) -> dict[str, Any]:
    return replay_commands(args.state, args.commands, content_path=args.content)


def _scene_report(args: argparse.Namespace) -> dict[str, Any]:
    return scene_candidate_report(args.state, args.content, actor=args.actor)


def _state_diff(args: argparse.Namespace) -> dict[str, Any]:
    return diff_state_files(args.before, args.after)


def _changed_by(args: argparse.Namespace) -> dict[str, Any]:
    with Path(args.trace).open("r", encoding="utf-8-sig") as file:
        trace = json.load(file)
    return {"matches": changed_by_report(trace, args.path)}


if __name__ == "__main__":
    sys.exit(main())
