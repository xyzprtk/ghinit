"""Template discovery helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional


def package_templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def _discover_from_dir(root: Path) -> Dict[str, Path]:
    templates: Dict[str, Path] = {}
    if not root.exists():
        return templates

    for child in root.iterdir():
        if child.is_dir():
            templates[child.name] = child
    return templates


def discover_templates(custom_dir: Optional[Path] = None) -> Dict[str, Path]:
    templates = _discover_from_dir(package_templates_dir())
    if custom_dir is not None:
        templates.update(_discover_from_dir(custom_dir))
    return dict(sorted(templates.items()))
