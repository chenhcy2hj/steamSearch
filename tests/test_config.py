from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from app.core.config import load_settings


class ConfigTest(unittest.TestCase):
    def test_steamdt_environment_overrides_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                """
                [steamdt]
                api_key = "file-key"
                base_url = "https://example.test"
                """,
                encoding="utf-8",
            )
            old_key = os.environ.get("STEAMDT_API_KEY")
            old_base_url = os.environ.get("STEAMDT_BASE_URL")
            os.environ["STEAMDT_API_KEY"] = "env-key"
            os.environ["STEAMDT_BASE_URL"] = "https://env.example"
            try:
                settings, _ = load_settings(config_path)
            finally:
                _restore_env("STEAMDT_API_KEY", old_key)
                _restore_env("STEAMDT_BASE_URL", old_base_url)

        self.assertEqual(settings.steamdt.api_key, "env-key")
        self.assertEqual(settings.steamdt.base_url, "https://env.example")

    def test_buff_environment_enables_cookie(self) -> None:
        old_enabled = os.environ.get("BUFF_ENABLED")
        old_cookie = os.environ.get("BUFF_COOKIE")
        os.environ["BUFF_ENABLED"] = "true"
        os.environ["BUFF_COOKIE"] = "buff-cookie"
        try:
            settings, _ = load_settings(Path("/tmp/missing-steamsearch-config.toml"))
        finally:
            _restore_env("BUFF_ENABLED", old_enabled)
            _restore_env("BUFF_COOKIE", old_cookie)

        self.assertTrue(settings.buff.enabled)
        self.assertEqual(settings.buff.cookie, "buff-cookie")


def _restore_env(key: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
