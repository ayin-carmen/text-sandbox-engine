"""Presentation selection boundary for the phase 1 prototype."""

from __future__ import annotations

from typing import Any

from .models import Presentation


class SceneOrchestrator:
    def select(self, state: dict[str, Any], context: dict[str, Any]) -> Presentation:
        return Presentation(
            selected_scene=None,
            scene_candidate_report={
                "selected": None,
                "candidates": [],
                "filtered": [],
                "reason": "scene selection is reserved for phase 2",
            },
        )
