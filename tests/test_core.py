from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from repox.core import CommandExecutionError, RepoxError, check_prerequisites, init_local_repo, open_remote_repo, push_to_remote, apply_template


class CoreTests(unittest.TestCase):
    def test_apply_template_copies_files(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            apply_template("flask", root)

            self.assertTrue((root / "app.py").exists())
            self.assertTrue(
                (root / "requirements.txt").read_text(encoding="utf-8").strip()
            )

    def test_apply_template_rejects_unknown_template(self) -> None:
        with TemporaryDirectory() as tmp:
            with self.assertRaises(RepoxError):
                apply_template("unknown", Path(tmp))

    def test_init_local_repo_writes_gitignore_and_runs_git(self) -> None:
        calls = []

        def fake_run_command(args, cwd=None, check=True):
            calls.append((args, cwd, check))
            return mock.Mock(stdout="", stderr="", returncode=0)

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch("repox.core.run_command", side_effect=fake_run_command):
                init_local_repo(
                    destination=root,
                    remote_url="git@github.com:example/project.git",
                    gitignore_content="__pycache__/\n",
                )

            self.assertEqual(
                (root / ".gitignore").read_text(encoding="utf-8"), "__pycache__/\n"
            )
            self.assertEqual(
                [call[0] for call in calls],
                [
                    ["git", "init"],
                    ["git", "add", "."],
                    ["git", "commit", "-m", "Initial commit"],
                    ["git", "branch", "-M", "main"],
                    ["git", "remote", "add", "origin", "git@github.com:example/project.git"],
                ],
            )

    def test_init_local_repo_respects_custom_remote_name(self) -> None:
        calls = []

        def fake_run_command(args, cwd=None, check=True):
            calls.append(args)
            return mock.Mock(stdout="", stderr="", returncode=0)

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch("repox.core.run_command", side_effect=fake_run_command):
                init_local_repo(
                    destination=root,
                    remote_url="git@github.com:example/project.git",
                    remote_name="upstream",
                )

        self.assertIn(
            ["git", "remote", "add", "upstream", "git@github.com:example/project.git"],
            calls,
        )

    def test_check_prerequisites_reports_missing_auth(self) -> None:
        with mock.patch("repox.core.shutil.which", return_value="/usr/bin/tool"), mock.patch(
            "repox.core.run_command",
            side_effect=CommandExecutionError(
                args=["gh", "auth", "status"],
                stderr="not logged in",
                stdout="",
                returncode=1,
            ),
        ):
            with self.assertRaisesRegex(RepoxError, "gh auth login"):
                check_prerequisites()

    def test_push_to_remote_wraps_failures(self) -> None:
        with mock.patch(
            "repox.core.run_command",
            side_effect=CommandExecutionError(
                args=["git", "push", "-u", "origin", "main"],
                stderr="permission denied",
                stdout="",
                returncode=1,
            ),
        ):
            with self.assertRaisesRegex(RepoxError, "Failed to push to GitHub"):
                push_to_remote(Path.cwd())

    def test_push_to_remote_uses_custom_remote_name(self) -> None:
        with mock.patch("repox.core.run_command", return_value=mock.Mock(stdout="", stderr="", returncode=0)) as run_command:
            push_to_remote(Path.cwd(), remote_name="upstream")

        run_command.assert_called_once_with(
            ["git", "push", "-u", "upstream", "main"],
            cwd=Path.cwd(),
        )

    def test_open_remote_repo_wraps_failures(self) -> None:
        with mock.patch(
            "repox.core.run_command",
            side_effect=CommandExecutionError(
                args=["gh", "repo", "view", "demo", "--web"],
                stderr="cannot open browser",
                stdout="",
                returncode=1,
            ),
        ):
            with self.assertRaisesRegex(RepoxError, "opening it in the browser failed"):
                open_remote_repo("demo")


if __name__ == "__main__":
    unittest.main()
