from __future__ import annotations


def _render_hn_items(items: list[dict]) -> list[str]:
    if not items:
        return ["No items fetched."]

    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        meta = item.get("meta", {})
        score = meta.get("score")
        comments = meta.get("comments")
        discussion_url = meta.get("hn_discussion_url", "")
        summary = item.get("summary") or ""
        title = item.get("title") or "Untitled"
        url = item.get("url") or discussion_url or "#"

        lines.extend(
            [
                f"{index}. [{title}]({url})",
                f"   - {score if score is not None else 0} points, {comments if comments is not None else 0} comments",
                f"   - HN: {discussion_url}",
                f"   - Summary: {summary}",
                "",
            ]
        )

    return lines[:-1]


def _render_trending_items(items: list[dict]) -> list[str]:
    if not items:
        return ["No items fetched."]

    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        meta = item.get("meta", {})
        repo_name = meta.get("repo_name") or item.get("title") or "unknown/unknown"
        language = meta.get("language", "")
        stars_today = meta.get("stars_today")
        description = meta.get("description", "")
        url = item.get("url") or "#"

        lines.extend(
            [
                f"{index}. [{repo_name}]({url})",
                f"   - Language: {language}",
                f"   - ⭐ today: {stars_today if stars_today is not None else ''}",
                f"   - Description: {description}",
                "",
            ]
        )

    return lines[:-1]


def render_markdown(
    date_str: str,
    hn_items: list[dict],
    trending_items: list[dict],
    generated_at: str,
) -> str:
    lines = [
        f"# Newsletter - {date_str}",
        "",
        "## GitHub Trending",
        "",
        *_render_trending_items(trending_items),
        "",
        "## Hacker News",
        "",
        *_render_hn_items(hn_items),
        "",
        "---",
        f"Generated at: {generated_at}",
    ]
    return "\n".join(lines) + "\n"
