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
from repox.config import config_path, custom_template_dir, load_config, reset_config, save_config
from repox.core import (
    RepoxError,
    apply_template,
    check_prerequisites,
    create_remote_repo,
    fetch_gitignore,
    get_git_author_name,
    init_local_repo,
    open_remote_repo,
    push_to_remote,
    render_template_content,
    terminal_supports_color,
)
from repox.detect import suggest_gitignore
from repox.templates import discover_template_manifests


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


class RepoGroup(click.Group):
    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        should_dispatch_to_create = not args
        if args:
            first = click.utils.make_str(args[0])
            should_dispatch_to_create = (
                first not in self.commands
                and first not in {"-h", "--help", "--version"}
            )
        if should_dispatch_to_create:
            args.insert(0, "create")
        return super().parse_args(ctx, args)

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        if HEADER:
            click.echo(style(HEADER.rstrip("\n"), "magenta", bold=True))
            click.echo()
        super().format_help(ctx, formatter)
        click.echo()
        click.echo(HELP_TEXT)

    def list_commands(self, ctx: click.Context) -> list[str]:
        return [name for name in super().list_commands(ctx) if name != "create"]


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


def prompt_for_template(choices: Sequence[str], default: str = "none") -> str:
    if questionary is not None:
        response = questionary.select(
            "Template:",
            choices=list(choices),
            default=default,
        ).ask()
        if response is None:
            raise click.ClickException("Template selection was cancelled.")
        return response
    return click.prompt(
        "Template",
        type=click.Choice(list(choices), case_sensitive=False),
        default=default,
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


def render_config(config: dict) -> str:
    return "\n".join(
        [
            f"config: {config_path()}",
            f"visibility: {config['defaults']['visibility']}",
            f"template: {config['defaults']['template']}",
            f"remote: {config['defaults']['remote']}",
            f"custom_template_dir: {config['templates']['custom_dir'] or 'none'}",
        ]
    )


def render_templates_table(templates: Sequence[tuple[str, str]]) -> str:
    if not templates:
        return "No templates available."

    width = max(len(name) for name, _ in templates)
    return "\n".join(
        f"{name.ljust(width)}  {description}"
        for name, description in templates
    )


def prompt_for_config_value(message: str, default: str, choices: Optional[Sequence[str]] = None) -> str:
    if questionary is not None:
        if choices is not None:
            response = questionary.select(message, choices=list(choices), default=default).ask()
        else:
            response = questionary.text(message, default=default).ask()
        if response is None:
            raise click.ClickException("Configuration update was cancelled.")
        return str(response).strip()

    if choices is not None:
        return str(
            click.prompt(
                message,
                type=click.Choice(list(choices), case_sensitive=False),
                default=default,
                show_choices=True,
            )
        )
    return click.prompt(message, type=str, default=default).strip()


@click.group(
    cls=RepoGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Create a GitHub repository from the terminal.",
    invoke_without_command=True,
)
@click.version_option(version=__version__)
def main() -> None:
    """Create a GitHub repository from the terminal."""
    return


@main.command("create", cls=click.Command, hidden=True)
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
def create_command(
    name: Optional[str],
    visibility: Optional[str],
    template: Optional[str],
    yes: bool,
    open_in_browser: bool,
) -> None:
    """Create a GitHub repository from the terminal."""

    destination = Path.cwd()
    config = load_config()
    configured_custom_dir = custom_template_dir(config)
    templates = discover_template_manifests(configured_custom_dir)
    template_choices = ["none", *templates.keys()]
    default_visibility = config["defaults"]["visibility"]
    default_template = config["defaults"]["template"]
    remote_name = config["defaults"]["remote"]

    click.echo(style(HEADER.rstrip("\n"), "magenta", bold=True))
    click.echo()

    repo_name = name or prompt_for_name()
    selected_visibility = visibility or default_visibility
    if template is not None:
        selected_template = template
    elif default_template != "none" and default_template in template_choices:
        selected_template = default_template
    else:
        selected_template = prompt_for_template(template_choices, default="none")
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
    template_variables = None
    if selected_template != "none":
        template_variables = {
            "repo_name": repo_name,
            "author": get_git_author_name(destination),
        }

    steps: Sequence[Step] = (
        ("Checking prerequisites", check_prerequisites),
        (
            "Creating GitHub repository",
            lambda: remote_url_holder.__setitem__(
                "url", create_remote_repo(repo_name, selected_visibility)
            ),
        ),
        (
            "Applying template",
            lambda: apply_template(
                selected_template,
                destination,
                custom_template_dir=configured_custom_dir,
                variables=template_variables,
            ),
        ),
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
                remote_name=remote_name,
            ),
        ),
        ("Pushing to remote", lambda: push_to_remote(destination, remote_name=remote_name)),
    )

    execute_steps(steps)
    if open_in_browser:
        click.echo(info("Opening repository in browser..."))
        try:
            open_remote_repo(repo_name)
        except RepoxError as exc:
            raise click.ClickException(str(exc)) from exc

    if selected_template != "none":
        post_install = templates[selected_template].post_install
        if post_install:
            click.echo(info(f"Next steps: {render_template_content(post_install, template_variables)}"))

    click.echo(ok(f"Repository '{repo_name}' created successfully."))


@main.command("config")
@click.option("--show", "show_config", is_flag=True, help="Print the current config.")
@click.option("--reset", "reset_to_defaults", is_flag=True, help="Reset the config to defaults.")
def config_command(show_config: bool, reset_to_defaults: bool) -> None:
    """View or update repox configuration."""
    if show_config and reset_to_defaults:
        raise click.ClickException("Use either --show or --reset, not both.")

    if reset_to_defaults:
        config = reset_config()
        click.echo(ok(f"Configuration reset at {config_path()}"))
        click.echo(render_config(config))
        return

    config = load_config()
    if show_config:
        click.echo(render_config(config))
        return

    templates = ["none", *discover_template_manifests(custom_template_dir(config)).keys()]
    config["defaults"]["visibility"] = prompt_for_config_value(
        "Default visibility:",
        config["defaults"]["visibility"],
        choices=["private", "public"],
    )
    config["defaults"]["template"] = prompt_for_config_value(
        "Default template:",
        config["defaults"]["template"]
        if config["defaults"]["template"] in templates
        else "none",
        choices=templates,
    )
    config["defaults"]["remote"] = prompt_for_config_value(
        "Default remote name:",
        config["defaults"]["remote"],
    )
    config["templates"]["custom_dir"] = prompt_for_config_value(
        "Custom template directory (blank to disable):",
        config["templates"]["custom_dir"],
    )

    save_config(config)
    click.echo(ok(f"Configuration saved to {config_path()}"))
    click.echo(render_config(config))


@main.command("templates")
def templates_command() -> None:
    """List available templates."""
    config = load_config()
    manifests = discover_template_manifests(custom_template_dir(config))
    rows = [
        (manifest.slug, manifest.description)
        for manifest in manifests.values()
    ]
    click.echo(render_templates_table(rows))


if __name__ == "__main__":
    main()
