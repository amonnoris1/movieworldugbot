# (c) adarsh-goel
import os
import sys
import glob
import asyncio
import logging
import importlib
from pathlib import Path

# Python 3.14 no longer creates a main-thread event loop implicitly. Pyrogram's
# synchronous compatibility layer still expects one during import.
asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import idle, utils as pyrogram_utils
from pyrogram.types import BotCommand
from .bot import StreamBot
from .vars import Var
from aiohttp import web
from .server import web_server
from Adarsh.bot.clients import initialize_clients

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

# Pyrogram 2.0.106 still limits channel peer IDs to the old signed 32-bit
# range. Telegram now issues larger channel IDs; accept the current channel
# range without changing the message or authentication protocol.
pyrogram_utils.MIN_CHANNEL_ID = -2_000_000_000_000

ppath = "Adarsh/bot/plugins/*.py"
files = glob.glob(ppath)
loop = asyncio.get_event_loop()


def register_plugins():
    """Register every command handler before Telegram polling begins."""
    print('--------------------------- Importing ---------------------------')
    for name in files:
        with open(name) as a:
            patt = Path(a.name)
            plugin_name = patt.stem.replace(".py", "")
            plugins_dir = Path(f"Adarsh/bot/plugins/{plugin_name}.py")
            import_path = ".plugins.{}".format(plugin_name)
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            load = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(load)
            sys.modules["Adarsh.bot.plugins." + plugin_name] = load
            print("Imported => " + plugin_name)


async def configure_bot_commands():
    """Publish only commands that this maintained bot actually handles."""
    commands = [
        BotCommand("start", "Start the MovieWorld file bot"),
        BotCommand("help", "Learn how private file links work"),
        BotCommand("about", "About this test service"),
    ]
    if Var.REQUIRE_LOGIN_PASSWORD:
        commands.append(BotCommand("login", "Private test login"))
    await StreamBot.set_bot_commands(commands)


async def start_services():
    register_plugins()
    print('\n')
    print('------------------- Initializing Telegram Bot -------------------')
    await StreamBot.start()
    bot_info = await StreamBot.get_me()
    StreamBot.username = bot_info.username
    await configure_bot_commands()
    try:
        await StreamBot.get_chat(Var.BIN_CHANNEL)
        logging.info("Configured Telegram storage channel is reachable")
    except Exception:
        logging.exception("Configured Telegram storage channel could not be resolved")
    print("------------------------------ DONE ------------------------------")
    print()
    print("---------------------- Initializing Clients ----------------------")
    await initialize_clients()
    print("------------------------------ DONE ------------------------------")
    print('\n')
    print('-------------------- Initalizing Web Server -------------------------')
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = Var.BIND_ADRESS
    await web.TCPSite(app, bind_address, Var.PORT).start()
    print('----------------------------- DONE ---------------------------------------------------------------------')
    print('\n')
    print('MovieWorld Telegram test service started on {}:{}'.format(bind_address, Var.PORT))
    await idle()

if __name__ == '__main__':
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        logging.info('----------------------- Service Stopped -----------------------')
