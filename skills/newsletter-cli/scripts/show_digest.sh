#!/usr/bin/env bash

set -euo pipefail

WORKDIR="$(pwd)"

FILE="daily/$(date +%F).md"

if [[ -f "${FILE}" ]]; then
  printf '__WORKDIR__=%s\n' "${WORKDIR}"
  printf '__DIGEST_FILE__=%s\n' "${FILE}"
  sed -n '1,220p' "${FILE}"
else
  printf '__WORKDIR__=%s\n' "${WORKDIR}"
  printf '__DIGEST_FILE_MISSING__=%s\n' "${FILE}"
fi
