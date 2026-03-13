"""Configuration management for repox."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib


DEFAULT_CONFIG: Dict[str, Dict[str, str]] = {
    "defaults": {
        "visibility": "private",
        "template": "none",
        "remote": "origin",
    },
    "templates": {
        "custom_dir": "",
    },
}


def default_config() -> Dict[str, Dict[str, str]]:
    return copy.deepcopy(DEFAULT_CONFIG)


def config_path() -> Path:
    override = os.getenv("REPOX_CONFIG_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".repox.toml"


def _ensure_shape(config: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    merged = default_config()
    for section, values in config.items():
        if section not in merged or not isinstance(values, dict):
            continue
        for key, value in values.items():
            if key in merged[section] and isinstance(value, str):
                merged[section][key] = value
    return merged


def render_toml(config: Dict[str, Dict[str, str]]) -> str:
    lines = []
    for section in ("defaults", "templates"):
        lines.append(f"[{section}]")
        for key, value in config[section].items():
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def save_config(config: Dict[str, Dict[str, str]], path: Optional[Path] = None) -> Path:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_toml(_ensure_shape(config)), encoding="utf-8")
    return target


def load_config(path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    target = path or config_path()
    if not target.exists():
        config = default_config()
        save_config(config, target)
        return config

    try:
        parsed = tomllib.loads(target.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise ValueError(f"Failed to read config file at {target}: {exc}") from exc
    return _ensure_shape(parsed)


def reset_config(path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    config = default_config()
    save_config(config, path)
    return config


def custom_template_dir(config: Dict[str, Dict[str, str]]) -> Optional[Path]:
    configured = config["templates"].get("custom_dir", "").strip()
    if not configured:
        return None
    return Path(configured).expanduser()
