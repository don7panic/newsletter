#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="newsletter-cli"
SKILL_DIR="${SCRIPT_DIR}/${SKILL_NAME}"

usage() {
  echo "Usage: $0 [destination-directory]" >&2
  echo "Installs ${SKILL_NAME} into ~/.claude/skills/${SKILL_NAME} by default." >&2
  echo "Pass [destination-directory] to override the skills root." >&2
}

if [[ $# -gt 1 ]]; then
  usage
  exit 1
fi

if [[ ! -d "${SKILL_DIR}" ]]; then
  echo "Skill directory not found: ${SKILL_DIR}" >&2
  exit 1
fi

DEFAULT_DEST_ROOT="${HOME}/.claude/skills"
DEST_ROOT="${1:-$DEFAULT_DEST_ROOT}"
DEST_DIR="${DEST_ROOT%/}/${SKILL_NAME}"

mkdir -p "${DEST_ROOT}"

if [[ -e "${DEST_DIR}" ]]; then
  rm -rf "${DEST_DIR}"
fi

cp -R "${SKILL_DIR}" "${DEST_DIR}"

echo "Installed Claude Code skill to: ${DEST_DIR}"
