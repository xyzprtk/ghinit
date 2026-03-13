from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from repox.detect import detect_language, suggest_gitignore


class DetectTests(unittest.TestCase):
    def test_detect_language_from_python_files(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('hi')\n", encoding="utf-8")

            self.assertEqual(detect_language(root), "Python")

    def test_suggest_gitignore_prefers_template(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<!doctype html>\n", encoding="utf-8")

            self.assertEqual(suggest_gitignore(root, "flask"), "Python")


if __name__ == "__main__":
    unittest.main()
