#!/usr/bin/env bash
# Start the isolated local development bot. It must not share a token with the VPS bot.
set -euo pipefail

readonly SERVICE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly LOCAL_ENV_FILE="${SERVICE_ROOT}/.env.local"
readonly BACKEND_ENV_FILE="${SERVICE_ROOT}/../../backend/.env"

if [[ ! -f "${LOCAL_ENV_FILE}" ]]; then
  echo "Missing ${LOCAL_ENV_FILE}. Run ./scripts/bootstrap-local.sh first." >&2
  exit 1
fi

if [[ ! -x "${SERVICE_ROOT}/.venv/bin/python" ]]; then
  echo "Missing local virtual environment. Run ./scripts/bootstrap-local.sh first." >&2
  exit 1
fi

if [[ ! -f "${BACKEND_ENV_FILE}" ]]; then
  echo "MovieWorld backend configuration was not found at ${BACKEND_ENV_FILE}." >&2
  exit 1
fi

set -a
source "${LOCAL_ENV_FILE}"
set +a
export DB_HOST=127.0.0.1
export DB_PORT="$(awk -F= '$1=="DB_PORT" {print substr($0, index($0, "=")+1); exit}' "${BACKEND_ENV_FILE}")"
export DB_DATABASE="$(awk -F= '$1=="DB_DATABASE" {print substr($0, index($0, "=")+1); exit}' "${BACKEND_ENV_FILE}")"
export DB_USERNAME="$(awk -F= '$1=="DB_USERNAME" {print substr($0, index($0, "=")+1); exit}' "${BACKEND_ENV_FILE}")"
export DB_PASSWORD="$(awk -F= '$1=="DB_PASSWORD" {print substr($0, index($0, "=")+1); exit}' "${BACKEND_ENV_FILE}")"
cd "${SERVICE_ROOT}"
exec "${SERVICE_ROOT}/.venv/bin/python" -m Adarsh
