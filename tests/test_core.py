from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from repox.core import RepoxError, apply_template, init_local_repo


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


if __name__ == "__main__":
    unittest.main()
