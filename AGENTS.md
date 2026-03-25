# AGENTS.md

Guidance for agents working in this repository.

## Skills

These project-local skills should be used when their description matches the task.

- `newsletter-cli`: Generate today's newsletter, inspect today's digest Markdown, or troubleshoot a failed installed `newsletter` CLI run. (file: `./skills/newsletter-cli/SKILL.md`)

## Read This First

1. `README.md`
2. `main.py`
3. `renderers/markdown.py`

## Repo Facts

- CLI command name: `newsletter`
- Recommended user invocation: `newsletter`
- Repo-local development invocation: `uv run newsletter`
- Direct entry script: `uv run python main.py`
- Output path: `./daily/YYYY-MM-DD.md` relative to the working directory where the CLI is run
- Code is the source of truth when docs disagree
- Current rendered section order is `GitHub Trending` first, then `Hacker News`
- If both sources fail, the CLI should exit non-zero
- If one source fails, partial output is acceptable and the file should still be written

## Important Files

- `config.py`
- `fetchers/hn.py`
- `fetchers/github_trending.py`
- `renderers/markdown.py`
- `storage/writer.py`
