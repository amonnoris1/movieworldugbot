"""Private-file intake for the isolated MovieWorld Telegram streaming test."""

import asyncio
import logging
import os
from asyncio import TimeoutError
from urllib.parse import quote_plus

from pyrogram import Client, enums, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from Adarsh.bot import StreamBot
from Adarsh.utils.database import Database
from Adarsh.utils.file_properties import get_hash, get_media_file_size, get_name
from Adarsh.utils.human_readable import humanbytes
from Adarsh.vars import Var

logger = logging.getLogger(__name__)
db = Database(Var.DB_CONFIG, "users")
password_db = Database(Var.DB_CONFIG, "passwords")
MY_PASS = os.environ.get("MY_PASS") if Var.REQUIRE_LOGIN_PASSWORD else None


def file_links(message) -> tuple[str, str]:
    query = f"hash={get_hash(message)}&access_token={quote_plus(Var.STREAM_ACCESS_TOKEN)}"
    filename = quote_plus(get_name(message))
    watch_url = f"{Var.URL}watch/{message.id}/{filename}?{query}"
    download_url = f"{Var.URL}{message.id}/{filename}?{query}"
    return watch_url, download_url


@StreamBot.on_message(filters.command("login") & filters.private, group=4)
async def login_handler(client: Client, message: Message):
    if not MY_PASS:
        await message.reply_text("Password login is not enabled for this test bot.")
        return
    prompt = await message.reply_text("Send the access password, or /cancel to stop.")
    try:
        response = await client.listen(message.chat.id, filters.text, timeout=90)
    except TimeoutError:
        await prompt.edit("Timed out. Use /login to try again.")
        return
    if response.text == "/cancel":
        await prompt.edit("Login cancelled.")
    elif response.text == MY_PASS:
        # Store only the verified Telegram ID, never the shared password.
        await password_db.add_user_pass(message.chat.id)
        await prompt.edit("Login successful.")
    else:
        await prompt.edit("Incorrect password.")


@StreamBot.on_message(
    filters.private & (filters.document | filters.video | filters.audio | filters.photo),
    group=4,
)
async def private_receive_handler(client: Client, message: Message):
    if MY_PASS and not await password_db.get_user_pass(message.chat.id):
        await message.reply_text("Log in first with /login.")
        return

    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id)

    try:
        # The bot must be a Telegram administrator in this private channel.
        await client.resolve_peer(Var.BIN_CHANNEL)
        stored_message = await message.forward(chat_id=Var.BIN_CHANNEL)
        watch_url, download_url = file_links(stored_message)
        name = get_name(stored_message) or "test file"
        size = humanbytes(get_media_file_size(message))
        await message.reply_text(
            f"Private test link created.\n\nFile: {name}\nSize: {size}\n\n"
            "Do not share these links; they are not production MovieWorld links.",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("Watch test", url=watch_url),
                    InlineKeyboardButton("Download test", url=download_url),
                ]]
            ),
        )
    except FloodWait as wait:
        logger.warning("Telegram flood wait: %s seconds", wait.value)
        await asyncio.sleep(wait.value)
        await message.reply_text("Telegram asked the bot to slow down. Please try again shortly.")
    except Exception:
        logger.exception("Could not create a private test link")
        await message.reply_text("The file could not be processed. Contact the administrator.")
