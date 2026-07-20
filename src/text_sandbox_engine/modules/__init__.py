"""Minimal gameplay modules for the phase 3 prototype."""

from __future__ import annotations

from .actor import register_actor_module
from .narrative import register_narrative_module
from .space import register_space_module
from .time import register_time_module


def register_default_modules(registry: object) -> None:
    register_time_module(registry)
    register_space_module(registry)
    register_narrative_module(registry)
    register_actor_module(registry)
