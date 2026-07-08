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


def _rank_for_fallback(item: dict) -> int:
    rank = item.get("rank")
    return rank if isinstance(rank, int) else config.DEFAULT_ITEM_LIMIT + 1


def _restore_minimum_items(
    *,
    kept_items: list[dict],
    scored_items: list[dict],
    minimum_count: int,
) -> None:
    min_items = min(minimum_count, len(scored_items))

    if len(kept_items) >= min_items:
        return

    kept_ids = {id(item) for item in kept_items}
    needed = min_items - len(kept_items)
    for item in sorted(scored_items, key=_rank_for_fallback):
        if id(item) in kept_ids:
            continue
        kept_items.append(item)
        kept_ids.add(id(item))
        needed -= 1
        if needed == 0:
            break


def filter_ai_items(items: list[dict], minimum_count: int = 0) -> list[dict]:
    scored_items, ai_worked = score_and_summarize(items)

    if not ai_worked:
        LOGGER.warning("AI scoring failed for all items, skipping filter")
        return items

    kept_items = [
        item
        for item in scored_items
        if item.get("ai_score", 0.0) >= config.AI_SCORE_THRESHOLD
    ]

    _restore_minimum_items(
        kept_items=kept_items,
        scored_items=scored_items,
        minimum_count=minimum_count,
    )

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

    # --- AI scoring & filtering ---
    if config.AI_ENABLED:
        before_hn = len(hn_items)
        before_trending = len(trending_items)
        before = before_hn + before_trending
        LOGGER.info("AI scoring enabled, scoring Hacker News %d items", before_hn)
        hn_items = filter_ai_items(
            hn_items,
            minimum_count=config.HN_MIN_ITEMS_AFTER_AI,
        )
        LOGGER.info("AI scoring enabled, scoring GitHub Trending %d items", before_trending)
        trending_items = filter_ai_items(
            trending_items,
            minimum_count=config.GITHUB_TRENDING_MIN_ITEMS_AFTER_AI,
        )
        after = len(hn_items) + len(trending_items)
        LOGGER.info(
            "AI filter: %d items kept (threshold >= %s), %d removed",
            after,
            config.AI_SCORE_THRESHOLD,
            before - after,
        )
        LOGGER.info(
            "AI filter by source: Hacker News %d/%d kept, GitHub Trending %d/%d kept",
            len(hn_items),
            before_hn,
            len(trending_items),
            before_trending,
        )

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
