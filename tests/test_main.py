from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main
import newsletter.digest as digest
from newsletter.renderers.markdown import render_markdown


FIXED_NOW = datetime(2026, 3, 26, 9, 30, 0)


def make_hn_item() -> dict:
    return {
        "title": "Example HN Story",
        "url": "https://example.com/hn",
        "summary": "A short summary.",
        "meta": {
            "score": 123,
            "comments": 45,
            "hn_discussion_url": "https://news.ycombinator.com/item?id=1",
        },
    }


def make_trending_item() -> dict:
    return {
        "title": "example/project",
        "url": "https://github.com/example/project",
        "meta": {
            "repo_name": "example/project",
            "language": "Python",
            "stars_today": 42,
            "description": "Example repository.",
        },
    }


class MainCLITest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        output_dir = Path(self.tempdir.name) / "daily"
        output_patch = patch.object(digest.config, "OUTPUT_DIR", str(output_dir))
        digest_now_patch = patch("newsletter.digest.get_now", return_value=FIXED_NOW)
        cli_now_patch = patch("newsletter.cli.get_now", return_value=FIXED_NOW)

        output_patch.start()
        digest_now_patch.start()
        cli_now_patch.start()

        self.addCleanup(output_patch.stop)
        self.addCleanup(digest_now_patch.stop)
        self.addCleanup(cli_now_patch.stop)

    def capture_cli(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main.main(argv)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def write_digest(self, *, hn_items: list[dict], trending_items: list[dict]) -> Path:
        digest_path = digest.get_output_path(FIXED_NOW)
        digest_path.parent.mkdir(parents=True, exist_ok=True)
        digest_path.write_text(
            render_markdown(
                date_str="2026-03-26",
                hn_items=hn_items,
                trending_items=trending_items,
                generated_at="2026-03-26 09:30:00",
            ),
            encoding="utf-8",
        )
        return digest_path

    def test_no_args_prints_help(self) -> None:
        exit_code, stdout, stderr = self.capture_cli([])

        self.assertEqual(exit_code, 0)
        self.assertIn("usage:", stdout)
        self.assertIn("generate", stdout)
        self.assertIn("status", stdout)
        self.assertIn("show", stdout)
        self.assertEqual(stderr, "")

    def test_version_prints_cli_version(self) -> None:
        exit_code, stdout, stderr = self.capture_cli(["--version"])

        self.assertEqual(exit_code, 0)
        self.assertIn("newsletter 0.1.0", stdout)
        self.assertEqual(stderr, "")

    def test_generate_writes_digest(self) -> None:
        with patch("newsletter.digest.fetch_hn", return_value=[make_hn_item()]), patch(
            "newsletter.digest.fetch_github_trending",
            return_value=[make_trending_item()],
        ):
            exit_code, stdout, stderr = self.capture_cli(["generate"])

        digest_path = digest.get_output_path(FIXED_NOW)

        self.assertEqual(exit_code, 0)
        self.assertTrue(digest_path.exists())
        content = digest_path.read_text(encoding="utf-8")
        self.assertIn("# Newsletter - 2026-03-26", content)
        self.assertIn("## GitHub Trending", content)
        self.assertIn("## Hacker News", content)
        self.assertIn(f"Wrote newsletter to {digest_path}", stdout)
        self.assertEqual(stderr, "")

    def test_generate_allows_partial_output(self) -> None:
        with patch("newsletter.digest.fetch_hn", side_effect=RuntimeError("HN unavailable")), patch(
            "newsletter.digest.fetch_github_trending",
            return_value=[make_trending_item()],
        ):
            exit_code, stdout, stderr = self.capture_cli(["generate"])

        digest_path = digest.get_output_path(FIXED_NOW)

        self.assertEqual(exit_code, 0)
        self.assertTrue(digest_path.exists())
        self.assertIn(f"Wrote newsletter to {digest_path}", stdout)
        self.assertIn("Hacker News fetch failed: HN unavailable", stderr)
        self.assertIn("No items fetched.", digest_path.read_text(encoding="utf-8"))

    def test_generate_fails_when_both_sources_fail(self) -> None:
        with patch("newsletter.digest.fetch_hn", side_effect=RuntimeError("HN unavailable")), patch(
            "newsletter.digest.fetch_github_trending",
            side_effect=RuntimeError("GitHub unavailable"),
        ):
            exit_code, stdout, stderr = self.capture_cli(["generate"])

        self.assertEqual(exit_code, 1)
        self.assertFalse(digest.get_output_path(FIXED_NOW).exists())
        self.assertIn("Fetching Hacker News items", stdout)
        self.assertIn("Fetching GitHub Trending items", stdout)
        self.assertIn("Both sources failed; newsletter was not generated", stderr)

    def test_status_reports_success(self) -> None:
        digest_path = self.write_digest(
            hn_items=[make_hn_item()],
            trending_items=[make_trending_item()],
        )

        exit_code, stdout, stderr = self.capture_cli(["status"])

        self.assertEqual(exit_code, 0)
        self.assertIn("status: success", stdout)
        self.assertIn(f"path: {digest_path}", stdout)
        self.assertEqual(stderr, "")

    def test_status_reports_partial(self) -> None:
        self.write_digest(hn_items=[], trending_items=[make_trending_item()])

        exit_code, stdout, stderr = self.capture_cli(["status"])

        self.assertEqual(exit_code, 0)
        self.assertIn("status: partial", stdout)
        self.assertIn("Hacker News", stdout)
        self.assertEqual(stderr, "")

    def test_status_reports_missing(self) -> None:
        exit_code, stdout, stderr = self.capture_cli(["status"])

        self.assertEqual(exit_code, 1)
        self.assertIn("status: missing", stdout)
        self.assertEqual(stderr, "")

    def test_status_reports_invalid(self) -> None:
        digest_path = digest.get_output_path(FIXED_NOW)
        digest_path.parent.mkdir(parents=True, exist_ok=True)
        digest_path.write_text("# Wrong File\n", encoding="utf-8")

        exit_code, stdout, stderr = self.capture_cli(["status"])

        self.assertEqual(exit_code, 1)
        self.assertIn("status: invalid", stdout)
        self.assertIn("# Newsletter - 2026-03-26", stdout)
        self.assertEqual(stderr, "")

    def test_show_prints_digest(self) -> None:
        self.write_digest(
            hn_items=[make_hn_item()],
            trending_items=[make_trending_item()],
        )

        exit_code, stdout, stderr = self.capture_cli(["show"])

        self.assertEqual(exit_code, 0)
        self.assertIn("# Newsletter - 2026-03-26", stdout)
        self.assertEqual(stderr, "")

    def test_show_fails_when_digest_missing(self) -> None:
        exit_code, stdout, stderr = self.capture_cli(["show"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Newsletter file does not exist", stderr)
