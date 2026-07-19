# Ported from KurumiFileStoreV2 (plugins/link_generator.py +
# plugins/channel_post.py).
#
# These are the ONLY /batch /genlink /custom_batch commands in the bot now
# — the old KafkaLinkBotV1 channel-invite-link versions of those names were
# removed from plugins/settings.py. They're always active (fsub + shortener
# already gate delivery, so no separate bot-mode switch is needed).
# Requires CHANNEL_ID to be set in config.py (the bot must be admin there).

import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
)
from pyrogram.errors import FloodWait

from bot import Bot
from config import CUSTOM_CAPTION, PROTECT_CONTENT
from database.database import Seishiro
from helper_func import encode, get_message_id, admin
from plugins.autodelete import schedule_delete

# Commands the generic "store this message" catch-all below must NOT
# swallow — keep this in sync with every @Bot.on_message(filters.command(...))
# handler across the whole bot.
RESERVED_COMMANDS = [
    'start', 'commands', 'users', 'stats',
    'broadcast', 'pbroadcast', 'dbroadcast',
    'genlink', 'batch', 'custom_batch',
    'dlt_time', 'check_dlt_time',
    'ban', 'unban', 'banlist',
    'add_admin', 'deladmin', 'del_admin', 'admins',
    'add_chnl', 'del_chnl',
    'settings', 'cancel', 'listchnl', 'fsub_mode',
    'shortener', 'caption',
    'addpremium', 'delpremium', 'premiumusers',
]


@Bot.on_message(filters.private & admin & filters.command('batch'))
async def fbatch(client: Client, message: Message):
    if not client.db_channel:
        return await message.reply("<b>CHANNEL_ID is not configured — file-store is disabled.</b>")

    while True:
        try:
            first_message = await client.ask(
                text="Forward the First Message from the DB Channel (with quotes)..\n\nor send the DB Channel post link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except asyncio.TimeoutError:
            return
        f_msg_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        await first_message.reply("❌ Error\n\nThis forwarded post is not from the DB Channel, or the link isn't from the DB Channel.", quote=True)

    while True:
        try:
            second_message = await client.ask(
                text="Forward the Last Message from the DB Channel (with quotes)..\nor send the DB Channel post link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except asyncio.TimeoutError:
            return
        s_msg_id = await get_message_id(client, second_message)
        if s_msg_id:
            break
        await second_message.reply("❌ Error\n\nThis forwarded post is not from the DB Channel, or the link isn't from the DB Channel.", quote=True)

    string = f"get-{f_msg_id * abs(client.db_channel.id)}-{s_msg_id * abs(client.db_channel.id)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Sʜᴀʀᴇ ᴜʀʟ", url=f'https://telegram.me/share/url?url={link}')]])
    # "batch link" is auto-detected by the global cleaner's share-link
    # heuristic, so this gets the 5-minute schedule automatically.
    await second_message.reply_text(f"<b>Here is your batch link</b>\n\n{link}", quote=True, reply_markup=reply_markup)


@Bot.on_message(filters.private & admin & filters.command('genlink'))
async def filelink(client: Client, message: Message):
    if not client.db_channel:
        return await message.reply("<b>CHANNEL_ID is not configured — file-store is disabled.</b>")

    while True:
        try:
            channel_message = await client.ask(
                text="Forward a Message from the DB Channel (with quotes)..\nor send the DB Channel post link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except asyncio.TimeoutError:
            return
        msg_id = await get_message_id(client, channel_message)
        if msg_id:
            break
        await channel_message.reply("❌ Error\n\nThis forwarded post is not from the DB Channel, or the link isn't from the DB Channel.", quote=True)

    base64_string = await encode(f"get-{msg_id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Sʜᴀʀᴇ ᴜʀʟ", url=f'https://telegram.me/share/url?url={link}')]])
    # "your link" is auto-detected by the global cleaner's share-link
    # heuristic, so this gets the 5-minute schedule automatically.
    await channel_message.reply_text(f"<b>Here is your link</b>\n\n{link}", quote=True, reply_markup=reply_markup)


@Bot.on_message(filters.private & admin & filters.command("custom_batch"))
async def custom_fbatch(client: Client, message: Message):
    if not client.db_channel:
        return await message.reply("<b>CHANNEL_ID is not configured — file-store is disabled.</b>")

    collected = []
    stop_keyboard = ReplyKeyboardMarkup([["STOP"]], resize_keyboard=True)

    await message.reply("Send all messages you want to include in the batch.\n\nPress STOP when you're done.", reply_markup=stop_keyboard)

    while True:
        try:
            user_msg = await client.ask(chat_id=message.chat.id, text="Waiting for files/messages...\nPress STOP to finish.", timeout=60)
        except asyncio.TimeoutError:
            break

        if user_msg.text and user_msg.text.strip().upper() == "STOP":
            break

        try:
            sent = await user_msg.copy(client.db_channel.id, disable_notification=True)
            collected.append(sent.id)
        except Exception as e:
            await message.reply(f"❌ Failed to store a message:\n<code>{e}</code>")
            continue

    await message.reply("✅ Batch collection complete.", reply_markup=ReplyKeyboardRemove())

    if not collected:
        return await message.reply("❌ No messages were added to the batch.")

    start_id = collected[0] * abs(client.db_channel.id)
    end_id = collected[-1] * abs(client.db_channel.id)
    base64_string = await encode(f"get-{start_id}-{end_id}")
    link = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Sʜᴀʀᴇ ᴜʀʟ", url=f'https://telegram.me/share/url?url={link}')]])
    # "batch link" is auto-detected by the global cleaner's share-link
    # heuristic, so this gets the 5-minute schedule automatically.
    await message.reply(f"<b>Here is your custom batch link:</b>\n\n{link}", reply_markup=reply_markup)


@Bot.on_message(filters.private & admin & ~filters.command(RESERVED_COMMANDS))
async def channel_post(client: Client, message: Message):
    """Auto file-store: any other private message an admin sends is
    copied into the DB Channel and a shareable link is generated."""
    if not client.db_channel:
        return  # silently ignore if file-store isn't configured

    reply_text = await message.reply_text("Please wait...!", quote=True)
    try:
        post_message = await message.copy(chat_id=client.db_channel.id, disable_notification=True)
    except FloodWait as e:
        await asyncio.sleep(e.x)
        post_message = await message.copy(chat_id=client.db_channel.id, disable_notification=True)
    except Exception as e:
        print(e)
        return await reply_text.edit_text("Something went wrong..!")

    converted_id = post_message.id * abs(client.db_channel.id)
    base64_string = await encode(f"get-{converted_id}")
    link = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Sʜᴀʀᴇ ᴜʀʟ", url=f'https://telegram.me/share/url?url={link}')]])
    await reply_text.edit(
        f"<b>Here is your link</b>\n\n{link}",
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
    # reply_text was originally sent as a plain "Please wait...!" placeholder
    # (auto-deletes in 1h by default) — now that it's been edited into the
    # actual share link, put it on the 5-minute share-link schedule instead.
    schedule_delete(client, reply_text, 300)
