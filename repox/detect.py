"""Language detection and gitignore selection."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, Optional

EXTENSION_TO_GITIGNORE: Dict[str, str] = {
    ".py": "Python",
    ".js": "Node",
    ".jsx": "Node",
    ".ts": "Node",
    ".tsx": "Node",
    ".html": "Node",
    ".css": "Node",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
}

TEMPLATE_TO_GITIGNORE: Dict[str, str] = {
    "flask": "Python",
    "fastapi": "Python",
    "react": "Node",
}

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
}


def iter_project_files(root: Path) -> Iterable[Path]:
    """Yield files suitable for lightweight language detection."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        yield path


def detect_language(root: Path) -> Optional[str]:
    """Return the most likely gitignore template name for the project."""
    counts = Counter()
    for path in iter_project_files(root):
        gitignore_name = EXTENSION_TO_GITIGNORE.get(path.suffix.lower())
        if gitignore_name:
            counts[gitignore_name] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def suggest_gitignore(root: Path, template: Optional[str] = None) -> Optional[str]:
    """Prefer the selected template, then fall back to extension-based detection."""
    if template:
        template_match = TEMPLATE_TO_GITIGNORE.get(template)
        if template_match:
            return template_match
    return detect_language(root)
