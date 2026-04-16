from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from newsletter import config


class ConfigTest(unittest.TestCase):
    def test_parse_dotenv_line(self) -> None:
        self.assertEqual(config._parse_dotenv_line("X_COOKIES=auth_token=a; ct0=b"), ("X_COOKIES", "auth_token=a; ct0=b"))
        self.assertEqual(config._parse_dotenv_line("export FOO='bar'"), ("FOO", "bar"))
        self.assertEqual(config._parse_dotenv_line("FOO=bar # comment"), ("FOO", "bar"))
        self.assertIsNone(config._parse_dotenv_line("# only comment"))

    def test_load_dotenv_file_sets_defaults_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {"X_COOKIES": "existing"}, clear=False):
            dotenv_path = Path(tmpdir) / ".env"
            dotenv_path.write_text("X_COOKIES=from_file\nX_WEB_BEARER_TOKEN=from_file\n", encoding="utf-8")
            config._load_dotenv_file(dotenv_path)
            self.assertEqual(os.environ["X_COOKIES"], "existing")
            self.assertEqual(os.environ["X_WEB_BEARER_TOKEN"], "from_file")

    def test_is_x_enabled_when_x_cookies_present(self) -> None:
        with patch.object(config, "X_COOKIES", "auth_token=token; ct0=csrf"), patch.object(
            config,
            "X_COOKIES_PATH",
            "",
        ):
            self.assertTrue(config.is_x_enabled())

