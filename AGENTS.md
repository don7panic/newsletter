# AGENTS.md

Guidance for agents working in this repository.

## Skills

These project-local skills should be used when their description matches the task.

- `newsletter-cli`: Run the installed `newsletter` command, inspect today's generated newsletter Markdown, or troubleshoot a failed installed CLI run. (file: `./skills/newsletter-cli/SKILL.md`)

## Read This First

1. `README.md`
2. `src/newsletter/cli.py`
3. `src/newsletter/digest.py`

## Repo Facts

- CLI command name: `newsletter`
- Supported CLI surface for users:
  - `newsletter generate`
  - `newsletter status`
  - `newsletter show`
  - `newsletter --help`
  - `newsletter --version`
  - bare `newsletter` prints help
- Output path: `./daily/YYYY-MM-DD.md` relative to the working directory where the CLI is run
- Code is the source of truth when docs disagree
- Current rendered section order is `GitHub Trending` first, then `Hacker News`
- If both sources fail, the CLI should exit non-zero
- If one source fails, partial output is acceptable and the file should still be written

## Important Files

- `main.py`
- `src/newsletter/cli.py`
- `src/newsletter/digest.py`
- `src/newsletter/config.py`
- `src/newsletter/fetchers/hn.py`
- `src/newsletter/fetchers/github_trending.py`
- `src/newsletter/renderers/markdown.py`
- `src/newsletter/storage/writer.py`
