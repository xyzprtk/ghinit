"""Core git and GitHub operations for repox."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from repox.templates import discover_templates


class RepoxError(RuntimeError):
    """Raised when a repo creation step fails."""


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


def run_command(
    args: Iterable[str],
    cwd: Optional[Path] = None,
    check: bool = True,
) -> CommandResult:
    completed = subprocess.run(
        list(args),
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )
    result = CommandResult(
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
        returncode=completed.returncode,
    )
    if check and result.returncode != 0:
        command = " ".join(args)
        message = result.stderr or result.stdout or f"Command failed: {command}"
        raise RepoxError(message)
    return result


def check_prerequisites() -> None:
    for tool in ("git", "gh"):
        if shutil.which(tool) is None:
            raise RepoxError(
                f"Missing required dependency '{tool}'. Install it before running repo."
            )


def get_authenticated_username() -> str:
    result = run_command(["gh", "api", "user"])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RepoxError("Failed to parse GitHub username from gh api user output.") from exc

    username = payload.get("login")
    if not username:
        raise RepoxError("Unable to determine authenticated GitHub username.")
    return str(username)


def create_remote_repo(name: str, visibility: str) -> str:
    if visibility not in {"public", "private"}:
        raise RepoxError(f"Unsupported visibility '{visibility}'.")

    username = get_authenticated_username()
    flag = f"--{visibility}"
    run_command(["gh", "repo", "create", name, flag, "--confirm"])
    return f"git@github.com:{username}/{name}.git"


def fetch_gitignore(gitignore_name: Optional[str]) -> Optional[str]:
    if not gitignore_name:
        return None

    result = run_command(
        [
            "gh",
            "api",
            f"/gitignore/templates/{gitignore_name}",
            "--jq",
            ".source",
        ]
    )
    return result.stdout + "\n" if result.stdout else None


def apply_template(template: Optional[str], destination: Path) -> None:
    if not template or template == "none":
        return

    templates = discover_templates()
    template_dir = templates.get(template)
    if template_dir is None:
        available = ", ".join(templates) or "none"
        raise RepoxError(
            f"Unknown template '{template}'. Available templates: {available}."
        )

    for source in template_dir.rglob("*"):
        relative = source.relative_to(template_dir)
        target = destination / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def init_local_repo(
    destination: Path,
    remote_url: str,
    gitignore_content: Optional[str] = None,
) -> None:
    if gitignore_content:
        gitignore_path = destination / ".gitignore"
        existing = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
        if existing and not existing.endswith("\n"):
            existing += "\n"
        gitignore_path.write_text(existing + gitignore_content, encoding="utf-8")

    run_command(["git", "init"], cwd=destination)
    run_command(["git", "add", "."], cwd=destination)
    run_command(["git", "commit", "-m", "Initial commit"], cwd=destination)
    run_command(["git", "branch", "-M", "main"], cwd=destination)
    run_command(["git", "remote", "add", "origin", remote_url], cwd=destination)


def push_to_remote(destination: Path) -> None:
    run_command(["git", "push", "-u", "origin", "main"], cwd=destination)
