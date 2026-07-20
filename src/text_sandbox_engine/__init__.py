"""Core runtime prototype for the text sandbox engine."""

from .content import ContentRepository
from .migrations import MigrationRegistry, MigrationReport
from .models import Command, CommandResult
from .persistence import LoadedSave, SaveMetadata, SaveReport
from .runtime import Runtime

__all__ = [
    "Command",
    "CommandResult",
    "ContentRepository",
    "LoadedSave",
    "MigrationRegistry",
    "MigrationReport",
    "Runtime",
    "SaveMetadata",
    "SaveReport",
]
