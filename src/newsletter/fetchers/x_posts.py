from __future__ import annotations

import email.utils
import json
import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from newsletter import config


LOGGER = logging.getLogger(__name__)
TRANSIENT_NETWORK_ERRORS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
    requests.exceptions.SSLError,
)
X_WEB_BEARER_TOKEN = (
    "Bearer "
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D"
    "1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)
X_GQL_URL = "https://x.com/i/api/graphql"
DEFAULT_X_USER_TWEETS_OPERATION = "x3B_xLqC0yZawOB7WQhaVQ/UserTweets"
X_USER_TWEETS_FEATURES = {
    # Keep this payload intentionally small. In some environments a large
    # features query triggers TLS EOF/connection resets for this endpoint.
    "rweb_video_screen_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
}
DEFAULT_AUTHOR_NAMES = {
    "karpathy": "Andrej Karpathy",
    "sama": "Sam Altman",
    "swyxl": "Swyx",
    "joshwoodward": "Josh Woodward",
    "mattturck": "Matt Turck",
    "trq212": "Thariq",
}


def _now_string(now: datetime | None = None) -> str:
    current_time = now or datetime.now()
    return current_time.strftime("%Y-%m-%d %H:%M:%S")


def _normalize_text(text: object) -> str:
    if not isinstance(text, str):
        return ""
    return " ".join(text.split())


def _is_retweet_text(text: object) -> bool:
    normalized = _normalize_text(text)
    return normalized.startswith("RT @")


def _coerce_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value:
        try:
            return email.utils.parsedate_to_datetime(value).astimezone(UTC)
        except (TypeError, ValueError):
            candidate = value.replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(candidate)
            except ValueError:
                return None
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None


def _get_by_path(obj: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = obj
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _encode_params(obj: dict[str, Any]) -> dict[str, str]:
    encoded: dict[str, str] = {}
    for key, value in obj.items():
        if isinstance(value, dict):
            encoded[key] = json.dumps(value, separators=(",", ":"))
        else:
            encoded[key] = str(value)
    return encoded


def _parse_cookies(raw_value: str) -> dict[str, str]:
    try:
        loaded = json.loads(raw_value)
    except json.JSONDecodeError:
        loaded = None

    if isinstance(loaded, dict):
        cookies = loaded.get("cookies", loaded)
        if isinstance(cookies, dict):
            return {str(key): str(value) for key, value in cookies.items()}

    if isinstance(loaded, list):
        result: dict[str, str] = {}
        for item in loaded:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            value = item.get("value")
            if isinstance(name, str) and isinstance(value, str):
                result[name] = value
        if result:
            return result

    result = {}
    for chunk in raw_value.split(";"):
        part = chunk.strip()
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        result[key] = value
    if result:
        return result

    raise RuntimeError(
        "X cookies could not be parsed. Use a JSON object, cookie list, or raw cookie header."
    )


def _resolve_cookies_path() -> Path:
    cookies_path = config.resolve_x_cookies_path()
    if cookies_path is None:
        raise RuntimeError(
            "X cookies are not configured. Set X_COOKIES in .env or X_COOKIES_PATH."
        )
    if not cookies_path.is_file():
        raise RuntimeError(f"X cookies file does not exist: {cookies_path}")
    return cookies_path


def _validate_required_cookies(cookies: dict[str, str], source_label: str) -> dict[str, str]:
    missing = [key for key in ("auth_token", "ct0") if key not in cookies]
    if missing:
        raise RuntimeError(
            f"{source_label} is missing required cookies: " + ", ".join(missing)
        )
    return cookies


def _load_cookies() -> dict[str, str]:
    raw_cookies = (config.X_COOKIES or "").strip()
    if raw_cookies:
        return _validate_required_cookies(
            _parse_cookies(raw_cookies),
            "X_COOKIES",
        )

    cookies_path = _resolve_cookies_path()
    raw_value = cookies_path.read_text(encoding="utf-8").strip()
    if not raw_value:
        raise RuntimeError(f"X cookies file is empty: {cookies_path}")

    return _validate_required_cookies(
        _parse_cookies(raw_value),
        f"X cookies file ({cookies_path})",
    )


def _build_x_session(cookies: dict[str, str]) -> requests.Session:
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Authorization": config.X_WEB_BEARER_TOKEN or X_WEB_BEARER_TOKEN,
            "x-csrf-token": cookies["ct0"],
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "en",
            "Referer": "https://x.com/",
            "Origin": "https://x.com",
        }
    )
    if config.X_CLIENT_TRANSACTION_ID:
        session.headers["x-client-transaction-id"] = config.X_CLIENT_TRANSACTION_ID
    return session


