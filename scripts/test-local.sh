#!/usr/bin/env bash
# Verify the local-only web endpoint without exposing the token in terminal output.
set -euo pipefail

readonly SERVICE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly LOCAL_ENV_FILE="${SERVICE_ROOT}/.env.local"

if [[ ! -f "${LOCAL_ENV_FILE}" ]]; then
  echo "Missing ${LOCAL_ENV_FILE}. Run ./scripts/bootstrap-local.sh first." >&2
  exit 1
fi

set -a
source "${LOCAL_ENV_FILE}"
set +a

curl --fail --silent --show-error "${PUBLIC_BASE_URL}/healthz?token=${HEALTHCHECK_TOKEN}"
printf '\nlocal-health=passed\n'
