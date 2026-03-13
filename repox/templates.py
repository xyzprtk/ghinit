"""Template discovery helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib


@dataclass(frozen=True)
class TemplateManifest:
    slug: str
    path: Path
    name: str
    description: str
    language: str
    post_install: str


DEFAULT_TEMPLATE_METADATA = {
    "name": "",
    "description": "",
    "language": "",
    "post_install": "",
}


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


def load_manifest(template_name: str, template_dir: Path) -> TemplateManifest:
    manifest_path = template_dir / "template.toml"
    values = dict(DEFAULT_TEMPLATE_METADATA)
    if manifest_path.exists():
        parsed = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        meta = parsed.get("meta", {})
        if isinstance(meta, dict):
            for key in values:
                value = meta.get(key)
                if isinstance(value, str):
                    values[key] = value

    return TemplateManifest(
        slug=template_name,
        path=template_dir,
        name=values["name"] or template_name,
        description=values["description"] or "No description provided.",
        language=values["language"],
        post_install=values["post_install"],
    )


def discover_template_manifests(custom_dir: Optional[Path] = None) -> Dict[str, TemplateManifest]:
    templates = discover_templates(custom_dir)
    manifests = {
        name: load_manifest(name, path)
        for name, path in templates.items()
    }
    return dict(sorted(manifests.items()))
