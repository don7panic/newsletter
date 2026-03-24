from __future__ import annotations

from datetime import datetime
from pathlib import Path

import config
from fetchers.github_trending import fetch_github_trending
from fetchers.hn import fetch_hn
from renderers.markdown import render_markdown
from storage.writer import write_output


def log(level: str, message: str) -> None:
    print(f"[{level}] {message}")


def main() -> int:
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%d %H:%M:%S")

    hn_items: list[dict] = []
    trending_items: list[dict] = []

    try:
        log("INFO", "Fetching Hacker News items")
        hn_items = fetch_hn(config.DEFAULT_ITEM_LIMIT)
        log("INFO", f"Fetched {len(hn_items)} Hacker News items")
    except Exception as exc:
        log("ERROR", f"Hacker News fetch failed: {exc}")

    try:
        log("INFO", "Fetching GitHub Trending items")
        trending_items = fetch_github_trending(config.DEFAULT_ITEM_LIMIT)
        log("INFO", f"Fetched {len(trending_items)} GitHub Trending items")
    except Exception as exc:
        log("ERROR", f"GitHub Trending fetch failed: {exc}")

    if not hn_items and not trending_items:
        log("ERROR", "Both sources failed; digest was not generated")
        return 1

    output_path = Path(config.OUTPUT_DIR) / f"{date_str}.md"

    try:
        markdown = render_markdown(
            date_str=date_str,
            hn_items=hn_items,
            trending_items=trending_items,
            generated_at=generated_at,
        )
        write_output(str(output_path), markdown)
    except Exception as exc:
        log("ERROR", f"Failed to render or write digest: {exc}")
        return 1

    log("INFO", f"Wrote digest to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
