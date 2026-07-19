# Ported from KurumiFileStoreV2 (plugins/broadcast.py), adapted to the
# merged bot's database.database.Seishiro instance.

import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from pyrogram.types import Message

from bot import Bot
from database.database import Seishiro
from helper_func import admin


@Bot.on_message(filters.private & filters.command('pbroadcast') & admin)
async def send_pin_text(client: Bot, message: Message):
    if not message.reply_to_message:
        msg = await message.reply("Reply to a message to broadcast and pin it.")
        await asyncio.sleep(8)
        return await msg.delete()

    query = await Seishiro.full_userbase()
    broadcast_msg = message.reply_to_message
    total = successful = blocked = deleted = unsuccessful = 0

    pls_wait = await message.reply("<i>Broadcast processing....</i>")
    for chat_id in query:
        try:
            sent_msg = await broadcast_msg.copy(chat_id)
            await client.pin_chat_message(chat_id=chat_id, message_id=sent_msg.id, both_sides=True)
            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)
            sent_msg = await broadcast_msg.copy(chat_id)
            await client.pin_chat_message(chat_id=chat_id, message_id=sent_msg.id, both_sides=True)
            successful += 1
        except UserIsBlocked:
            await Seishiro.del_user(chat_id)
            blocked += 1
        except InputUserDeactivated:
            await Seishiro.del_user(chat_id)
            deleted += 1
        except Exception as e:
            print(f"Failed to send or pin message to {chat_id}: {e}")
            unsuccessful += 1
        total += 1

    status = (
        f"<b><u>Broadcast completed</u></b>\n\n"
        f"Total Users: <code>{total}</code>\n"
        f"Successful: <code>{successful}</code>\n"
        f"Blocked Users: <code>{blocked}</code>\n"
        f"Deleted Accounts: <code>{deleted}</code>\n"
        f"Unsuccessful: <code>{unsuccessful}</code>"
    )
    await pls_wait.edit(status)


# NOTE: a plain /broadcast (reply-to-message, no pin, no auto-delete) is
# already implemented in plugins/start.py (broadcast_handler, ported from
# KafkaLinkBotV1) — intentionally not duplicated here to avoid two
# handlers registering the same command.


@Bot.on_message(filters.private & filters.command('dbroadcast') & admin)
async def delete_broadcast(client: Bot, message: Message):
    if not message.reply_to_message:
        await message.reply("Please reply to a message to broadcast it with auto-delete.")
        return

    try:
        duration = int(message.command[1])
    except (IndexError, ValueError):
        return await message.reply("<b>Please use a valid duration in seconds.</b> Usage: /dbroadcast {duration}")

    query = await Seishiro.full_userbase()
    broadcast_msg = message.reply_to_message
    total = successful = blocked = deleted = unsuccessful = 0

    pls_wait = await message.reply("<i>Broadcast with auto-delete processing....</i>")
    for chat_id in query:
        try:
            sent_msg = await broadcast_msg.copy(chat_id)
            await asyncio.sleep(duration)
            await sent_msg.delete()
            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)
            sent_msg = await broadcast_msg.copy(chat_id)
            await asyncio.sleep(duration)
            await sent_msg.delete()
            successful += 1
        except UserIsBlocked:
            await Seishiro.del_user(chat_id)
            blocked += 1
        except InputUserDeactivated:
            await Seishiro.del_user(chat_id)
            deleted += 1
        except Exception:
            unsuccessful += 1
        total += 1

    status = (
        f"<b><u>Broadcasting with auto-delete</u></b>\n\n"
        f"Total Users: <code>{total}</code>\n"
        f"Successful: <code>{successful}</code>\n"
        f"Blocked Users: <code>{blocked}</code>\n"
        f"Deleted Accounts: <code>{deleted}</code>\n"
        f"Unsuccessful: <code>{unsuccessful}</code>"
    )
    await pls_wait.edit(status)
