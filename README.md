# Newsletter

[中文说明](README.zh-CN.md)

Local-first CLI for generating a daily Markdown tech digest from GitHub Trending and Hacker News.

```text
daily/YYYY-MM-DD.md
```

## What It Does

- Generates a daily digest in the directory where you run the CLI
- Renders `GitHub Trending` first, then `Hacker News`
- Overwrites the same day's file on re-run
- Writes partial output if one source fails
- Exits non-zero only when both sources fail

## Prerequisites

- Python `3.10+`
- `uv`

## Install

Recommended for normal CLI use:

```bash
uv tool install --force --editable .
```

After installation:

```bash
newsletter --help
```

If you prefer not to install the tool, you can run it from the repo with `uv run`.

## Quick Start

Generate today's digest:

```bash
newsletter generate
```

Check whether today's digest exists and looks complete:

```bash
newsletter status
```

Print today's digest Markdown:

```bash
newsletter show
```

Show help or version:

```bash
newsletter --help
newsletter --version
newsletter
```

`newsletter` without arguments prints the same help text as `newsletter --help`.

## Command Surface

- `newsletter generate`: fetch data and write today's digest
- `newsletter status`: inspect today's digest file
- `newsletter show`: print today's digest content
- `newsletter --help`: show CLI help
- `newsletter --version`: show installed CLI version

## Output Example

```md
# Newsletter - 2026-03-25

## GitHub Trending

1. [owner/repo](https://github.com/owner/repo)
   - Language: Python
   - ⭐ today: 2341
   - Description: ...

## Hacker News

1. [Article Title](https://example.com)
   - 320 points, 120 comments
   - HN: https://news.ycombinator.com/item?id=123
   - Summary: ...

---
Generated at: 2026-03-25 09:00:00
```

## Data Sources

- GitHub Trending page for ranking and daily star growth
- GitHub repo API for repository metadata such as description and language
- Hacker News official API for top stories and item details

Only HN items with `type == "story"` are kept.

## Runtime Notes

- Output path is `daily/YYYY-MM-DD.md` relative to the current working directory
- The Markdown format is intentionally stable for downstream parsing or archiving
- A missing GitHub token may cause GitHub API rate limiting

You can set `GITHUB_TOKEN` or `GH_TOKEN` to reduce anonymous GitHub API limits.

## Development

Install the project dependencies:

```bash
uv sync
```

Run the CLI from the repo without a global install:

```bash
uv run newsletter generate
```

## Project Layout

```text
newsletter/
  README.md
  README.zh-CN.md
  pyproject.toml
  src/
    newsletter/
      cli.py
      digest.py
      config.py
      fetchers/
      renderers/
      storage/
  tests/
  docs/
```
