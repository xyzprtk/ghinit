import unittest
from unittest import mock

from click.testing import CliRunner

from repox.cli import main


class CliTests(unittest.TestCase):
    def test_cli_runs_with_prompted_name_and_template(self) -> None:
        operations = []

        with mock.patch("repox.cli.prompt_for_name", return_value="demo-repo"), mock.patch(
            "repox.cli.prompt_for_visibility", return_value="private"
        ), mock.patch(
            "repox.cli.prompt_for_template", return_value="flask"
        ), mock.patch("repox.cli.suggest_gitignore", return_value="Python"), mock.patch(
            "repox.cli.confirm_execution", return_value=True
        ), mock.patch(
            "repox.cli.check_prerequisites",
            side_effect=lambda: operations.append("check_prerequisites"),
        ), mock.patch(
            "repox.cli.create_remote_repo",
            side_effect=lambda name, visibility: operations.append(
                ("create_remote_repo", name, visibility)
            )
            or "git@github.com:user/demo-repo.git",
        ), mock.patch(
            "repox.cli.apply_template",
            side_effect=lambda template, destination: operations.append(
                ("apply_template", template, destination.name)
            ),
        ), mock.patch(
            "repox.cli.fetch_gitignore",
            side_effect=lambda gitignore: operations.append(("fetch_gitignore", gitignore))
            or "__pycache__/\n",
        ), mock.patch(
            "repox.cli.init_local_repo",
            side_effect=lambda destination, remote_url, gitignore_content: operations.append(
                ("init_local_repo", destination.name, remote_url, gitignore_content)
            ),
        ), mock.patch(
            "repox.cli.push_to_remote",
            side_effect=lambda destination: operations.append(("push_to_remote", destination.name)),
        ):
            runner = CliRunner()
            result = runner.invoke(main, [])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Repository 'demo-repo' created successfully.", result.output)
        self.assertEqual(
            operations,
            [
                "check_prerequisites",
                ("create_remote_repo", "demo-repo", "private"),
                ("apply_template", "flask", "repox"),
                ("fetch_gitignore", "Python"),
                (
                    "init_local_repo",
                    "repox",
                    "git@github.com:user/demo-repo.git",
                    "__pycache__/\n",
                ),
                ("push_to_remote", "repox"),
            ],
        )

    def test_cli_skips_confirmation_with_yes_and_opens_browser(self) -> None:
        operations = []

        with mock.patch("repox.cli.suggest_gitignore", return_value=None), mock.patch(
            "repox.cli.check_prerequisites",
            side_effect=lambda: operations.append("check_prerequisites"),
        ), mock.patch(
            "repox.cli.create_remote_repo",
            side_effect=lambda name, visibility: operations.append(
                ("create_remote_repo", name, visibility)
            )
            or "git@github.com:user/demo.git",
        ), mock.patch(
            "repox.cli.apply_template",
            side_effect=lambda template, destination: operations.append(
                ("apply_template", template, destination.name)
            ),
        ), mock.patch(
            "repox.cli.fetch_gitignore",
            side_effect=lambda gitignore: operations.append(("fetch_gitignore", gitignore)),
        ), mock.patch(
            "repox.cli.init_local_repo",
            side_effect=lambda destination, remote_url, gitignore_content: operations.append(
                ("init_local_repo", destination.name, remote_url, gitignore_content)
            ),
        ), mock.patch(
            "repox.cli.push_to_remote",
            side_effect=lambda destination: operations.append(("push_to_remote", destination.name)),
        ), mock.patch(
            "repox.cli.open_remote_repo",
            side_effect=lambda name: operations.append(("open_remote_repo", name)),
        ), mock.patch("repox.cli.confirm_execution") as confirm_execution:
            runner = CliRunner()
            result = runner.invoke(main, ["demo", "--public", "--template", "none", "--yes", "--open"])

        self.assertEqual(result.exit_code, 0)
        self.assertFalse(confirm_execution.called)
        self.assertIn("Opening repository in browser", result.output)
        self.assertEqual(
            operations,
            [
                "check_prerequisites",
                ("create_remote_repo", "demo", "public"),
                ("apply_template", "none", "repox"),
                ("fetch_gitignore", None),
                ("init_local_repo", "repox", "git@github.com:user/demo.git", None),
                ("push_to_remote", "repox"),
                ("open_remote_repo", "demo"),
            ],
        )

    def test_cli_aborts_when_confirmation_declined(self) -> None:
        with mock.patch("repox.cli.prompt_for_name", return_value="demo-repo"), mock.patch(
            "repox.cli.prompt_for_visibility", return_value="private"
        ), mock.patch(
            "repox.cli.prompt_for_template", return_value="none"
        ), mock.patch(
            "repox.cli.suggest_gitignore", return_value=None
        ), mock.patch(
            "repox.cli.confirm_execution", return_value=False
        ), mock.patch("repox.cli.execute_steps") as execute_steps:
            runner = CliRunner()
            result = runner.invoke(main, [])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Aborted.", result.output)
        self.assertFalse(execute_steps.called)


if __name__ == "__main__":
    unittest.main()
