from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main
import newsletter.digest as digest
from newsletter.renderers.markdown import render_markdown


FIXED_NOW = datetime(2026, 3, 26, 9, 30, 0)


def make_hn_item() -> dict:
    return {
        "source": "hacker_news",
        "title": "Example HN Story",
        "url": "https://example.com/hn",
        "rank": 1,
        "summary": "A short summary.",
        "meta": {
            "score": 123,
            "comments": 45,
            "hn_discussion_url": "https://news.ycombinator.com/item?id=1",
        },
    }


def make_trending_item() -> dict:
    return {
        "source": "github_trending",
        "title": "example/project",
        "url": "https://github.com/example/project",
        "rank": 1,
        "meta": {
            "repo_name": "example/project",
            "language": "Python",
            "stars_today": 42,
            "description": "Example repository.",
        },
    }


def make_x_author_items() -> dict[str, list[dict]]:
    return {
        "karpathy": [
            {
                "title": "@karpathy",
                "url": "https://x.com/karpathy/status/1",
                "summary": "A post from Karpathy.",
                "meta": {
                    "author_name": "Andrej Karpathy",
                    "username": "karpathy",
                    "created_at": "2026-03-26T09:00:00Z",
                    "like_count": 10,
                    "reply_count": 2,
                    "retweet_count": 3,
                    "quote_count": 1,
                },
            }
        ]
    }


