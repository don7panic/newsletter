# Newsletter

Local-first daily tech digest generator for GitHub Trending and Hacker News.

一个本地优先的每日技术简报生成器，用于抓取 GitHub Trending 和 Hacker News，并输出为 Markdown 文件。

```text
daily/YYYY-MM-DD.md
```

This project is designed for personal dashboards, scheduled digests, and Markdown-first archival workflows.

这个项目适合个人日报、定时任务、Markdown 归档，以及后续周报 / 月报的输入流程。

## Highlights / 特性

- Local-first, no database, no web service
- `uv`-managed Python project
- GitHub Trending ranking from the Trending page
- GitHub repository metadata enriched via the GitHub repo API
- Hacker News data from the official API
- Only keeps HN items with `type == "story"`
- Extracts a simple summary from HN posts that include `text`
- Stable Markdown output for downstream parsing
- Re-running on the same day overwrites the existing file
- Partial output is allowed if one source fails

## Quick Start / 快速开始

Install dependencies:

安装依赖：

```bash
uv sync
```

Generate today's digest:

生成当天日报：

```bash
uv run newsletter
```

Or run the entry script directly:

也可以直接运行入口脚本：

```bash
uv run python main.py
```

Default output path:

默认输出路径：

```text
daily/YYYY-MM-DD.md
```

## Example Output / 输出示例

```md
# Newsletter - 2026-03-25

## GitHub Trending

1. [owner/repo](https://github.com/owner/repo)
   - Language: Python
   - Stars today: 2341
   - Description: ...

## Hacker News

1. [Article Title](https://example.com)
   - 320 points, 120 comments
   - HN: https://news.ycombinator.com/item?id=123
   - Summary: ...

---
Generated at: 2026-03-25 09:00:00
```

## How It Works / 工作方式

### GitHub Trending

- Reads `https://github.com/trending?since=daily`
- Uses the Trending page for ranking and `stars today`
- Calls `https://api.github.com/repos/{owner}/{repo}` to enrich fields like `description` and `language`
- Falls back to page-derived fields if the repo API is unavailable or rate-limited

### Hacker News

- Reads `https://hacker-news.firebaseio.com/v0/topstories.json`
- Fetches item details from `https://hacker-news.firebaseio.com/v0/item/{id}.json`
- Keeps only `story` items
- Extracts a short summary from HTML `text` when present

## Notes / 说明

- Default fetch size is `Top 10` per source
- The output format is intentionally stable and Markdown-first
- Running multiple times on the same day overwrites `daily/YYYY-MM-DD.md`
- If both sources fail, the program exits with a non-zero status
- If only one source fails, a partial digest is still generated

### Optional GitHub Token / 可选 GitHub Token

You can set `GITHUB_TOKEN` or `GH_TOKEN` to reduce the chance of hitting anonymous GitHub API rate limits.

你可以设置 `GITHUB_TOKEN` 或 `GH_TOKEN`，降低匿名访问 GitHub API 时遇到限流的概率。

## Project Layout / 项目结构

```text
newsletter/
  README.md
  pyproject.toml
  main.py
  config.py
  fetchers/
  renderers/
  storage/
  daily/
  docs/
```