def _collect_entities(node: Any, *, tweets: dict[str, dict], users: dict[str, dict]) -> None:
    if isinstance(node, dict):
        typename = node.get("__typename")
        rest_id = node.get("rest_id")
        legacy = node.get("legacy")

        if typename == "Tweet" and isinstance(rest_id, str) and isinstance(legacy, dict):
            tweets[rest_id] = node
        elif typename == "TweetWithVisibilityResults":
            tweet_node = node.get("tweet")
            if isinstance(tweet_node, dict):
                _collect_entities(tweet_node, tweets=tweets, users=users)
        elif typename == "User" and isinstance(rest_id, str) and isinstance(legacy, dict):
            users[rest_id] = node

        for value in node.values():
            _collect_entities(value, tweets=tweets, users=users)
        return

    if isinstance(node, list):
        for item in node:
            _collect_entities(item, tweets=tweets, users=users)


def _extract_entities(payload: dict[str, Any]) -> tuple[dict[str, dict], dict[str, dict]]:
    tweets: dict[str, dict] = {}
    users: dict[str, dict] = {}
    _collect_entities(payload, tweets=tweets, users=users)
    return tweets, users


def _is_original_post(tweet: dict[str, Any]) -> bool:
    legacy = tweet.get("legacy", {})
    note_text = _get_by_path(tweet, "note_tweet.note_tweet_results.result.text", "")
    full_text = legacy.get("full_text", "")
    return not any(
        (
            legacy.get("retweeted_status_id_str"),
            _get_by_path(tweet, "retweeted_status_result.result.rest_id"),
            _get_by_path(tweet, "retweeted_status_result.result.tweet.rest_id"),
            _is_retweet_text(note_text),
            _is_retweet_text(full_text),
            legacy.get("quoted_status_id_str"),
            _get_by_path(tweet, "quoted_status_result.result.rest_id"),
            _get_by_path(tweet, "quoted_status_result.result.tweet.rest_id"),
            legacy.get("in_reply_to_status_id_str"),
        )
    )


def _get_author_name(user: dict[str, Any] | None, username: str) -> str:
    if user is not None:
        legacy = user.get("legacy", {})
        name = legacy.get("name")
        if isinstance(name, str) and name.strip():
            return name
    return DEFAULT_AUTHOR_NAMES.get(username, f"@{username}")


def _normalize_post(
    tweet: dict[str, Any],
    users: dict[str, dict],
    username: str,
    now: datetime,
    expected_user_id: str | None = None,
) -> dict | None:
    legacy = tweet.get("legacy", {})
    created_at = _coerce_datetime(legacy.get("created_at"))
    if created_at is None:
        return None

    if created_at < now - timedelta(hours=config.X_LOOKBACK_HOURS):
        return None

    if not _is_original_post(tweet):
        return None

    post_id = tweet.get("rest_id")
    if not isinstance(post_id, str):
        return None

    user_id = legacy.get("user_id_str")
    if expected_user_id is not None and str(user_id) != str(expected_user_id):
        return None
    user = users.get(str(user_id)) if user_id is not None else None
    actual_username = _get_by_path(user or {}, "legacy.screen_name")
    if isinstance(actual_username, str) and actual_username.lower() != username.lower():
        return None

    text = _normalize_text(
        _get_by_path(tweet, "note_tweet.note_tweet_results.result.text", legacy.get("full_text", ""))
    )
    return {
        "source": "x_authors",
        "title": f"@{username}",
        "url": f"https://x.com/{username}/status/{post_id}",
        "rank": None,
        "summary": text,
        "fetched_at": _now_string(now),
        "meta": {
            "author_name": _get_author_name(user, username),
            "username": username,
            "post_id": post_id,
            "created_at": created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "like_count": legacy.get("favorite_count", 0) or 0,
            "reply_count": legacy.get("reply_count", 0) or 0,
            "retweet_count": legacy.get("retweet_count", 0) or 0,
            "quote_count": legacy.get("quote_count", 0) or 0,
            "text": text,
        },
    }