class MainCLITest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        output_dir = Path(self.tempdir.name) / "daily"
        output_patch = patch.object(digest.config, "OUTPUT_DIR", str(output_dir))
        x_enabled_patch = patch.object(digest.config, "X_ENABLED", False)
        ai_enabled_patch = patch.object(digest.config, "AI_ENABLED", False)
        digest_now_patch = patch("newsletter.digest.get_now", return_value=FIXED_NOW)
        cli_now_patch = patch("newsletter.cli.get_now", return_value=FIXED_NOW)

        output_patch.start()
        x_enabled_patch.start()
        ai_enabled_patch.start()
        digest_now_patch.start()
        cli_now_patch.start()

        self.addCleanup(output_patch.stop)
        self.addCleanup(x_enabled_patch.stop)
        self.addCleanup(ai_enabled_patch.stop)
        self.addCleanup(digest_now_patch.stop)
        self.addCleanup(cli_now_patch.stop)

    def capture_cli(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main.main(argv)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def write_digest(
        self,
        *,
        hn_items: list[dict],
        trending_items: list[dict],
        x_items_by_author: dict[str, list[dict]] | None = None,
    ) -> Path:
        digest_path = digest.get_output_path(FIXED_NOW)
        digest_path.parent.mkdir(parents=True, exist_ok=True)
        digest_path.write_text(
            render_markdown(
                date_str="2026-03-26",
                hn_items=hn_items,
                trending_items=trending_items,
                x_items_by_author=x_items_by_author,
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

    def test_ai_filter_keeps_minimum_hn_items(self) -> None:
        hn_items = [
            {**make_hn_item(), "title": "HN Story One", "rank": 1},
            {**make_hn_item(), "title": "HN Story Two", "rank": 2},
            {**make_hn_item(), "title": "HN Story Three", "rank": 3},
        ]
        trending_items = [
            {
                **make_trending_item(),
                "title": "example/kept",
                "meta": {
                    **make_trending_item()["meta"],
                    "repo_name": "example/kept",
                },
            }
        ]

        def fake_score_and_summarize(items: list[dict]) -> tuple[list[dict], bool]:
            scored = []
            for item in items:
                scored_item = dict(item)
                scored_item["ai_score"] = 8.0 if item["source"] == "github_trending" else 4.0
                scored_item["ai_summary"] = item.get("summary", "")
                scored.append(scored_item)
            return scored, True

        with patch.object(digest.config, "AI_ENABLED", True), patch.object(
            digest.config,
            "HN_MIN_ITEMS_AFTER_AI",
            2,
        ), patch("newsletter.digest.fetch_hn", return_value=hn_items), patch(
            "newsletter.digest.fetch_github_trending",
            return_value=trending_items,
        ), patch(
            "newsletter.digest.score_and_summarize",
            side_effect=fake_score_and_summarize,
        ):
            exit_code, stdout, stderr = self.capture_cli(["generate"])

        content = digest.get_output_path(FIXED_NOW).read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("HN Story One", content)
        self.assertIn("HN Story Two", content)
        self.assertNotIn("HN Story Three", content)
        self.assertIn("example/kept", content)
        self.assertIn("Hacker News 2/3 kept", stdout)
        self.assertEqual(stderr, "")

    def test_ai_filter_keeps_minimum_github_trending_items(self) -> None:
        trending_items = [
            {
                **make_trending_item(),
                "title": "example/one",
                "rank": 1,
                "meta": {
                    **make_trending_item()["meta"],
                    "repo_name": "example/one",
                },
            },
            {
                **make_trending_item(),
                "title": "example/two",
                "rank": 2,
                "meta": {
                    **make_trending_item()["meta"],
                    "repo_name": "example/two",
                },
            },
            {
                **make_trending_item(),
                "title": "example/three",
                "rank": 3,
                "meta": {
                    **make_trending_item()["meta"],
                    "repo_name": "example/three",
                },
            },
        ]

        def fake_score_and_summarize(items: list[dict]) -> tuple[list[dict], bool]:
            scored = []
            for item in items:
                scored_item = dict(item)
                scored_item["ai_score"] = 4.0
                scored_item["ai_summary"] = item.get("summary", "")
                scored.append(scored_item)
            return scored, True

        with patch.object(digest.config, "AI_ENABLED", True), patch.object(
            digest.config,
            "HN_MIN_ITEMS_AFTER_AI",
            0,
        ), patch.object(
            digest.config,
            "GITHUB_TRENDING_MIN_ITEMS_AFTER_AI",
            2,
        ), patch("newsletter.digest.fetch_hn", return_value=[]), patch(
            "newsletter.digest.fetch_github_trending",
            return_value=trending_items,
        ), patch(
            "newsletter.digest.score_and_summarize",
            side_effect=fake_score_and_summarize,
        ):
            exit_code, stdout, stderr = self.capture_cli(["generate"])

        content = digest.get_output_path(FIXED_NOW).read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("example/one", content)
        self.assertIn("example/two", content)
        self.assertNotIn("example/three", content)
        self.assertIn("GitHub Trending 2/3 kept", stdout)
        self.assertEqual(stderr, "")

    def test_ai_filter_scores_sources_separately(self) -> None:
        hn_items = [{**make_hn_item(), "rank": 1}]
        trending_items = [{**make_trending_item(), "rank": 1}]

        def fake_score_and_summarize(items: list[dict]) -> tuple[list[dict], bool]:
            scored = []
            for item in items:
                scored_item = dict(item)
                scored_item["ai_score"] = 8.0
                scored_item["ai_summary"] = item.get("summary", "")
                scored.append(scored_item)
            return scored, True

        score_mock = MagicMock(side_effect=fake_score_and_summarize)

        with patch.object(digest.config, "AI_ENABLED", True), patch(
            "newsletter.digest.fetch_hn",
            return_value=hn_items,
        ), patch(
            "newsletter.digest.fetch_github_trending",
            return_value=trending_items,
        ), patch(
            "newsletter.digest.score_and_summarize",
            score_mock,
        ):
            exit_code, stdout, stderr = self.capture_cli(["generate"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(score_mock.call_count, 2)
        self.assertEqual(score_mock.call_args_list[0].args[0], hn_items)
        self.assertEqual(score_mock.call_args_list[1].args[0], trending_items)
        self.assertIn("AI scoring enabled, scoring Hacker News 1 items", stdout)
        self.assertIn("AI scoring enabled, scoring GitHub Trending 1 items", stdout)
        self.assertEqual(stderr, "")

    def test_ai_all_failed_skips_filter(self) -> None:
        hn_items = [
            {**make_hn_item(), "title": "HN Story One", "rank": 1},
            {**make_hn_item(), "title": "HN Story Two", "rank": 2},
            {**make_hn_item(), "title": "HN Story Three", "rank": 3},
        ]
        trending_items = [
            {
                **make_trending_item(),
                "title": "example/one",
                "rank": 1,
                "meta": {
                    **make_trending_item()["meta"],
                    "repo_name": "example/one",
                },
            },
        ]

        def fake_score_and_summarize(items: list[dict]) -> tuple[list[dict], bool]:
            scored = []
            for item in items:
                scored_item = dict(item)
                scored_item["ai_score"] = 5.0
                scored_item["ai_summary"] = item.get("summary", "")
                scored.append(scored_item)
            return scored, False

        with patch.object(digest.config, "AI_ENABLED", True), patch(
            "newsletter.digest.fetch_hn",
            return_value=hn_items,
        ), patch(
            "newsletter.digest.fetch_github_trending",
            return_value=trending_items,
        ), patch(
            "newsletter.digest.score_and_summarize",
            side_effect=fake_score_and_summarize,
        ):
            exit_code, stdout, stderr = self.capture_cli(["generate"])

        content = digest.get_output_path(FIXED_NOW).read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        # All items should be kept when AI fails
        self.assertIn("HN Story One", content)
        self.assertIn("HN Story Two", content)
        self.assertIn("HN Story Three", content)
        self.assertIn("example/one", content)
        self.assertIn("skipping filter", stdout)
        self.assertEqual(stderr, "")

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
        self.assertIn("All enabled sources failed; newsletter was not generated", stderr)

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

    def test_generate_writes_x_author_section_when_enabled(self) -> None:
        with patch.object(digest.config, "X_ENABLED", True), patch(
            "newsletter.digest.fetch_hn",
            return_value=[make_hn_item()],
        ), patch(
            "newsletter.digest.fetch_github_trending",
            return_value=[make_trending_item()],
        ), patch(
            "newsletter.digest.fetch_x_posts",
            return_value=make_x_author_items(),
        ):
            exit_code, stdout, stderr = self.capture_cli(["generate"])

        digest_path = digest.get_output_path(FIXED_NOW)
        content = digest_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("## X Posts", content)
        self.assertIn("### Andrej Karpathy (@karpathy)", content)
        self.assertIn("Fetched 1 X author posts", stdout)
        self.assertEqual(stderr, "")

    def test_status_reports_partial_when_x_enabled_but_empty(self) -> None:
        with patch.object(digest.config, "X_ENABLED", True):
            self.write_digest(
                hn_items=[make_hn_item()],
                trending_items=[make_trending_item()],
                x_items_by_author={},
            )

            exit_code, stdout, stderr = self.capture_cli(["status"])

        self.assertEqual(exit_code, 0)
        self.assertIn("status: partial", stdout)
        self.assertIn("X Posts", stdout)
        self.assertEqual(stderr, "")

    def test_render_markdown_places_x_section_first(self) -> None:
        content = render_markdown(
            date_str="2026-03-26",
            hn_items=[make_hn_item()],
            trending_items=[make_trending_item()],
            generated_at="2026-03-26 09:30:00",
            x_items_by_author=make_x_author_items(),
        )

        self.assertLess(content.index("## X Posts"), content.index("## GitHub Trending"))
        self.assertLess(content.index("## GitHub Trending"), content.index("## Hacker News"))

    def test_render_markdown_renders_empty_x_section(self) -> None:
        content = render_markdown(
            date_str="2026-03-26",
            hn_items=[make_hn_item()],
            trending_items=[make_trending_item()],
            generated_at="2026-03-26 09:30:00",
            x_items_by_author={},
        )

        self.assertIn("## X Posts", content)
        self.assertIn("No items fetched.", content)

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
