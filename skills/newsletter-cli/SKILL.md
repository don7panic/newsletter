---
name: newsletter-cli
description: Use when the user wants to generate today's newsletter, inspect today's digest Markdown, or troubleshoot a failed installed `newsletter` CLI run.
---

# Newsletter CLI

Use this skill when the user wants to run the installed `newsletter` command, inspect today's output, or debug a failed run.

## Context

User notes: `$ARGUMENTS`

- Current working directory:

!`pwd`

- Installed CLI run:

!`${CLAUDE_SKILL_DIR}/scripts/run.sh`

- Today's digest, if present:

!`${CLAUDE_SKILL_DIR}/scripts/show_digest.sh`

## Ground Truth

- Installed CLI command: `newsletter`
- Recommended user invocation: `newsletter`
- Repo-local development invocation: `uv run newsletter`
- Direct entry: `uv run python main.py`
- Output path: `./daily/YYYY-MM-DD.md` relative to the working directory where the CLI is run
- Source of truth is code, not older docs
- Current rendered section order is `GitHub Trending` first, then `Hacker News`
- If both sources fail, the CLI exits non-zero
- If one source fails, partial output is acceptable and the file should still be written

Default to `newsletter` when the user asks to run or validate the installed CLI. Only switch to `uv run newsletter` when the user explicitly wants to test the current repository checkout instead of the installed command.

## Your Task

Use the injected command output above to:

1. Classify the run as success, partial success, or failure.
2. Confirm whether today's digest file exists.
3. Verify the digest contains:
   - `# Newsletter - YYYY-MM-DD`
   - `## GitHub Trending`
   - `## Hacker News`
   - `Generated at:`
4. If the run failed, identify the first likely issue area:
   - CLI orchestration in `main.py`
   - Hacker News fetching in `fetchers/hn.py`
   - GitHub Trending fetching in `fetchers/github_trending.py`
   - Markdown rendering in `renderers/markdown.py`
   - File writing in `storage/writer.py`

Keep the response concise and action-oriented.
