from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

import config


def _now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean_text(element: Tag | None) -> str:
    if element is None:
        return ""
    return " ".join(element.get_text(" ", strip=True).split())


def _extract_stars_today(article: Tag) -> int | None:
    for text in article.stripped_strings:
        normalized = " ".join(text.split())
        if "star today" not in normalized.lower() and "stars today" not in normalized.lower():
            continue

        match = re.search(r"([\d,]+)", normalized)
        if match:
            return int(match.group(1).replace(",", ""))

    return None


def fetch_github_trending(limit: int) -> list[dict]:
    response = requests.get(
        config.GITHUB_TRENDING_URL,
        headers={"User-Agent": config.USER_AGENT},
        timeout=config.REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.select("article.Box-row")
    if not articles:
        raise ValueError("GitHub Trending page structure was not recognized")

    items: list[dict] = []

    for rank, article in enumerate(articles, start=1):
        if len(items) >= limit:
            break

        link = article.select_one("h2 a")
        if not isinstance(link, Tag):
            print(f"[ERROR] GitHub Trending parse failed at rank {rank}: missing repo link")
            continue

        href = link.get("href")
        if not href:
            print(f"[ERROR] GitHub Trending parse failed at rank {rank}: missing href")
            continue

        repo_name = href.strip("/")
        description = _clean_text(article.select_one("p"))
        language = _clean_text(article.select_one('[itemprop="programmingLanguage"]'))
        stars_today = _extract_stars_today(article)

        items.append(
            {
                "source": "github_trending",
                "title": repo_name,
                "url": urljoin("https://github.com", href),
                "rank": rank,
                "summary": description,
                "fetched_at": _now_string(),
                "meta": {
                    "repo_name": repo_name,
                    "language": language,
                    "stars_today": stars_today,
                    "description": description,
                },
            }
        )

    if not items:
        raise RuntimeError("No valid GitHub Trending items fetched")

    return items
