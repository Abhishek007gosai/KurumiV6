# Ported from KurumiFileStoreV2 (plugins/useless.py), adapted to the
# merged bot's database.database.Seishiro instance.

from datetime import datetime
from pyrogram import filters
from pyrogram.types import Message

from bot import Bot
from config import BOT_STATS_TEXT
from database.database import Seishiro
from helper_func import admin, get_readable_time

WAIT_MSG = "<b>Working....</b>"


@Bot.on_message(filters.command('stats') & admin)
async def stats(bot: Bot, message: Message):
    now = datetime.now()
    delta = now - bot.uptime
    uptime = get_readable_time(delta.seconds)
    await message.reply(BOT_STATS_TEXT.format(uptime=uptime))


@Bot.on_message(filters.command('users') & filters.private & admin)
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await Seishiro.full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")


@Bot.on_message(filters.private & filters.command('dlt_time') & admin)
async def set_delete_time(client: Bot, message: Message):
    try:
        duration = int(message.command[1])
    except (IndexError, ValueError):
        return await message.reply("<b>Please provide a valid duration in seconds.</b> Usage: /dlt_time {duration}")

    await Seishiro.set_del_timer(duration)
    await message.reply(f"<b>Delete timer has been set to <blockquote>{duration} seconds.</blockquote></b>")


@Bot.on_message(filters.private & filters.command('check_dlt_time') & admin)
async def check_delete_time(client: Bot, message: Message):
    duration = await Seishiro.get_del_timer()
    await message.reply(f"<b><blockquote>Current delete timer is set to {duration} seconds.</blockquote></b>")


@Bot.on_message(filters.command('commands') & filters.private & admin)
async def bcmd(bot: Bot, message: Message):
    from config import CMD_TXT
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("• Cʟᴏsᴇ •", callback_data="close")]])
    await message.reply(text=CMD_TXT, reply_markup=reply_markup, quote=True)
