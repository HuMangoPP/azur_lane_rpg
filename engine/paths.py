"""Resolve files shipped alongside the game independently of the working directory."""

from __future__ import annotations

import sys
from pathlib import Path


def application_root() -> Path:
    """Return the directory containing the game's external runtime files."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str | Path) -> Path:
    """Return an absolute path beneath the application's runtime root."""
    return application_root().joinpath(*parts)


SAVE_FILE_PATH = resource_path("data", "save_file.json")
