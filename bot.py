import asyncio
import sys
from datetime import datetime

# pyromod patches Client with .ask()/.listen() — required by:
#   - plugins/settings.py  (ban_user / unban_user use client.listen)
#   - plugins/filestore.py (link_generator / batch use client.ask)
import pyromod.listen

from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiohttp import web

from config import *
from plugins import web_server
from plugins.autodelete import enable_global_auto_delete

name = """
Combined FileStore + LinkShare Bot
(merged from KurumiFileStoreV2 + KafkaLinkBotV1)
"""


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={"root": "plugins"},
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN,
        )
        self.LOGGER = LOGGER

    async def start(self, *args, **kwargs):
        await super().start()
        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()

        # ---- File-store DB channel (KurumiFileStoreV2 feature) ----
        # Only required if you plan to use /filelink, /fbatch, /customfbatch.
        self.db_channel = None
        if CHANNEL_ID:
            try:
                db_channel = await self.get_chat(CHANNEL_ID)
                self.db_channel = db_channel
                test = await self.send_message(chat_id=db_channel.id, text="Test Message")
                await test.delete()
                self.LOGGER(__name__).info(f"File-store DB channel OK: {db_channel.title}")
            except Exception as e:
                self.LOGGER(__name__).warning(e)
                self.LOGGER(__name__).warning(
                    f"Make sure the bot is Admin in the DB Channel and CHANNEL_ID is correct. "
                    f"Current Value: {CHANNEL_ID}. /filelink, /fbatch and /customfbatch will not work."
                )
        else:
            self.LOGGER(__name__).info(
                "CHANNEL_ID not set — file-store commands (/filelink, /fbatch, /customfbatch) are disabled."
            )

        # ---- Global auto-cleaner ----
        # Every message the bot sends (start message, command replies, admin
        # panel, broadcasts, etc.) is auto-deleted 1 hour after it's sent.
        # Share/invite-link messages are auto-deleted after 5 minutes instead.
        # Anything sent into db_channel/DATABASE_CHANNEL is never touched.
        enable_global_auto_delete(self)

        # ---- Pre-resolve fsub/link-share channels (KafkaLinkBotV1 feature) ----
        try:
            from database.database import Seishiro

            self.LOGGER(__name__).info("=" * 60)
            self.LOGGER(__name__).info("STARTING CHANNEL PEER RESOLUTION...")
            self.LOGGER(__name__).info("=" * 60)

            channels = await Seishiro.get_channels()

            if channels:
                self.LOGGER(__name__).info(f"Found {len(channels)} channel(s) in database")
                resolved_count = 0
                failed_count = 0

                for channel_id in channels:
                    try:
                        chat = await self.get_chat(channel_id)
                        resolved_count += 1
                        self.LOGGER(__name__).info(
                            f"✓ [{resolved_count}/{len(channels)}] Resolved: {channel_id} ({chat.title})"
                        )
                    except Exception as e:
                        failed_count += 1
                        self.LOGGER(__name__).warning(
                            f"✗ [{resolved_count + failed_count}/{len(channels)}] Failed: {channel_id} - {e}"
                        )

                self.LOGGER(__name__).info(
                    f"PEER RESOLUTION COMPLETE: {resolved_count} success, {failed_count} failed"
                )
            else:
                self.LOGGER(__name__).info("No channels found in database. Skipping peer resolution.")

        except Exception as e:
            self.LOGGER(__name__).error(f"Error during channel pre-resolution: {e}")
            self.LOGGER(__name__).warning("Bot will continue, but may encounter PeerIdInvalid errors")

        # ---- Restart notification ----
        if DATABASE_CHANNEL:
            try:
                await self.send_message(
                    chat_id=DATABASE_CHANNEL,
                    text="<b>Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ ✅</b>",
                )
            except Exception as e:
                self.LOGGER(__name__).warning(f"Failed to send restart message in {DATABASE_CHANNEL}: {e}")
        elif OWNER_ID:
            try:
                await self.send_message(OWNER_ID, text="<b><blockquote>Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ</blockquote></b>")
            except Exception:
                pass

        self.set_parse_mode(ParseMode.HTML)
        self.username = usr_bot_me.username
        self.LOGGER(__name__).info(f"Bot Running..! @{self.username}")
        self.LOGGER(__name__).info(name)

        # ---- Web server (keep-alive endpoint) ----
        try:
            app = web.AppRunner(await web_server())
            await app.setup()
            bind_address = "0.0.0.0"
            await web.TCPSite(app, bind_address, PORT).start()
            self.LOGGER(__name__).info(f"Web server started on {bind_address}:{PORT}")
        except Exception as e:
            self.LOGGER(__name__).error(f"Failed to start web server: {e}")

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        self.LOGGER(__name__).info("Bot is now running.")
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            self.LOGGER(__name__).info("Shutting down...")
        finally:
            loop.run_until_complete(self.stop())
