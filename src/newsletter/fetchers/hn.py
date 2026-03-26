from __future__ import annotations

from datetime import datetime

import requests
from bs4 import BeautifulSoup

from newsletter import config


SUMMARY_MAX_LENGTH = 280


def _now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _get_json(session: requests.Session, url: str) -> object:
    response = session.get(url, timeout=config.REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _extract_summary(text: object) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""

    cleaned = " ".join(BeautifulSoup(text, "html.parser").get_text(" ", strip=True).split())
    if len(cleaned) <= SUMMARY_MAX_LENGTH:
        return cleaned

    return cleaned[: SUMMARY_MAX_LENGTH - 3].rstrip() + "..."


def fetch_hn(limit: int) -> list[dict]:
    session = requests.Session()
    session.headers.update({"User-Agent": config.USER_AGENT})

    top_story_ids = _get_json(session, config.HN_TOP_STORIES_URL)
    if not isinstance(top_story_ids, list):
        raise ValueError("Unexpected Hacker News top stories response")

    items: list[dict] = []

    for rank, item_id in enumerate(top_story_ids, start=1):
        if len(items) >= limit:
            break

        try:
            item = _get_json(
                session,
                config.HN_ITEM_URL_TEMPLATE.format(item_id=item_id),
            )
        except Exception as exc:
            print(f"[ERROR] Hacker News item request failed for {item_id}: {exc}")
            continue

        if not isinstance(item, dict):
            print(f"[ERROR] Hacker News item parse failed for {item_id}: invalid JSON")
            continue

        if item.get("type") != "story":
            continue

        title = item.get("title")
        if not title:
            print(f"[ERROR] Hacker News item parse failed for {item_id}: missing title")
            continue

        discussion_url = f"https://news.ycombinator.com/item?id={item.get('id', item_id)}"

        items.append(
            {
                "source": "hacker_news",
                "title": title,
                "url": item.get("url") or discussion_url,
                "rank": rank,
                "summary": _extract_summary(item.get("text")),
                "fetched_at": _now_string(),
                "meta": {
                    "score": item.get("score"),
                    "comments": item.get("descendants"),
                    "hn_discussion_url": discussion_url,
                },
            }
        )

    if not items:
        raise RuntimeError("No valid Hacker News items fetched")

    return items
