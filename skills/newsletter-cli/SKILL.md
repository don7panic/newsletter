---
name: newsletter-cli
description: Use when the user wants to generate today's newsletter, inspect today's digest Markdown, or troubleshoot a failed installed `newsletter` CLI run.
---

# Newsletter CLI

Use this skill when the user wants to run the installed `newsletter` command, inspect today's output, or debug a failed run.

## Context

User request notes: `$ARGUMENTS`

- Current working directory:

`pwd`

- Current date: `$CURRENT_DATE` (format: YYYY-MM-DD)

- Check if newsletter CLI is installed:

`which newsletter 2>&1 || echo "not_installed"`

- Get newsletter CLI version:

`newsletter --version 2>&1 || echo "version_check_failed"`

- Typical installed CLI commands:
  - `newsletter generate`
  - `newsletter status`
  - `newsletter show`
  - `newsletter --version`

## Ground Truth

- Installed CLI command: `newsletter`
- Supported CLI surface:
  - `newsletter generate` - Generate today's newsletter
  - `newsletter status` - Check status of today's newsletter
  - `newsletter show` - Display today's newsletter
  - `newsletter --help` - Show help
  - `newsletter --version` - Show version
- Bare `newsletter` prints help
- Output path: `./daily/YYYY-MM-DD.md` relative to the working directory where the CLI is run
- Source of truth is code, not older docs
- Current rendered section order is `GitHub Trending` first, then `Hacker News`
- If both sources fail, the CLI exits non-zero
- If one source fails, partial output is acceptable and the file should still be written

Do not introduce or rely on additional helper scripts; the installed CLI surface above is sufficient.

Do not suggest or run `uv run newsletter` as part of this skill. Use the installed CLI surface above. If the user wants source-level debugging of a repository checkout, handle that as a separate code task rather than as installed-CLI validation.

## Execution Steps

### Step 1: Generate Newsletter

Run the newsletter generation command:

`newsletter generate 2>&1`

### Step 2: Check Status

Run status to confirm generation result:

`newsletter status 2>&1`

### Step 3: Read Today's Digest File

Read the generated digest file using the CLI:

`newsletter show 2>&1`

## Your Task

Use the injected command output above to:

1. **Check CLI Availability**: If `which newsletter` returns "not_installed", report that `newsletter` is not installed or not on `PATH`.

2. **Classify the Run**: Based on `newsletter generate` output and exit behavior, classify as:
   - `success` - Both sources fetched and rendered successfully
   - `partial` - One source failed but file was still written
   - `failure` - Both sources failed or file write failed

3. **Verify Digest File**: Check if `./daily/$CURRENT_DATE.md` exists (if Step 3 output is "FILE_NOT_FOUND", the file is missing).

4. **Validate Content**: If file exists, verify it contains:
   - `# Newsletter - YYYY-MM-DD` (correct date header)
   - `## GitHub Trending`
   - `## Hacker News`
   - `Generated at:` timestamp

5. **Cross-check Status**: Use `newsletter status` output to confirm status matches (`success`, `partial`, `missing`, or `invalid`).

6. **Failure Analysis**: If run failed, identify the first likely failure category:
   - `newsletter` is not installed or not on `PATH`
   - CLI version mismatch or unsupported subcommand
   - Network or upstream fetch failure
   - Render or file-write failure

## Response Format

Provide a concise summary:
- **Status**: success / partial / failure
- **File**: Path to today's digest and whether it exists
- **Content Check**: List of required sections found/missing
- **Issues**: Any failures or warnings detected
- **Action**: Recommended next step if needed

Do not imply that helper scripts are user-facing CLI commands; use the CLI surface above.
