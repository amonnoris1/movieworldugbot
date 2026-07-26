# (c) adarsh-goel
import os
from os import getenv, environ
from dotenv import load_dotenv



load_dotenv()


def _required(name: str) -> str:
    value = getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _enabled(name: str, default: str = "false") -> bool:
    return getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


class Var(object):
    MULTI_CLIENT = False
    API_ID = int(_required('API_ID'))
    API_HASH = _required('API_HASH')
    BOT_TOKEN = _required('BOT_TOKEN')
    name = str(getenv('SESSION_NAME', 'filetolinkbot'))
    SLEEP_THRESHOLD = int(getenv('SLEEP_THRESHOLD', '60'))
    WORKERS = int(getenv('WORKERS', '4'))
    BIN_CHANNEL = int(_required('BIN_CHANNEL'))
    PORT = int(getenv('PORT', 9080))
    # Keep the service private; Nginx is the only public entry point.
    BIND_ADRESS = str(getenv('WEB_SERVER_BIND_ADDRESS', '127.0.0.1'))
    PING_INTERVAL = int(environ.get("PING_INTERVAL", "1200"))
    OWNER_ID = set(int(x) for x in os.environ.get("OWNER_ID", "").split())  
    OWNER_USERNAME = str(getenv('OWNER_USERNAME', ''))
    # Public HTTPS address handled by Nginx/Cloudflare, never the raw bot port.
    PUBLIC_BASE_URL = _required('PUBLIC_BASE_URL').rstrip('/')
    URL = f"{PUBLIC_BASE_URL}/"
    # This protects the test stream endpoints. It must remain server-side.
    STREAM_ACCESS_TOKEN = _required('STREAM_ACCESS_TOKEN')
    HEALTHCHECK_TOKEN = _required('HEALTHCHECK_TOKEN')
    DB_HOST = _required('DB_HOST')
    DB_PORT = int(getenv('DB_PORT', '3306'))
    DB_DATABASE = _required('DB_DATABASE')
    DB_USERNAME = _required('DB_USERNAME')
    DB_PASSWORD = _required('DB_PASSWORD')
    DB_CONFIG = {
        'host': DB_HOST,
        'port': DB_PORT,
        'user': DB_USERNAME,
        'password': DB_PASSWORD,
        'db': DB_DATABASE,
    }
    UPDATES_CHANNEL = getenv('UPDATES_CHANNEL')
    REQUIRE_LOGIN_PASSWORD = _enabled('REQUIRE_LOGIN_PASSWORD')
    BANNED_CHANNELS = list(set(int(x) for x in str(getenv("BANNED_CHANNELS", "")).split()))
