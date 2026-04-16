from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import requests

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from newsletter import config
from newsletter.fetchers.x_posts import (
    _build_x_session,
    _extract_entities,
    _load_cookies,
    _normalize_post,
    _parse_cookies,
    fetch_x_posts,
)


FIXED_NOW = datetime(2026, 4, 14, 12, 0, 0, tzinfo=UTC)


def make_payload(
    *,
    username: str = "karpathy",
    display_name: str = "Andrej Karpathy",
    tweet_ids: list[str] | None = None,
    tweet_overrides: dict[str, dict] | None = None,
    user_id: str = "42",
) -> dict:
    tweet_ids = tweet_ids or ["1"]
    tweet_overrides = tweet_overrides or {}

    instructions = []
    for tweet_id in tweet_ids:
        base_tweet = {
            "__typename": "Tweet",
            "rest_id": tweet_id,
            "legacy": {
                "created_at": email_date(hours_ago=int(tweet_id)),
                "full_text": f"tweet-{tweet_id}",
                "favorite_count": 10,
                "reply_count": 2,
                "retweet_count": 3,
                "quote_count": 1,
                "user_id_str": user_id,
                "id_str": tweet_id,
                "in_reply_to_status_id_str": None,
                "retweeted_status_id_str": None,
                "quoted_status_id_str": None,
            },
        }
        override = tweet_overrides.get(tweet_id, {})
        merged = deep_merge(base_tweet, override)
        instructions.append({"entryId": f"tweet-{tweet_id}", "content": {"itemContent": {"tweet_results": {"result": merged}}}})

    return {
        "data": {
            "search_by_raw_query": {
                "search_timeline": {
                    "timeline": {
                        "instructions": instructions,
                    }
                }
            },
            "user": {
                "result": {
                    "__typename": "User",
                    "rest_id": user_id,
                    "id": user_id,
                    "legacy": {
                        "name": display_name,
                        "screen_name": username,
                    },
                }
            },
        }
    }


def deep_merge(base: dict, override: dict) -> dict:
    result = {**base}
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def email_date(*, hours_ago: int) -> str:
    dt = FIXED_NOW - timedelta(hours=hours_ago)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


class XPostsFetcherTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        self.cookies_path = Path(self.tempdir.name) / "cookies.json"
        self.cookies_path.write_text(
            '{"auth_token":"token","ct0":"csrf","twid":"u%3D123"}',
            encoding="utf-8",
        )

        self.cookies_patch = patch.object(config, "X_COOKIES_PATH", str(self.cookies_path))
        self.cookies_env_patch = patch.object(config, "X_COOKIES", None)
        self.enabled_patch = patch.object(config, "X_ENABLED", True)
        self.authors_patch = patch.object(config, "X_AUTHORS", ("karpathy", "sama"))
        self.operation_patch = patch.object(config, "X_USER_TWEETS_OPERATION", None)
        self.author_ids_patch = patch.object(
            config,
            "get_x_author_ids",
            return_value={"karpathy": "42", "sama": "43"},
        )

        self.cookies_patch.start()
        self.cookies_env_patch.start()
        self.enabled_patch.start()
        self.authors_patch.start()
        self.operation_patch.start()
        self.author_ids_patch.start()

        self.addCleanup(self.cookies_patch.stop)
        self.addCleanup(self.cookies_env_patch.stop)
        self.addCleanup(self.enabled_patch.stop)
        self.addCleanup(self.authors_patch.stop)
        self.addCleanup(self.operation_patch.stop)
        self.addCleanup(self.author_ids_patch.stop)

    def test_parse_cookies_accepts_object_list_and_header(self) -> None:
        self.assertEqual(
            _parse_cookies('{"auth_token":"a","ct0":"b"}'),
            {"auth_token": "a", "ct0": "b"},
        )
        self.assertEqual(
            _parse_cookies('[{"name":"auth_token","value":"a"},{"name":"ct0","value":"b"}]'),
            {"auth_token": "a", "ct0": "b"},
        )
        self.assertEqual(
            _parse_cookies("auth_token=a; ct0=b"),
            {"auth_token": "a", "ct0": "b"},
        )

    def test_load_cookies_requires_auth_token_and_ct0(self) -> None:
        self.cookies_path.write_text('{"ct0":"only"}', encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "missing required cookies: auth_token"):
            _load_cookies()

    def test_load_cookies_uses_x_cookies_env_first(self) -> None:
        missing_path = Path(self.tempdir.name) / "missing.json"
        with patch.object(config, "X_COOKIES", "auth_token=envtoken; ct0=envcsrf"), patch.object(
            config,
            "X_COOKIES_PATH",
            str(missing_path),
        ):
            cookies = _load_cookies()

        self.assertEqual(cookies["auth_token"], "envtoken")
        self.assertEqual(cookies["ct0"], "envcsrf")

    def test_build_x_session_sets_required_headers(self) -> None:
        session = _build_x_session({"auth_token": "token", "ct0": "csrf"})
        self.assertEqual(session.headers["x-csrf-token"], "csrf")
        self.assertIn("Bearer", session.headers["Authorization"])
        self.assertEqual(session.cookies.get("auth_token"), "token")

    def test_extract_entities_finds_tweets_and_users(self) -> None:
        payload = make_payload(tweet_ids=["1", "2"])
        tweets, users = _extract_entities(payload)
        self.assertEqual(set(tweets.keys()), {"1", "2"})
        self.assertEqual(set(users.keys()), {"42"})

    def test_normalize_post_filters_replies_reposts_quotes_and_old_posts(self) -> None:
        payload = make_payload()
        tweets, users = _extract_entities(payload)
        self.assertIsNotNone(_normalize_post(tweets["1"], users, "karpathy", FIXED_NOW))
        self.assertIsNone(
            _normalize_post(
                tweets["1"],
                users,
                "karpathy",
                FIXED_NOW,
                expected_user_id="999",
            )
        )

        reply_payload = make_payload(
            tweet_overrides={"1": {"legacy": {"in_reply_to_status_id_str": "99"}}}
        )
        tweets, users = _extract_entities(reply_payload)
        self.assertIsNone(_normalize_post(tweets["1"], users, "karpathy", FIXED_NOW))

        retweet_payload = make_payload(
            tweet_overrides={"1": {"legacy": {"retweeted_status_id_str": "99"}}}
        )
        tweets, users = _extract_entities(retweet_payload)
        self.assertIsNone(_normalize_post(tweets["1"], users, "karpathy", FIXED_NOW))

        quote_payload = make_payload(
            tweet_overrides={"1": {"legacy": {"quoted_status_id_str": "99"}}}
        )
        tweets, users = _extract_entities(quote_payload)
        self.assertIsNone(_normalize_post(tweets["1"], users, "karpathy", FIXED_NOW))

        old_payload = make_payload(
            tweet_overrides={
                "1": {
                    "legacy": {
                        "created_at": email_date(hours_ago=config.X_LOOKBACK_HOURS + 1)
                    }
                }
            }
        )
        tweets, users = _extract_entities(old_payload)
        self.assertIsNone(_normalize_post(tweets["1"], users, "karpathy", FIXED_NOW))

    def test_fetch_x_posts_groups_filters_and_truncates(self) -> None:
        payloads = {
            "karpathy": make_payload(tweet_ids=["1", "2", "3", "4"]),
            "sama": make_payload(username="sama", display_name="Sam Altman", tweet_ids=["1"], user_id="43"),
        }

        with patch(
            "newsletter.fetchers.x_posts._fetch_user_tweets_payload",
            side_effect=lambda session, username, user_id: payloads[username],
        ):
            items = fetch_x_posts(FIXED_NOW)

        self.assertEqual(list(items.keys()), ["karpathy", "sama"])
        self.assertEqual(len(items["karpathy"]), 3)
        self.assertEqual(items["karpathy"][0]["summary"], "tweet-1")
        self.assertEqual(items["sama"][0]["meta"]["author_name"], "Sam Altman")

    def test_fetch_x_posts_continues_when_one_author_fails(self) -> None:
        payloads = {
            "karpathy": make_payload(),
        }

        def fake_fetch(session, username, user_id):
            del user_id
            if username == "sama":
                raise RuntimeError("boom")
            return payloads[username]

        with patch("newsletter.fetchers.x_posts._fetch_user_tweets_payload", side_effect=fake_fetch):
            items = fetch_x_posts(FIXED_NOW)

        self.assertEqual(list(items.keys()), ["karpathy"])

    def test_fetch_x_posts_returns_empty_when_no_usable_posts(self) -> None:
        payloads = {
            "karpathy": make_payload(
                tweet_overrides={
                    "1": {
                        "legacy": {
                            "created_at": email_date(hours_ago=config.X_LOOKBACK_HOURS + 1)
                        }
                    }
                }
            ),
            "sama": make_payload(username="sama", display_name="Sam Altman", tweet_overrides={"1": {"legacy": {"quoted_status_id_str": "99"}}}),
        }

        with patch(
            "newsletter.fetchers.x_posts._fetch_user_tweets_payload",
            side_effect=lambda session, username, user_id: payloads[username],
        ):
            items = fetch_x_posts(FIXED_NOW)

        self.assertEqual(items, {})

    def test_fetch_x_posts_handles_request_timeout(self) -> None:
        def fake_fetch(session, username, user_id):
            del session, username, user_id
            raise requests.Timeout("slow")

        with patch("newsletter.fetchers.x_posts._fetch_user_tweets_payload", side_effect=fake_fetch):
            with self.assertRaisesRegex(RuntimeError, "No valid X author posts fetched"):
                fetch_x_posts(FIXED_NOW)

    def test_fetch_user_tweets_payload_uses_configured_operation_and_surfaces_stale_id(self) -> None:
        class FakeResponse:
            status_code = 404

            def raise_for_status(self) -> None:
                raise requests.HTTPError("404")

        class FakeSession:
            def __init__(self) -> None:
                self.url = ""

            def get(self, url, params=None, timeout=None):
                del params, timeout
                self.url = url
                return FakeResponse()

        from newsletter.fetchers.x_posts import _fetch_user_tweets_payload

        session = FakeSession()
        with patch.object(config, "X_USER_TWEETS_OPERATION", "custom/UserTweets"):
            with self.assertRaisesRegex(RuntimeError, "operation id is stale"):
                _fetch_user_tweets_payload(session, "karpathy", "42")

        self.assertEqual(session.url, "https://x.com/i/api/graphql/custom/UserTweets")

    def test_fetch_x_posts_requires_author_ids(self) -> None:
        with patch.object(config, "get_x_author_ids", return_value={}):
            with self.assertRaisesRegex(RuntimeError, "Missing userId for configured X Posts"):
                fetch_x_posts(FIXED_NOW)

    def test_fetch_x_posts_supports_single_author_probe(self) -> None:
        payloads = {
            "karpathy": make_payload(),
        }

        with patch.object(config, "get_x_author_ids", return_value={"karpathy": "42"}), patch(
            "newsletter.fetchers.x_posts._fetch_user_tweets_payload",
            side_effect=lambda session, username, user_id: payloads[username],
        ):
            items = fetch_x_posts(FIXED_NOW)

        self.assertEqual(list(items.keys()), ["karpathy"])
