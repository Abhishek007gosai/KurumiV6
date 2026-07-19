import os
import sys

from pyrogram import Client, filters
from config import OWNER_ID


@Client.on_message(filters.command("restart") & filters.user(OWNER_ID))
async def restart_bot(client, message):
    msg = await message.reply_text("🔄 Restarting...")

    try:
        await msg.edit_text("♻️ Bot is restarting...")
    except:
        pass

    os.execl(sys.executable, sys.executable, *sys.argv)
