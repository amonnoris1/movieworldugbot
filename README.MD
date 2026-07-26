# MovieWorld Telegram File-to-Link Bot

A security-hardened, MySQL-backed adaptation of the original
[FileStreamBot-pro](https://github.com/adarsh-goel/FileStreamBot-pro) project.
It accepts a media file in a private Telegram chat, forwards it to a private
Telegram storage channel, and replies with Watch and Download test links.

This repository contains the improvements made for MovieWorld:

- MySQL replaces MongoDB for registered users and broadcast recipients.
- Secrets are read from a protected environment file; none belong in Git.
- The Python service binds to `127.0.0.1` only, with Nginx handling public HTTPS.
- File and health routes require server-side secrets and return `404` when
  authentication fails, rather than confirming guessed links.
- HTML player pages use local templates and escaped values.
- The service works with recent Python releases and Telegram channel IDs larger
  than Pyrogram's older default range.
- A systemd unit and Nginx templates are supplied for a least-privilege Linux
  deployment.

> **Status: private proof of concept.** This is not yet MovieWorld's public
> streaming pipeline. It proxies every byte from Telegram through the VPS,
> does not transcode to HLS, and does not apply per-customer entitlement checks.
> Use it only with media you own or are authorised to distribute.

## Contents

- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Security model](#security-model)
- [Installation](#installation)
- [Configuration](#configuration)
- [Telegram setup](#telegram-setup)
- [Nginx and HTTPS](#nginx-and-https)
- [Running as a service](#running-as-a-service)
- [Using the bot](#using-the-bot)
- [Testing](#testing)
- [Operations](#operations)
- [Known limitations and roadmap](#known-limitations-and-roadmap)
- [Credits and licence](#credits-and-licence)

## How it works

```text
Authorised uploader
        |
        v
Telegram bot (private chat) -----> private Telegram storage channel
        |                                      |
        | Watch / Download link                | file remains in Telegram
        v                                      v
Browser -> HTTPS Nginx -> localhost Python service -> Telegram byte stream
```

The web service does not store a second copy of the video. On every playback
or download request it reads the file from the configured Telegram channel and
streams it through the server to the browser.

## Requirements

- Linux VPS running systemd
- Python 3.11 or newer (tested with modern Python; use a virtual environment)
- MySQL 8+ or MariaDB 10.6+
- Nginx and a DNS name with a valid HTTPS certificate
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Telegram `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org)
- A private Telegram channel where the bot is an administrator

Do not point public DNS directly at the Python port. The process should only
listen on the loopback address and Nginx should be the public entry point.

## Security model

### Secrets

Keep `BOT_TOKEN`, `API_HASH`, `STREAM_ACCESS_TOKEN`, `HEALTHCHECK_TOKEN`, and
the MySQL password in a root-owned environment file such as:

```text
/etc/movieworld-telegram-streamer.env
```

Set it to `0600` permissions and make the service account its group owner only
when that account needs to read it. Never commit it, paste it into a frontend
environment file, or show a full link containing an access token in a
screenshot.

Generate unrelated secrets on the server:

```bash
openssl rand -hex 32
```

### Network and process isolation

- `WEB_SERVER_BIND_ADDRESS=127.0.0.1` keeps the Python port off the Internet.
- Nginx terminates TLS and proxies to the local process.
- The supplied systemd unit uses a dedicated unprivileged user, a restrictive
  umask, private temporary storage, and systemd filesystem protections.
- The MySQL account should have access only to this bot database, from
  `localhost`, with the minimum grants needed for its tables.
- Nginx sends `no-referrer`, `no-store`, `nosniff`, frame blocking, and a
  restrictive Content Security Policy for player pages.

### Current link protection

The proof of concept uses a global stream access token in each generated URL.
It is suitable only for private testing. If that token leaks, it may be reused
against other file URLs. Before serving real customers, replace it with a
unique long random key per video, stored in MySQL, so revoking one leaked link
does not affect every file.

## Installation

The example uses `/opt/movieworld-telegram-streamer`. Adjust paths and the
service user for your VPS.

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx mariadb-server

sudo useradd --system --home /opt/movieworld-telegram-streamer \
  --shell /usr/sbin/nologin movieworldtg
sudo install -d -o movieworldtg -g movieworldtg /opt/movieworld-telegram-streamer

sudo -u movieworldtg git clone https://github.com/amonnoris1/movieworldugbot.git \
  /opt/movieworld-telegram-streamer
sudo -u movieworldtg python3 -m venv /opt/movieworld-telegram-streamer/.venv
sudo -u movieworldtg /opt/movieworld-telegram-streamer/.venv/bin/pip install --upgrade pip
sudo -u movieworldtg /opt/movieworld-telegram-streamer/.venv/bin/pip install \
  -r /opt/movieworld-telegram-streamer/requirements.txt
```

## Configuration

Create a dedicated database and local-only account. Replace the example
password before executing it; do not reuse MovieWorld's main database account.

```sql
CREATE DATABASE movieworld_telegram
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'movieworld_telegram'@'localhost' IDENTIFIED BY 'choose-a-long-unique-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE ON movieworld_telegram.*
  TO 'movieworld_telegram'@'localhost';
FLUSH PRIVILEGES;
```

Create the protected runtime file from the committed template:

```bash
sudo install -o root -g movieworldtg -m 0640 /dev/null \
  /etc/movieworld-telegram-streamer.env
sudoedit /etc/movieworld-telegram-streamer.env
```

Use this structure, replacing every placeholder with your own value:

```dotenv
API_ID=
API_HASH=
BOT_TOKEN=
BIN_CHANNEL=
OWNER_ID=

PUBLIC_BASE_URL=https://telegram.example.com
STREAM_ACCESS_TOKEN=
HEALTHCHECK_TOKEN=

DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=movieworld_telegram
DB_USERNAME=movieworld_telegram
DB_PASSWORD=

WEB_SERVER_BIND_ADDRESS=127.0.0.1
PORT=9080
REQUIRE_LOGIN_PASSWORD=false
```

The committed [.env.example](.env.example) contains the same list. It is safe
to copy, but it intentionally contains no live credentials.

## Telegram setup

1. Create a bot through BotFather and copy its token only into the protected
   environment file.
2. Obtain `API_ID` and `API_HASH` from `my.telegram.org` for the Telegram
   application used by this service.
3. Create a dedicated **private** Telegram channel to hold uploaded media.
4. Add the bot to the channel and promote it to administrator with permission
   to post messages.
5. Determine the channel's numeric ID and set it as `BIN_CHANNEL`.
6. Set `OWNER_ID` to the Telegram numeric ID permitted to use administrative
   commands such as broadcasts.
7. Start a private chat with the bot and send `/start`.

Do not make the storage channel public. Treat its content and message IDs as
private application data.

## Nginx and HTTPS

Copy and adapt the relevant template from [deploy/](deploy/):

- `telegram-movieworldug.acme.nginx` is a minimal HTTP configuration for the
  initial Let's Encrypt webroot challenge.
- `telegram-movieworldug.filmjust.com.nginx` is the HTTPS template for the
  first-level hostname pattern required by some Cloudflare certificates.
- `telegram.movieworldug.filmjust.com.nginx` is an alternative nested-hostname
  template; use it only if your DNS provider's certificate covers that name.

For a new domain, replace the sample hostname in the chosen template, then:

```bash
sudo install -d -m 0755 /var/www/letsencrypt
sudo cp deploy/telegram-movieworldug.acme.nginx /etc/nginx/sites-available/telegram-streamer
sudo ln -s /etc/nginx/sites-available/telegram-streamer /etc/nginx/sites-enabled/telegram-streamer
sudo nginx -t && sudo systemctl reload nginx

sudo certbot certonly --webroot -w /var/www/letsencrypt -d telegram.example.com

# Replace the temporary HTTP configuration with the HTTPS configuration.
sudo nginx -t && sudo systemctl reload nginx
```

If Cloudflare proxies the record, make sure its SSL/TLS mode is **Full
(strict)** after the origin certificate exists. Keep the origin server firewall
limited to the ports you actually need.

## Running as a service

Copy the supplied unit, then reload systemd and start it:

```bash
sudo cp deploy/movieworld-telegram-streamer.service \
  /etc/systemd/system/movieworld-telegram-streamer.service
sudo systemctl daemon-reload
sudo systemctl enable --now movieworld-telegram-streamer
sudo systemctl status movieworld-telegram-streamer --no-pager
```

Useful diagnostics:

```bash
sudo journalctl -u movieworld-telegram-streamer -n 100 --no-pager
sudo journalctl -u movieworld-telegram-streamer -f
sudo nginx -t
```

## Using the bot

Send a video, audio file, document, or photo to the bot in a **private chat**.
The bot forwards it to the private storage channel and responds with buttons:

- **Watch test** opens an HTML5 player page for audio/video.
- **Download test** streams the original file as an attachment.

Available user commands:

- `/start` — register the user and show the basic instructions.
- `/help` — show private-use guidance.
- `/about` — identify the service as an isolated MovieWorld test service.
- `/login` — only relevant when `REQUIRE_LOGIN_PASSWORD=true`; avoid enabling a
  shared password for public use.

Administrative and broadcast commands are restricted by `OWNER_ID`.

## Testing

Run these checks after each configuration or deployment change. Substitute
your actual domain and do not paste token-bearing URLs into public tickets or
screenshots.

```bash
# Service and local protected health check.
sudo systemctl is-active movieworld-telegram-streamer
curl -fsS 'http://127.0.0.1:9080/healthz?token=YOUR_HEALTH_TOKEN'

# Public protected health check.
curl -fsS 'https://telegram.example.com/healthz?token=YOUR_HEALTH_TOKEN'

# Must not reveal service details without a token.
curl -o /dev/null -sS -w '%{http_code}\n' 'https://telegram.example.com/healthz'
# Expected: 404
```

Then upload one rights-cleared test video through the bot and verify:

1. The bot returns Watch and Download buttons.
2. The Watch page responds with `200` and contains a `<video>` element.
3. A byte-range request to the Download URL responds with `206`.
4. A request with an invalid token responds with `404`.

## Operations

### Updating the code

Back up the protected environment file separately; it is intentionally not in
the repository. Then update and restart:

```bash
sudo -u movieworldtg git -C /opt/movieworld-telegram-streamer pull --ff-only
sudo -u movieworldtg /opt/movieworld-telegram-streamer/.venv/bin/pip install \
  -r /opt/movieworld-telegram-streamer/requirements.txt
sudo systemctl restart movieworld-telegram-streamer
sudo systemctl is-active movieworld-telegram-streamer
```

### Rotating a secret

Change the secret only in `/etc/movieworld-telegram-streamer.env`, restart the
service, and test with `curl`. Rotating the current global stream token
invalidates every existing test link. This is another reason to implement
per-file keys before broader use.

### Database backup

Back up only the bot database, and protect the dump because it contains
Telegram IDs:

```bash
mysqldump -u movieworld_telegram -p movieworld_telegram | gzip > telegram-bot.sql.gz
chmod 0600 telegram-bot.sql.gz
```

## Known limitations and roadmap

This service is intentionally not presented as a production content-delivery
platform. Before integrating it with MovieWorld customer accounts, implement:

1. One permanent, random, revocable MySQL access key per uploaded file.
2. MovieWorld account authentication and entitlement checks for playback.
3. Upload moderation, audit logs, rate limits, and abuse controls.
4. HLS packaging/transcoding and a storage/CDN designed for licensed video
   delivery, if traffic grows.
5. Monitoring, backups, incident alerts, and documented recovery procedures.

Never use this software to distribute media without the necessary rights.

## Credits and licence

This work is based on the upstream
[FileStreamBot-pro](https://github.com/adarsh-goel/FileStreamBot-pro) source.
See [LICENSE](LICENSE) for the licence that applies to this repository and
retain upstream notices when redistributing it.
