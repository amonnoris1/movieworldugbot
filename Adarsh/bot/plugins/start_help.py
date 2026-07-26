"""Private, MovieWorld-branded Telegram bot entry points."""

import logging

from pyrogram import filters
from pyrogram.types import Message, ReplyKeyboardRemove

from Adarsh.bot import StreamBot
from Adarsh.utils.database import Database
from Adarsh.vars import Var

logger = logging.getLogger(__name__)
db = Database(Var.DB_CONFIG, "users")


async def register_user(message: Message) -> None:
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id)


@StreamBot.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    await register_user(message)
    await message.reply_text(
        "MovieWorld file test bot is online. Send a test video or file to generate a private permanent link.",
        reply_markup=ReplyKeyboardRemove(),
    )


@StreamBot.on_message(
    filters.private
    & filters.text
    & filters.regex(r"(?i)^(start|help|login|dc|subscribe|ping|status|maintainers)"),
    group=10,
)
async def remove_legacy_keyboard(_, message: Message):
    """Retire the unsupported reply keyboard left by the upstream bot."""
    await message.reply_text(
        "That old menu is no longer used. Tap the command button or send /start, /help, or /about.",
        reply_markup=ReplyKeyboardRemove(),
    )


@StreamBot.on_message(filters.command("help") & filters.private)
async def help_handler(_, message: Message):
    await register_user(message)
    await message.reply_text(
        "Send a test video or file in this private chat. The bot will create a permanent private link for that one file."
    )


@StreamBot.on_message(filters.command("about") & filters.private)
async def about_handler(_, message: Message):
    await register_user(message)
    await message.reply_text(
        "MovieWorld Telegram streaming test service. It is isolated from the public MovieWorld catalogue."
    )
