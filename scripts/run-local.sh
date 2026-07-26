#!/usr/bin/env bash
# Start the isolated local development bot. It must not share a token with the VPS bot.
set -euo pipefail

readonly SERVICE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly LOCAL_ENV_FILE="${SERVICE_ROOT}/.env.local"

if [[ ! -f "${LOCAL_ENV_FILE}" ]]; then
  echo "Missing ${LOCAL_ENV_FILE}. Run ./scripts/bootstrap-local.sh first." >&2
  exit 1
fi

if [[ ! -x "${SERVICE_ROOT}/.venv/bin/python" ]]; then
  echo "Missing local virtual environment. Run ./scripts/bootstrap-local.sh first." >&2
  exit 1
fi

set -a
source "${LOCAL_ENV_FILE}"
set +a
cd "${SERVICE_ROOT}"
exec "${SERVICE_ROOT}/.venv/bin/python" -m Adarsh
