"""Template discovery helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict


def package_templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def discover_templates() -> Dict[str, Path]:
    templates: Dict[str, Path] = {}
    root = package_templates_dir()
    if not root.exists():
        return templates

    for child in root.iterdir():
        if child.is_dir():
            templates[child.name] = child

    return dict(sorted(templates.items()))
