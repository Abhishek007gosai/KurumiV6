"""
Premium / Pro users — ported from KurumiFileStoreV2 (Yato branch)
plugins/pro_users.py, adapted to Seishiro (this bot's db instance).

Owner can grant a user premium access for a duration (or permanently),
which makes them skip the shortener verification gate entirely — same
idea as ForYou's `present_premium` check, generalized here.
"""
import re
from datetime import datetime, timedelta

from pyrogram import filters
from pyrogram.types import Message

from bot import Bot
from config import OWNER_ID
from database.database import Seishiro


def parse_duration(duration_str: str):
    duration_str = duration_str.lower().strip()
    match = re.match(r'^(\d+)\s*(day|days|week|weeks|month|months|year|years)$', duration_str)
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2).rstrip('s')
    if unit == 'day':
        return timedelta(days=amount)
    elif unit == 'week':
        return timedelta(weeks=amount)
    elif unit == 'month':
        return timedelta(days=amount * 30)
    elif unit == 'year':
        return timedelta(days=amount * 365)
    return None


@Bot.on_message(filters.command('addpremium') & filters.private)
async def add_premium_command(client: Bot, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("Only Owner can use this command...!")

    usage = (
        "<b>Usage:</b>\n/addpremium <userid> [duration]\n\n"
        "<b>Examples:</b>\n"
        "• /addpremium 123456 1 day\n"
        "• /addpremium 123456 2 weeks\n"
        "• /addpremium 123456 1 month\n"
        "• /addpremium 123456 1 year\n"
        "• /addpremium 123456 (for permanent premium — skips the shortener forever)"
    )

    parts = message.command[1:]
    if not parts:
        return await message.reply_text(usage)

    try:
        user_id_to_add = int(parts[0])
    except ValueError:
        return await message.reply_text("Invalid user ID. Please check again...!")

    try:
        user = await client.get_users(user_id_to_add)
        user_name = user.first_name + (" " + user.last_name if user.last_name else "")
    except Exception as e:
        return await message.reply_text(f"Error fetching user information: {e}")

    duration_str = " ".join(parts[1:]) if len(parts) > 1 else None
    expiry_date = None
    duration_text = "permanently"

    if duration_str:
        duration = parse_duration(duration_str)
        if not duration:
            return await message.reply_text(f"Invalid duration format.\n\n{usage}")
        expiry_date = datetime.utcnow() + duration
        duration_text = f"until {expiry_date.strftime('%Y-%m-%d %H:%M:%S')} UTC"

    if not await Seishiro.is_pro(user_id_to_add):
        await Seishiro.add_pro(user_id_to_add, expiry_date)
        await message.reply_text(f"<b>User {user_name} - {user_id_to_add} is now premium {duration_text}!</b>\n\nThey now skip the shortener verification.")
        try:
            notify_msg = "<b>🎉 Congratulations! You've been given premium access — you no longer need to complete the shortener"
            notify_msg += f" until {expiry_date.strftime('%Y-%m-%d %H:%M:%S')} UTC.</b>" if expiry_date else " (permanently).</b>"
            await client.send_message(user_id_to_add, notify_msg)
        except Exception as e:
            await message.reply_text(f"Failed to notify the user: {e}")
    else:
        current_expiry = await Seishiro.get_expiry_date(user_id_to_add)
        if current_expiry:
            await message.reply_text(f"<b>User {user_name} - {user_id_to_add} is already premium until {current_expiry.strftime('%Y-%m-%d %H:%M:%S')} UTC.</b>")
        else:
            await message.reply_text(f"<b>User {user_name} - {user_id_to_add} is already a permanent premium user.</b>")


@Bot.on_message(filters.command('delpremium') & filters.private)
async def del_premium_command(client: Bot, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("Only Owner can use this command...!")

    if len(message.command) != 2:
        return await message.reply_text("<b>Usage:</b> /delpremium <userid>")

    try:
        user_id_to_remove = int(message.command[1])
    except ValueError:
        return await message.reply_text("Invalid user ID. Please check again...!")

    try:
        user = await client.get_users(user_id_to_remove)
        user_name = user.first_name + (" " + user.last_name if user.last_name else "")
    except Exception as e:
        return await message.reply_text(f"Error fetching user information: {e}")

    if await Seishiro.is_pro(user_id_to_remove):
        await Seishiro.remove_pro(user_id_to_remove)
        await message.reply_text(f"<b>User {user_name} - {user_id_to_remove} has been removed from premium...!</b>")
        try:
            await client.send_message(user_id_to_remove, "<b>Your premium membership has ended — you'll need to pass the shortener verification again.</b>")
        except Exception:
            pass
    else:
        await message.reply_text(f"<b>User {user_name} - {user_id_to_remove} is not premium or was not found.</b>")


@Bot.on_message(filters.command('premiumusers') & filters.private)
async def list_premium_command(client: Bot, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("Only Owner can use this command...!")

    pro_user_ids = await Seishiro.get_pros_list()
    formatted = []
    for user_id in pro_user_ids:
        try:
            user = await client.get_users(user_id)
            full_name = user.first_name + (" " + user.last_name if user.last_name else "")
            username = f"@{user.username}" if user.username else "No Username"
            expiry_date = await Seishiro.get_expiry_date(user_id)
            status = f"(Expires: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')} UTC)" if expiry_date else "(Permanent)"
            formatted.append(f"{full_name} - {username} {status}")
        except Exception:
            continue

    if formatted:
        await message.reply_text("<b>📊 Premium Users List:</b>\n\n" + "\n".join(formatted), disable_web_page_preview=True)
    else:
        await message.reply_text("<b>No premium users found.</b>")
