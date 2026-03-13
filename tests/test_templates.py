import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from repox.templates import discover_template_manifests


class TemplateTests(unittest.TestCase):
    def test_discover_template_manifests_reads_builtin_metadata(self) -> None:
        manifests = discover_template_manifests()

        self.assertIn("flask", manifests)
        self.assertEqual(manifests["flask"].language, "Python")
        self.assertIn("Flask", manifests["flask"].name)

    def test_discover_template_manifests_includes_custom_dir(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "custom"
            sample = root / "sample"
            sample.mkdir(parents=True)
            (sample / "template.toml").write_text(
                "[meta]\nname = \"Sample\"\ndescription = \"Custom template\"\nlanguage = \"Python\"\n",
                encoding="utf-8",
            )

            manifests = discover_template_manifests(root)

            self.assertIn("sample", manifests)
            self.assertEqual(manifests["sample"].description, "Custom template")


if __name__ == "__main__":
    unittest.main()
