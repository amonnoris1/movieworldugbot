"""Private, MovieWorld-branded Telegram bot entry points."""

import logging
from urllib.parse import quote_plus, urlencode

from pyrogram import filters
from pyrogram.types import Message

from Adarsh.bot import StreamBot
from Adarsh.utils.database import Database
from Adarsh.utils.file_properties import get_hash, get_name
from Adarsh.vars import Var

logger = logging.getLogger(__name__)
db = Database(Var.DB_CONFIG, "users")


async def register_user(message: Message) -> None:
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id)


def private_watch_url(file_message) -> str:
    query = urlencode(
        {
            "hash": get_hash(file_message),
            "access_token": Var.STREAM_ACCESS_TOKEN,
        }
    )
    return (
        f"{Var.URL}watch/{file_message.id}/"
        f"{quote_plus(get_name(file_message))}?{query}"
    )


@StreamBot.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    await register_user(message)
    payload = message.command[1] if len(message.command) > 1 else ""
    if not payload:
        await message.reply_text(
            "MovieWorld file test bot is online. Send a test video or file to generate a private test link."
        )
        return

    if not payload.isdigit():
        await message.reply_text("That link request is invalid.")
        return

    try:
        file_message = await client.get_messages(Var.BIN_CHANNEL, int(payload))
        if not file_message or not (file_message.video or file_message.document or file_message.audio):
            await message.reply_text("The requested test file is unavailable.")
            return
        await message.reply_text(
            f"Private test link:\n{private_watch_url(file_message)}\n\nDo not share this link."
        )
    except Exception:
        logger.exception("Could not create private test link")
        await message.reply_text("The test file could not be opened. Contact the administrator.")


@StreamBot.on_message(filters.command("help") & filters.private)
async def help_handler(_, message: Message):
    await register_user(message)
    await message.reply_text(
        "Send a test video or file in this private chat. The bot will create a temporary private test link."
    )


@StreamBot.on_message(filters.command("about") & filters.private)
async def about_handler(_, message: Message):
    await register_user(message)
    await message.reply_text(
        "MovieWorld Telegram streaming test service. It is isolated from the public MovieWorld catalogue."
    )
