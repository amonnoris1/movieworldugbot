#!/usr/bin/env bash
# Export the small MySQL recovery dataset to stdout. Run as root on the VPS.
# Redirect the output over SSH to an encrypted or permission-restricted backup
# location outside the VPS. This script intentionally never exports the
# protected environment file or prints any credentials.
set -euo pipefail

readonly ENV_FILE="/etc/movieworld-telegram-streamer.env"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root so it can read the protected environment file." >&2
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

export MYSQL_PWD="${DB_PASSWORD}"
exec mysqldump \
  --single-transaction \
  --skip-lock-tables \
  --no-tablespaces \
  --host="${DB_HOST}" \
  --port="${DB_PORT}" \
  --user="${DB_USERNAME}" \
  "${DB_DATABASE}"
