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


def _build_github_api_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": config.USER_AGENT,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": config.GITHUB_API_VERSION,
        }
    )
    if config.GITHUB_TOKEN:
        session.headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    return session


def _fetch_repo_metadata(session: requests.Session, repo_name: str) -> tuple[dict, bool]:
    try:
        response = session.get(
            config.GITHUB_REPO_API_URL_TEMPLATE.format(repo_name=repo_name),
            timeout=config.REQUEST_TIMEOUT,
        )
    except Exception as exc:
        print(f"[ERROR] GitHub repo API request failed for {repo_name}: {exc}")
        return {}, True

    if response.status_code in {403, 429}:
        print(
            "[ERROR] GitHub repo API is unavailable for this run; "
            f"status {response.status_code}. Falling back to page fields."
        )
        return {}, False

    if response.status_code != 200:
        print(f"[ERROR] GitHub repo API request failed for {repo_name}: status {response.status_code}")
        return {}, True

    data = response.json()
    if not isinstance(data, dict):
        print(f"[ERROR] GitHub repo API parse failed for {repo_name}: invalid JSON")
        return {}, True

    return (
        {
            "description": data.get("description") or "",
            "language": data.get("language") or "",
            "stars_total": data.get("stargazers_count"),
            "forks": data.get("forks_count"),
        },
        True,
    )


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

    api_session = _build_github_api_session()
    api_available = True
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
        page_description = _clean_text(article.select_one("p"))
        page_language = _clean_text(article.select_one('[itemprop="programmingLanguage"]'))
        stars_today = _extract_stars_today(article)
        repo_metadata = {}
        if api_available:
            repo_metadata, api_available = _fetch_repo_metadata(api_session, repo_name)
        description = repo_metadata.get("description") or page_description
        language = repo_metadata.get("language") or page_language

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
                    "stars_total": repo_metadata.get("stars_total"),
                    "forks": repo_metadata.get("forks"),
                },
            }
        )

    if not items:
        raise RuntimeError("No valid GitHub Trending items fetched")

    return items
