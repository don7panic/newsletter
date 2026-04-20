# Newsletter

[中文说明](README.zh-CN.md)

Local-first CLI for generating a daily Markdown tech newsletter from GitHub Trending, Hacker News, and optional X author posts.

```text
daily/YYYY-MM-DD.md
```

## What It Does

- Generates a daily newsletter in the directory where you run the CLI
- Renders `X Posts` first when enabled, then `GitHub Trending`, then `Hacker News`
- Overwrites the same day's file on re-run
- Writes partial output if one source fails
- Exits non-zero only when all enabled sources fail

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

Generate today's newsletter:

```bash
newsletter generate
```

Check whether today's newsletter exists and looks complete:

```bash
newsletter status
```

Print today's newsletter Markdown:

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

- `newsletter generate`: fetch data and write today's newsletter
- `newsletter status`: inspect today's newsletter file
- `newsletter show`: print today's newsletter content
- `newsletter --help`: show CLI help
- `newsletter --version`: show installed CLI version

## Output Example

```md
# Newsletter - 2026-03-25

## X Posts

### Andrej Karpathy (@karpathy)

1. [@karpathy](https://x.com/karpathy/status/1)
   - Posted: 2026-03-25T08:45:00Z
   - Text: ...

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
- Optional X author posts fetched from X Web using a logged-in cookies export

Only HN items with `type == "story"` are kept.

## Runtime Notes

- Output path is `daily/YYYY-MM-DD.md` relative to the current working directory
- The Markdown format is intentionally stable for downstream parsing or archiving
- A missing GitHub token may cause GitHub API rate limiting
- X author support uses your browser cookies against X Web endpoints and does not require API credits

You can set `GITHUB_TOKEN` or `GH_TOKEN` to reduce anonymous GitHub API limits.

## Optional X Posts Setup

To append an `X Posts` section for these authors:

- `@karpathy`
- `@sama`
- `@swyxl`
- `@joshwoodward`
- `@mattturck`
- `@trq212`

Put cookies into `.env` (recommended):

```bash
X_COOKIES='auth_token=...; ct0=...'
```

Then run:

```bash
newsletter generate
```

Notes:

- `X_COOKIES` supports three formats:
  - raw cookie header (`auth_token=...; ct0=...`)
  - JSON object (`{"auth_token":"...","ct0":"..."}`)
  - cookie list JSON (`[{"name":"auth_token","value":"..."}, ...]`)
- `X_COOKIES` in `.env` is loaded automatically and takes precedence over `X_COOKIES_PATH`
- If you prefer a file, set `X_COOKIES_PATH=/absolute/path/to/x-cookies.json` (default fallback is `./x.json`)
- The cookies must come from a logged-in X browser session
- If cookies expire, refresh the export and rerun
- Current default is hardcoded to test `@karpathy` (`33836629`) first
- If X Web starts rejecting the request, you can optionally set `X_WEB_BEARER_TOKEN` and `X_CLIENT_TRANSACTION_ID` from a browser `Copy as cURL`
- The default `UserTweets` operation is hardcoded to `x3B_xLqC0yZawOB7WQhaVQ/UserTweets`
- When both `X_COOKIES` and `X_COOKIES_PATH` are missing/unreadable, the CLI skips the X source and keeps the original two-section output

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
