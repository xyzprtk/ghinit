import click


@click.command()
def main() -> None:
    click.echo("{{repo_name}} by {{author}}")


if __name__ == "__main__":
    main()
