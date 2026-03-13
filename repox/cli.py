"""Click entry point for repox."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence, Tuple

import click

try:
    import questionary
except ImportError:  # pragma: no cover - exercised in sandboxed environments
    questionary = None

from repox import __version__
from repox.core import (
    RepoxError,
    apply_template,
    check_prerequisites,
    create_remote_repo,
    fetch_gitignore,
    init_local_repo,
    open_remote_repo,
    push_to_remote,
    terminal_supports_color,
)
from repox.detect import suggest_gitignore
from repox.templates import discover_templates


Step = Tuple[str, Callable[[], None]]
HEADER = r"""
   ____  ___  ____  ____  __
  / __ \/ _ \/ __ \/ __ \/ /
 / /_/ /  __/ /_/ / /_/ / /__
/ .___/\___/ .___/\____/____/
/_/       /_/
"""

HELP_TEXT = """Create GitHub repositories without leaving the terminal.

Examples:
  repo
  repo my-app --private --template flask
  repo my-app --yes --open
"""


def style(text: str, fg: str, *, bold: bool = False) -> str:
    if not terminal_supports_color():
        return text
    return click.style(text, fg=fg, bold=bold)


def ok(text: str) -> str:
    return style(text, "green", bold=True)


def err(text: str) -> str:
    return style(text, "red", bold=True)


def info(text: str) -> str:
    return style(text, "cyan")


def warn(text: str) -> str:
    return style(text, "yellow")


def step_label(current: int, total: int, label: str) -> str:
    return style(f"[{current}/{total}] {label}", "blue", bold=True)


class RepoCommand(click.Command):
    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        if HEADER:
            click.echo(style(HEADER.rstrip("\n"), "magenta", bold=True))
            click.echo()
        super().format_help(ctx, formatter)
        click.echo()
        click.echo(HELP_TEXT)


def prompt_for_name() -> str:
    if questionary is not None:
        response = questionary.text("Repository name:", default=Path.cwd().name).ask()
        if response is None or not response.strip():
            raise click.ClickException("Repository name is required.")
        return response.strip()
    return click.prompt("Repository name", type=str, default=Path.cwd().name).strip()


def prompt_for_visibility(default: str) -> str:
    choices = ["private", "public"]
    if questionary is not None:
        response = questionary.select(
            "Visibility:",
            choices=choices,
            default=default,
        ).ask()
        if response is None:
            raise click.ClickException("Visibility selection was cancelled.")
        return response
    return click.prompt(
        "Visibility",
        type=click.Choice(choices, case_sensitive=False),
        default=default,
        show_choices=True,
    )


def prompt_for_template(choices: Sequence[str]) -> str:
    if questionary is not None:
        response = questionary.select(
            "Template:",
            choices=list(choices),
            default="none",
        ).ask()
        if response is None:
            raise click.ClickException("Template selection was cancelled.")
        return response
    return click.prompt(
        "Template",
        type=click.Choice(list(choices), case_sensitive=False),
        default="none",
        show_choices=True,
    )


def confirm_execution(repo_name: str, visibility: str, template: str, gitignore_name: Optional[str]) -> bool:
    click.echo(style("Summary", "white", bold=True))
    click.echo(f"  name: {info(repo_name)}")
    click.echo(f"  visibility: {info(visibility)}")
    click.echo(f"  template: {info(template)}")
    click.echo(f"  gitignore: {info(gitignore_name or 'none')}")

    if questionary is not None:
        response = questionary.confirm("Create this repository now?", default=True).ask()
        return bool(response)
    return click.confirm("Create this repository now?", default=True)


def execute_steps(steps: Sequence[Step]) -> None:
    total = len(steps)
    for index, (label, operation) in enumerate(steps, start=1):
        click.echo(f"{step_label(index, total, label)} ... ", nl=False)
        try:
            operation()
        except RepoxError as exc:
            click.echo(err("FAIL"))
            raise click.ClickException(str(exc)) from exc
        click.echo(ok("OK"))


@click.command(
    cls=RepoCommand,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Create a GitHub repository from the terminal.",
)
@click.argument("name", required=False)
@click.option("--public", "visibility", flag_value="public", default=None, help="Create a public repository.")
@click.option("--private", "visibility", flag_value="private")
@click.option(
    "--template",
    type=str,
    default=None,
    help="Bundled project template to apply.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip the confirmation prompt.",
)
@click.option(
    "--open",
    "open_in_browser",
    is_flag=True,
    help="Open the created repository in the browser after push.",
)
@click.version_option(version=__version__)
def main(
    name: Optional[str],
    visibility: Optional[str],
    template: Optional[str],
    yes: bool,
    open_in_browser: bool,
) -> None:
    """Create a GitHub repository from the terminal."""
    destination = Path.cwd()
    templates = discover_templates()
    template_choices = ["none", *templates.keys()]

    click.echo(style(HEADER.rstrip("\n"), "magenta", bold=True))
    click.echo()

    repo_name = name or prompt_for_name()
    selected_visibility = visibility or prompt_for_visibility("private")
    selected_template = template or prompt_for_template(template_choices)
    if selected_template not in template_choices:
        raise click.ClickException(
            f"Unknown template '{selected_template}'. Choose from: {', '.join(template_choices)}."
        )

    gitignore_name = suggest_gitignore(destination, selected_template)
    if not yes and not confirm_execution(
        repo_name=repo_name,
        visibility=selected_visibility,
        template=selected_template,
        gitignore_name=gitignore_name,
    ):
        click.echo(warn("Aborted."))
        return

    remote_url_holder = {"url": ""}
    gitignore_holder = {"content": None}

    steps: Sequence[Step] = (
        ("Checking prerequisites", check_prerequisites),
        (
            "Creating GitHub repository",
            lambda: remote_url_holder.__setitem__(
                "url", create_remote_repo(repo_name, selected_visibility)
            ),
        ),
        ("Applying template", lambda: apply_template(selected_template, destination)),
        (
            "Fetching .gitignore",
            lambda: gitignore_holder.__setitem__(
                "content", fetch_gitignore(gitignore_name)
            ),
        ),
        (
            "Initializing local git repository",
            lambda: init_local_repo(
                destination=destination,
                remote_url=remote_url_holder["url"],
                gitignore_content=gitignore_holder["content"],
            ),
        ),
        ("Pushing to remote", lambda: push_to_remote(destination)),
    )

    execute_steps(steps)
    if open_in_browser:
        click.echo(info("Opening repository in browser..."))
        try:
            open_remote_repo(repo_name)
        except RepoxError as exc:
            raise click.ClickException(str(exc)) from exc

    click.echo(ok(f"Repository '{repo_name}' created successfully."))


if __name__ == "__main__":
    main()
