import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from repox.config import config_path, custom_template_dir, load_config, render_toml, reset_config, save_config


class ConfigTests(unittest.TestCase):
    def test_load_config_creates_default_file(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "repox.toml"
            config = load_config(path)

            self.assertTrue(path.exists())
            self.assertEqual(config["defaults"]["visibility"], "private")
            self.assertEqual(config["defaults"]["remote"], "origin")

    def test_save_and_load_round_trip(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "repox.toml"
            config = load_config(path)
            config["defaults"]["template"] = "flask"
            config["templates"]["custom_dir"] = "~/templates"
            save_config(config, path)

            loaded = load_config(path)
            self.assertEqual(loaded["defaults"]["template"], "flask")
            self.assertEqual(loaded["templates"]["custom_dir"], "~/templates")

    def test_reset_config_restores_defaults(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "repox.toml"
            save_config(
                {
                    "defaults": {"visibility": "public", "template": "react", "remote": "upstream"},
                    "templates": {"custom_dir": "/tmp/templates"},
                },
                path,
            )

            reset = reset_config(path)
            self.assertEqual(reset["defaults"]["visibility"], "private")
            self.assertEqual(reset["templates"]["custom_dir"], "")

    def test_custom_template_dir_expands_user_path(self) -> None:
        config = {
            "defaults": {"visibility": "private", "template": "none", "remote": "origin"},
            "templates": {"custom_dir": "~/custom-templates"},
        }
        self.assertTrue(str(custom_template_dir(config)).endswith("custom-templates"))

    def test_render_toml_contains_sections(self) -> None:
        text = render_toml(
            {
                "defaults": {"visibility": "private", "template": "none", "remote": "origin"},
                "templates": {"custom_dir": ""},
            }
        )
        self.assertIn("[defaults]", text)
        self.assertIn('[templates]', text)


if __name__ == "__main__":
    unittest.main()
