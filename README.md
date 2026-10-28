# flu-loader

A Telegram bot that downloads media from **Instagram**, **TikTok** and **YouTube Shorts**.
Drop a link in a chat, and the bot replies with the video (or photo carousel) plus the audio track as a separate file with cover art.

Built to keep working when individual download sources break, and to stay closed to anyone you haven't let in.

## Reliability

Every platform goes through a chain of independent sources. If one fails, returns a broken file or hits a rate limit, the bot moves on to the next one.

| Platform | Level 1 | Level 2 | Level 3 |
|---|---|---|---|
| Instagram | Cobalt (self-hosted) | Apify | yt-dlp |
| TikTok / YouTube Shorts | tikwm API | Cobalt (self-hosted) | yt-dlp |

- **Fake file detection.** Responses that are actually HTML error pages or tiny stubs are rejected before they reach Telegram.
- **Carousels.** Albums of any size are split into Telegram media groups of 10, and slides blocked by a CDN are skipped instead of failing the whole post.
- **Audio extraction.** The track is sent separately with an embedded square cover (from the author avatar, the post itself or a video frame).
- **No disk leaks.** Temporary files are removed right after sending, and a background job cleans anything left in `downloads/` older than 30 minutes.
- **Survives restarts.** The SQLite database lives in a mounted volume, and messages older than 60 seconds are ignored, so the bot doesn't flood a chat with a backlog after downtime.

## Security

- **Invite-only access.** The bot does nothing in a chat until it's activated with a one-time key (`/login <key>`). Keys are generated, listed, revoked and restored by the owner only.
- **Group activation by admins only.** In groups, only chat admins can enter a key.
- **Revocable access.** `/timeout <key>` cuts a chat off instantly, `/revive <key>` brings it back. Key history is kept.
- **Owner-only admin commands.** All key management is bound to a single `ADMIN_ID`. Other users' calls are silently ignored.
- **Secrets stay out of the code.** All tokens live in `.env`, which is excluded from both git and the Docker image (`.dockerignore`).
- **Self-hosted Cobalt, not exposed.** Cobalt runs in the same Docker network as the bot and publishes no ports, so it can't be used by anyone else and links don't go through third-party Cobalt instances.
- **Safe output.** User names are HTML-escaped before mentions are built.

## Commands

| Command | Who | What it does |
|---|---|---|
| `/start` | everyone | How to get access |
| `/login <key>` | everyone (admins in groups) | Activate the bot in this chat |
| `/cancel` | everyone | Cancel activation |
| `@all` | activated groups | Mention every member the bot has seen |
| `/newkey [note]` | owner | Generate a one-time key (aliases: `/genkey`, `/nk`, `/gk`) |
| `/keys`, `/deadkeys` | owner | List free/active or revoked keys |
| `/timeout <key>`, `/revive <key>` | owner | Revoke or restore a key (aliases: `/out`, `/rev`) |
| `/ids` | owner | Show user ID, chat ID and chat type |

Any Instagram / TikTok / YouTube Shorts link in an activated chat is downloaded automatically.

## Setup

Requirements: Docker with Docker Compose.

```bash
git clone https://github.com/fsguruu/flu-loader.git
cd flu-loader
cp .env.example .env   # fill in the values
docker compose up -d --build
```

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Token from [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | Your Telegram user ID (the bot owner) |
| `APIFY_API_TOKEN` | Apify token for the Instagram fallback |
| `FFMPEG_PATH` | Path to ffmpeg (`ffmpeg` inside Docker) |
| `BOT_MODE` | `prod` (default) or `local` |

Then send `/newkey` to the bot from the owner account and activate a chat with `/login <key>`.

Logs: `docker compose logs -f telegram-bot`. Update: `git pull && docker compose up -d --build`.

### Local run without Docker

```bash
python -m venv .venv
.venv/Scripts/activate      # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

ffmpeg must be installed. Without the Cobalt container, the first level is skipped and the fallbacks are used.

## Customizing texts

All user-facing texts are in `bot_msgs.py`. With `BOT_MODE=local`, the bot loads `bot_msgs_local.py` instead (not included in the repo), which can override any text and enables extra local-only commands. Missing keys fall back to `bot_msgs.py`.

## Project structure

```
main.py              entry point: bot, middlewares, routers
messages.py          picks the text set by BOT_MODE
bot_msgs.py          user-facing texts
handlers/            commands, activation, link handler
middlewares/         access control, member tracking, stale message filter
services/            per-platform download pipelines, sender, utils, cleanup
services/core/       download engines: Cobalt, Apify, yt-dlp
database/            SQLite access (keys, chat members)
```

## Stack

Python 3.11 · aiogram 3 · yt-dlp · Cobalt · ffmpeg · Pillow · SQLite · Docker
