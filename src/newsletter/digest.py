from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from newsletter import config
from newsletter.fetchers.github_trending import fetch_github_trending
from newsletter.fetchers.hn import fetch_hn
from newsletter.renderers.markdown import render_markdown
from newsletter.storage.writer import write_output


@dataclass(frozen=True)
class DigestInspection:
    state: str
    detail: str


LOGGER = logging.getLogger(__name__)


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
        if line in {"## GitHub Trending", "## Hacker News"}:
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
    required_markers = (
        f"# Newsletter - {date_str}",
        "## GitHub Trending",
        "## Hacker News",
        "Generated at:",
    )
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
        for heading in ("GitHub Trending", "Hacker News")
        if section_has_no_items(sections.get(heading, []))
    ]
    if empty_sections:
        return DigestInspection(
            "partial",
            "Sections with no items: " + ", ".join(empty_sections),
        )

    return DigestInspection("success", "Newsletter file exists and includes both sections.")


def generate_digest(now: datetime | None = None) -> int:
    current_time = now or get_now()
    date_str, generated_at = get_timestamp_strings(current_time)

    hn_items: list[dict] = []
    trending_items: list[dict] = []

    try:
        LOGGER.info("Fetching Hacker News items")
        hn_items = fetch_hn(config.DEFAULT_ITEM_LIMIT)
        LOGGER.info("Fetched %s Hacker News items", len(hn_items))
    except Exception as exc:
        LOGGER.error("Hacker News fetch failed: %s", exc)

    try:
        LOGGER.info("Fetching GitHub Trending items")
        trending_items = fetch_github_trending(config.DEFAULT_ITEM_LIMIT)
        LOGGER.info("Fetched %s GitHub Trending items", len(trending_items))
    except Exception as exc:
        LOGGER.error("GitHub Trending fetch failed: %s", exc)

    if not hn_items and not trending_items:
        LOGGER.error("Both sources failed; newsletter was not generated")
        return 1

    output_path = get_output_path(current_time)

    try:
        markdown = render_markdown(
            date_str=date_str,
            hn_items=hn_items,
            trending_items=trending_items,
            generated_at=generated_at,
        )
        write_output(str(output_path), markdown)
    except Exception as exc:
        LOGGER.error("Failed to render or write newsletter: %s", exc)
        return 1

    LOGGER.info("Wrote newsletter to %s", output_path)
    return 0
