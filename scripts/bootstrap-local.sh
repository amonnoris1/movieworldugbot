#!/usr/bin/env bash
# Create the ignored local bot configuration using MovieWorld's existing local database.
# Use a separate Telegram development bot and private development channel.
set -euo pipefail

readonly SERVICE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly LOCAL_ENV_FILE="${SERVICE_ROOT}/.env.local"
readonly BACKEND_ENV_FILE="${SERVICE_ROOT}/../../backend/.env"
readonly MYSQL_BIN="/Applications/AMPPS/apps/mysql/bin/mysql"
readonly MYSQL_SOCKET="/Applications/AMPPS/apps/mysql/var/mysql.sock"

if [[ -f "${LOCAL_ENV_FILE}" ]]; then
  echo "${LOCAL_ENV_FILE} already exists; refusing to overwrite local credentials." >&2
  exit 1
fi

if [[ ! -x "${MYSQL_BIN}" ]]; then
  echo "AMPPS MySQL was not found at ${MYSQL_BIN}. Start AMPPS MySQL first." >&2
  exit 1
fi

if [[ ! -f "${BACKEND_ENV_FILE}" ]]; then
  echo "MovieWorld backend configuration was not found at ${BACKEND_ENV_FILE}." >&2
  exit 1
fi

backend_db_username="$(awk -F= '$1=="DB_USERNAME" {print substr($0, index($0, "=")+1); exit}' "${BACKEND_ENV_FILE}")"
backend_db_password="$(awk -F= '$1=="DB_PASSWORD" {print substr($0, index($0, "=")+1); exit}' "${BACKEND_ENV_FILE}")"

MYSQL_PWD="${backend_db_password}" "${MYSQL_BIN}" \
  --protocol=socket --socket="${MYSQL_SOCKET}" -u "${backend_db_username}" -N -e 'SELECT 1' >/dev/null

read -r -p "Development Telegram API ID: " api_id
read -r -p "Development Telegram API hash: " api_hash
read -r -s -p "Development bot token: " bot_token
printf '\n'
read -r -p "Development private channel ID: " bin_channel
read -r -p "Your Telegram owner ID: " owner_id

if [[ ! "${api_id}" =~ ^[0-9]+$ || ! "${bin_channel}" =~ ^-?[0-9]+$ || ! "${owner_id}" =~ ^[0-9]+$ ]]; then
  echo "API ID, channel ID, and owner ID must be numeric." >&2
  exit 1
fi

healthcheck_token="$(openssl rand -hex 32)"

umask 077
{
  printf 'API_ID=%s\n' "${api_id}"
  printf 'API_HASH=%s\n' "${api_hash}"
  printf 'BOT_TOKEN=%s\n' "${bot_token}"
  printf 'BIN_CHANNEL=%s\n' "${bin_channel}"
  printf 'OWNER_ID=%s\n' "${owner_id}"
  printf 'PUBLIC_BASE_URL=http://127.0.0.1:9081\n'
  printf 'HEALTHCHECK_TOKEN=%s\n' "${healthcheck_token}"
  printf 'WEB_SERVER_BIND_ADDRESS=127.0.0.1\n'
  printf 'PORT=9081\n'
  printf 'REQUIRE_LOGIN_PASSWORD=false\n'
} > "${LOCAL_ENV_FILE}"
chmod 0600 "${LOCAL_ENV_FILE}"

python3 -m venv "${SERVICE_ROOT}/.venv"
"${SERVICE_ROOT}/.venv/bin/pip" install --upgrade pip
"${SERVICE_ROOT}/.venv/bin/pip" install -r "${SERVICE_ROOT}/requirements.txt"

echo "Local setup complete. The bot will create its own Telegram tables inside the existing movieworld database."
