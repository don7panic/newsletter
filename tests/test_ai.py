from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from newsletter.ai.client import score_and_summarize


def make_item(source: str = "hacker_news", **overrides: object) -> dict:
    item: dict = {
        "source": source,
        "title": "Test Item",
        "url": "https://example.com/test",
        "rank": 1,
        "summary": "Original summary text.",
        "fetched_at": "2026-05-06 12:00:00",
        "meta": {},
    }
    item.update(overrides)
    return item


class ScoreAndSummarizeTest(unittest.TestCase):
    """Unit tests for the AI scoring & summarization client."""

    def test_empty_items(self) -> None:
        self.assertEqual(score_and_summarize([]), [])

    @patch("newsletter.ai.client.OpenAI")
    def test_successful_scoring(self, mock_openai: MagicMock) -> None:
        fake_response = MagicMock()
        fake_response.choices = [
            MagicMock(message=MagicMock(
                content='{"score": 8, "reason": "Interesting project", "summary": "A great new tool."}'
            ))
        ]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = fake_response
        mock_openai.return_value = mock_client

        items = [make_item(summary="some repo description")]
        result = score_and_summarize(items)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["ai_score"], 8.0)
        self.assertEqual(result[0]["ai_summary"], "A great new tool.")

    @patch("newsletter.ai.client.OpenAI")
    def test_fallback_on_api_failure(self, mock_openai: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API timeout")
        mock_openai.return_value = mock_client

        items = [make_item(summary="fallback summary")]
        result = score_and_summarize(items)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["ai_score"], 5.0)
        self.assertEqual(result[0]["ai_summary"], "fallback summary")

    @patch("newsletter.ai.client.OpenAI")
    def test_fallback_on_invalid_json(self, mock_openai: MagicMock) -> None:
        fake_response = MagicMock()
        fake_response.choices = [
            MagicMock(message=MagicMock(content="not json at all"))
        ]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = fake_response
        mock_openai.return_value = mock_client

        items = [make_item(summary="invalid json fallback")]
        result = score_and_summarize(items)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["ai_score"], 5.0)
        self.assertEqual(result[0]["ai_summary"], "invalid json fallback")

    @patch("newsletter.ai.client.OpenAI")
    def test_partial_failure_does_not_affect_siblings(self, mock_openai: MagicMock) -> None:
        call_count = 0

        def side_effect(**kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("first item fails")
            fake = MagicMock()
            fake.choices = [
                MagicMock(message=MagicMock(
                    content='{"score": 9, "reason": "Great", "summary": "Second item summary."}'
                ))
            ]
            return fake

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = side_effect
        mock_openai.return_value = mock_client

        items = [
            make_item(title="First", summary="first summary"),
            make_item(title="Second", summary="second summary"),
        ]
        result = score_and_summarize(items)

        self.assertEqual(len(result), 2)
        # First item: fallback
        self.assertEqual(result[0]["ai_score"], 5.0)
        self.assertEqual(result[0]["ai_summary"], "first summary")
        # Second item: success
        self.assertEqual(result[1]["ai_score"], 9.0)
        self.assertEqual(result[1]["ai_summary"], "Second item summary.")

    @patch("newsletter.ai.client.OpenAI")
    def test_github_trending_item_scored(self, mock_openai: MagicMock) -> None:
        fake_response = MagicMock()
        fake_response.choices = [
            MagicMock(message=MagicMock(
                content='{"score": 7, "reason": "Popular repo", "summary": "A trending project."}'
            ))
        ]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = fake_response
        mock_openai.return_value = mock_client

        items = [make_item(
            source="github_trending",
            title="owner/repo",
            summary="Some repo.",
            meta={"language": "Python", "stars_today": 100},
        )]
        result = score_and_summarize(items)

        self.assertEqual(result[0]["ai_score"], 7.0)
        self.assertEqual(result[0]["ai_summary"], "A trending project.")