def _fetch_user_tweets_payload(
    session: requests.Session,
    username: str,
    user_id: str,
) -> dict[str, Any]:
    operation = config.X_USER_TWEETS_OPERATION or DEFAULT_X_USER_TWEETS_OPERATION
    params = _encode_params(
        {
            "variables": {
                "userId": user_id,
                "count": 20,
                "includePromotedContent": True,
                "withQuickPromoteEligibilityTweetFields": True,
                "withVoice": True,
            },
            "features": X_USER_TWEETS_FEATURES,
            "fieldToggles": {"withArticlePlainText": False},
        }
    )
    response: requests.Response | None = None
    retry_attempts = max(1, int(config.X_AUTHOR_REQUEST_RETRIES))
    for attempt in range(1, retry_attempts + 1):
        try:
            response = session.get(
                f"{X_GQL_URL}/{operation}",
                params=params,
                timeout=config.X_AUTHOR_REQUEST_TIMEOUT,
            )
            break
        except TRANSIENT_NETWORK_ERRORS as exc:
            if attempt >= retry_attempts:
                raise
            LOGGER.warning(
                "Transient X request error for @%s (attempt %s/%s): %s",
                username,
                attempt,
                retry_attempts,
                exc,
            )
            time.sleep(0.5 * attempt)

    if response is None:
        raise RuntimeError(f"X UserTweets request did not return a response for @{username}")

    if response.status_code == 404:
        raise RuntimeError(
            "X UserTweets operation id is stale. Update X_USER_TWEETS_OPERATION in config.py "
            "from a browser Copy as cURL request, for example '<id>/UserTweets'."
        )
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"X UserTweets response was not a JSON object for @{username}")

    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        messages = []
        for error in errors:
            if isinstance(error, dict):
                message = error.get("message")
                if isinstance(message, str):
                    messages.append(message)
        raise RuntimeError(
            f"X UserTweets returned errors for @{username}: {', '.join(messages) if messages else 'unknown'}"
        )

    return payload


def _fetch_author_posts(
    session: requests.Session,
    username: str,
    user_id: str,
    now: datetime,
) -> tuple[str, list[dict]]:
    payload = _fetch_user_tweets_payload(session, username, user_id)
    tweets, users = _extract_entities(payload)

    items: list[dict] = []
    for tweet_id in sorted(tweets.keys(), reverse=True):
        normalized = _normalize_post(
            tweets[tweet_id],
            users,
            username,
            now,
            expected_user_id=user_id,
        )
        if normalized is not None:
            items.append(normalized)

    items.sort(key=lambda item: item["meta"]["created_at"], reverse=True)
    return username, items[: config.X_POST_LIMIT_PER_AUTHOR]


def fetch_x_posts(now: datetime | None = None) -> dict[str, list[dict]]:
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)

    cookies = _load_cookies()
    session = _build_x_session(cookies)
    author_ids = config.get_x_author_ids()
    target_authors = [username for username in config.X_AUTHORS if author_ids.get(username)]

    try:
        if not target_authors:
            raise RuntimeError(
                "Missing userId for configured X Posts. Add username->userId entries in config.X_AUTHOR_IDS."
            )

        skipped_authors = [username for username in config.X_AUTHORS if username not in target_authors]
        if skipped_authors:
            LOGGER.info(
                "Skipping %s X Posts without configured userId: %s",
                len(skipped_authors),
                ", ".join(f"@{username}" for username in skipped_authors),
            )

        items_by_author: dict[str, list[dict]] = {}
        failures = 0

        for username in target_authors:
            try:
                user_id = author_ids[username]
                author_username, items = _fetch_author_posts(session, username, user_id, current_time)
                if items:
                    items_by_author[author_username] = items
            except requests.Timeout:
                failures += 1
                LOGGER.error(
                    "X author fetch timed out for @%s after %ss",
                    username,
                    config.X_AUTHOR_REQUEST_TIMEOUT,
                )
            except Exception as exc:
                failures += 1
                LOGGER.error("X author fetch failed for @%s: %s", username, exc)

        if failures == len(target_authors):
            raise RuntimeError("No valid X author posts fetched")

        if not items_by_author:
            LOGGER.info(
                "No X author posts matched filters in the last %sh (replies/reposts/quotes excluded)",
                config.X_LOOKBACK_HOURS,
            )
            return {}

        return items_by_author
    finally:
        session.close()
