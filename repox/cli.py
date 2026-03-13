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
    push_to_remote,
)
from repox.detect import suggest_gitignore
from repox.templates import discover_templates


Step = Tuple[str, Callable[[], None]]


def prompt_for_name() -> str:
    if questionary is not None:
        response = questionary.text("Repository name:").ask()
        if response is None or not response.strip():
            raise click.ClickException("Repository name is required.")
        return response.strip()
    return click.prompt("Repository name", type=str).strip()


def prompt_for_template(choices: Sequence[str]) -> str:
    if questionary is not None:
        response = questionary.select("Template:", choices=list(choices)).ask()
        if response is None:
            raise click.ClickException("Template selection was cancelled.")
        return response
    return click.prompt(
        "Template",
        type=click.Choice(list(choices), case_sensitive=False),
        default="none",
        show_choices=True,
    )


def execute_steps(steps: Iterable[Step]) -> None:
    for index, (label, operation) in enumerate(steps, start=1):
        click.echo(f"[{index}] {label} ... ", nl=False)
        try:
            operation()
        except RepoxError as exc:
            click.echo("FAIL")
            raise click.ClickException(str(exc)) from exc
        click.echo("OK")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("name", required=False)
@click.option("--public", "visibility", flag_value="public", default=True)
@click.option("--private", "visibility", flag_value="private")
@click.option(
    "--template",
    type=str,
    default=None,
    help="Bundled project template to apply.",
)
@click.version_option(version=__version__)
def main(name: Optional[str], visibility: str, template: Optional[str]) -> None:
    """Create a GitHub repository from the terminal."""
    destination = Path.cwd()
    templates = discover_templates()
    template_choices = ["none", *templates.keys()]

    repo_name = name or prompt_for_name()
    selected_template = template or prompt_for_template(template_choices)
    if selected_template not in template_choices:
        raise click.ClickException(
            f"Unknown template '{selected_template}'. Choose from: {', '.join(template_choices)}."
        )

    gitignore_name = suggest_gitignore(destination, selected_template)
    remote_url_holder = {"url": ""}
    gitignore_holder = {"content": None}

    steps: Sequence[Step] = (
        ("Checking prerequisites", check_prerequisites),
        (
            "Creating GitHub repository",
            lambda: remote_url_holder.__setitem__(
                "url", create_remote_repo(repo_name, visibility)
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
    click.echo(f"Repository '{repo_name}' created successfully.")


if __name__ == "__main__":
    main()
