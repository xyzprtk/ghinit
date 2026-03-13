import unittest
from unittest import mock

from click.testing import CliRunner

from repox.cli import main


class CliTests(unittest.TestCase):
    def test_cli_runs_with_prompted_name_and_template(self) -> None:
        operations = []

        with mock.patch("repox.cli.prompt_for_name", return_value="demo-repo"), mock.patch(
            "repox.cli.prompt_for_template", return_value="flask"
        ), mock.patch("repox.cli.suggest_gitignore", return_value="Python"), mock.patch(
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
                ("create_remote_repo", "demo-repo", "public"),
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


if __name__ == "__main__":
    unittest.main()
