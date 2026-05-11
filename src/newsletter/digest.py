from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from newsletter import config
from newsletter.ai.client import score_and_summarize
from newsletter.fetchers.github_trending import fetch_github_trending
from newsletter.fetchers.hn import fetch_hn
from newsletter.fetchers.x_posts import fetch_x_posts
from newsletter.renderers.markdown import render_markdown
from newsletter.storage.writer import write_output


@dataclass(frozen=True)
class DigestInspection:
    state: str
    detail: str


LOGGER = logging.getLogger(__name__)


def get_enabled_section_headings(include_x: bool | None = None) -> tuple[str, ...]:
    headings = ["GitHub Trending", "Hacker News"]
    x_enabled = config.X_ENABLED if include_x is None else include_x
    if x_enabled:
        headings.insert(0, "X Posts")
    return tuple(headings)


def get_now() -> datetime:
    return datetime.now()


def get_output_path(now: datetime | None = None) -> Path:
    current_time = now or get_now()
    return Path(config.OUTPUT_DIR) / f"{current_time:%Y-%m-%d}.md"


def get_timestamp_strings(now: datetime | None = None) -> tuple[str, str]:
    current_time = now or get_now()
    return (
        current_time.strftime("%Y-%m-%d"),
        current_time.strftime("%Y-%m-%d %H:%M:%S"),
    )


def extract_sections(content: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None

    for line in content.splitlines():
        if line.startswith("## "):
            current_heading = line.removeprefix("## ")
            sections[current_heading] = []
            continue

        if line == "---":
            current_heading = None
            continue

        if current_heading is not None:
            sections[current_heading].append(line)

    return sections


def section_has_no_items(lines: list[str]) -> bool:
    meaningful_lines = [line.strip() for line in lines if line.strip()]
    return meaningful_lines == ["No items fetched."]


def inspect_digest(path: Path, now: datetime | None = None) -> DigestInspection:
    if not path.exists():
        return DigestInspection("missing", "Newsletter file does not exist.")

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return DigestInspection("invalid", f"Failed to read newsletter file: {exc}")

    date_str, _ = get_timestamp_strings(now)
    required_markers = [f"# Newsletter - {date_str}", "Generated at:"]
    required_markers.extend(f"## {heading}" for heading in get_enabled_section_headings())
    missing_markers = [marker for marker in required_markers if marker not in content]
    if missing_markers:
        return DigestInspection(
            "invalid",
            "Newsletter file is missing required content: "
            + ", ".join(missing_markers),
        )

    sections = extract_sections(content)
    empty_sections = [
        heading
        for heading in get_enabled_section_headings()
        if section_has_no_items(sections.get(heading, []))
    ]
    if empty_sections:
        return DigestInspection(
            "partial",
            "Sections with no items: " + ", ".join(empty_sections),
        )

    return DigestInspection("success", "Newsletter file exists and includes all enabled sections.")


def _source_items(items: list[dict], source: str) -> list[dict]:
    return [item for item in items if item.get("source") == source]


def _rank_for_fallback(item: dict) -> int:
    rank = item.get("rank")
    return rank if isinstance(rank, int) else config.DEFAULT_ITEM_LIMIT + 1


def filter_ai_items(items: list[dict]) -> list[dict]:
    scored_items = score_and_summarize(items)
    kept_items = [
        item
        for item in scored_items
        if item.get("ai_score", 0.0) >= config.AI_SCORE_THRESHOLD
    ]

    hn_items = _source_items(scored_items, "hacker_news")
    hn_kept_count = len(_source_items(kept_items, "hacker_news"))
    hn_min_items = min(config.HN_MIN_ITEMS_AFTER_AI, len(hn_items))

    if hn_kept_count < hn_min_items:
        kept_ids = {id(item) for item in kept_items}
        needed = hn_min_items - hn_kept_count
        for item in sorted(hn_items, key=_rank_for_fallback):
            if id(item) in kept_ids:
                continue
            kept_items.append(item)
            kept_ids.add(id(item))
            needed -= 1
            if needed == 0:
                break

    return kept_items


def generate_digest(now: datetime | None = None) -> int:
    current_time = now or get_now()
    date_str, generated_at = get_timestamp_strings(current_time)

    hn_items: list[dict] = []
    trending_items: list[dict] = []
    x_items_by_author: dict[str, list[dict]] | None = None
    successful_sources = 0

    try:
        LOGGER.info("Fetching Hacker News items")
        hn_items = fetch_hn(config.DEFAULT_ITEM_LIMIT)
        LOGGER.info("Fetched %s Hacker News items", len(hn_items))
        successful_sources += 1
    except Exception as exc:
        LOGGER.error("Hacker News fetch failed: %s", exc)

    try:
        LOGGER.info("Fetching GitHub Trending items")
        trending_items = fetch_github_trending(config.DEFAULT_ITEM_LIMIT)
        LOGGER.info("Fetched %s GitHub Trending items", len(trending_items))
        successful_sources += 1
    except Exception as exc:
        LOGGER.error("GitHub Trending fetch failed: %s", exc)

    if config.X_ENABLED:
        x_items_by_author = {}
        try:
            LOGGER.info("Fetching X author posts")
            x_items_by_author = fetch_x_posts(current_time)
            post_count = sum(len(items) for items in x_items_by_author.values())
            LOGGER.info("Fetched %s X author posts", post_count)
            successful_sources += 1
        except Exception as exc:
            LOGGER.error("X author posts fetch failed: %s", exc)

    all_items: list[dict] = []
    all_items.extend(hn_items)
    all_items.extend(trending_items)

    # --- AI scoring & filtering ---
    if config.AI_ENABLED:
        LOGGER.info("AI scoring enabled, scoring %d items", len(all_items))
        before = len(all_items)
        before_hn = len(_source_items(all_items, "hacker_news"))
        before_trending = len(_source_items(all_items, "github_trending"))
        all_items = filter_ai_items(all_items)
        LOGGER.info(
            "AI filter: %d items kept (threshold >= %s), %d removed",
            len(all_items),
            config.AI_SCORE_THRESHOLD,
            before - len(all_items),
        )
        LOGGER.info(
            "AI filter by source: Hacker News %d/%d kept, GitHub Trending %d/%d kept",
            len(_source_items(all_items, "hacker_news")),
            before_hn,
            len(_source_items(all_items, "github_trending")),
            before_trending,
        )

    # Separate back into source-specific lists for the renderer
    hn_items = [it for it in all_items if it.get("source") == "hacker_news"]
    trending_items = [it for it in all_items if it.get("source") == "github_trending"]

    if successful_sources == 0:
        LOGGER.error("All enabled sources failed; newsletter was not generated")
        return 1

    output_path = get_output_path(current_time)

    try:
        markdown = render_markdown(
            date_str=date_str,
            hn_items=hn_items,
            trending_items=trending_items,
            x_items_by_author=x_items_by_author,
            generated_at=generated_at,
        )
        write_output(str(output_path), markdown)
    except Exception as exc:
        LOGGER.error("Failed to render or write newsletter: %s", exc)
        return 1

    LOGGER.info("Wrote newsletter to %s", output_path)
    return 0
