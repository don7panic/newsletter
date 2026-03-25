#!/usr/bin/env bash

set -euo pipefail

WORKDIR="$(pwd)"

set +e
OUTPUT="$(newsletter 2>&1)"
STATUS=$?
set -e

printf '__WORKDIR__=%s\n' "${WORKDIR}"
printf '%s\n' "${OUTPUT}"
printf '\n__EXIT_CODE__=%s\n' "${STATUS}"
