# Ported from KurumiFileStoreV2 (plugins/banuser.py) as slash-command
# equivalents of the ban_menu/ban_user/unban_user/banned_list buttons
# already in KafkaLinkBotV1's /settings menu. Both operate on the same
# Seishiro.ban_data collection, so state stays consistent either way.

from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot import Bot
from config import OWNER_ID
from database.database import Seishiro
from helper_func import admin

CLOSE_MARKUP = InlineKeyboardMarkup([[InlineKeyboardButton("Cʟᴏsᴇ", callback_data="close")]])


@Bot.on_message(filters.private & filters.command('ban') & admin)
async def add_banuser(client: Client, message: Message):
    pro = await message.reply("⏳ <i>Processing request...</i>", quote=True)
    banned_ids = await Seishiro.get_ban_users()
    admin_ids = await Seishiro.get_all_admins()
    targets = message.text.split()[1:]

    if not targets:
        return await pro.edit(
            "<b>❗ You must provide user ID(s) to ban.</b>\n\n"
            "<b>Usage:</b>\n<code>/ban [user_id]</code> — ban one or more users by ID.",
            reply_markup=CLOSE_MARKUP
        )

    report, success_count = "", 0
    for uid in targets:
        try:
            uid_int = int(uid)
        except ValueError:
            report += f"⚠️ Invalid ID: <code>{uid}</code>\n"
            continue

        if uid_int in admin_ids or uid_int == OWNER_ID:
            report += f"⛔ Skipped admin/owner ID: <code>{uid_int}</code>\n"
            continue

        if uid_int in banned_ids:
            report += f"⚠️ Already banned: <code>{uid_int}</code>\n"
            continue

        await Seishiro.add_ban_user(uid_int)
        report += f"✅ Banned: <code>{uid_int}</code>\n"
        success_count += 1

    if success_count:
        await pro.edit(f"<b>✅ Banned users updated:</b>\n\n{report}", reply_markup=CLOSE_MARKUP)
    else:
        await pro.edit(f"<b>❌ No users were banned.</b>\n\n{report}", reply_markup=CLOSE_MARKUP)


@Bot.on_message(filters.private & filters.command('unban') & admin)
async def delete_banuser(client: Client, message: Message):
    pro = await message.reply("⏳ <i>Processing request...</i>", quote=True)
    banned_ids = await Seishiro.get_ban_users()
    targets = message.text.split()[1:]

    if not targets:
        return await pro.edit(
            "<b>❗ Please provide user ID(s) to unban.</b>\n\n"
            "<code>/unban [user_id]</code> — unban specific user(s)\n"
            "<code>/unban all</code> — remove all banned users",
            reply_markup=CLOSE_MARKUP
        )

    if targets[0].lower() == "all":
        if not banned_ids:
            return await pro.edit("<b>✅ No users in the ban list.</b>", reply_markup=CLOSE_MARKUP)
        for uid in banned_ids:
            await Seishiro.del_ban_user(uid)
        listed = "\n".join(f"✅ Unbanned: <code>{uid}</code>" for uid in banned_ids)
        return await pro.edit(f"<b>🚫 Cleared ban list:</b>\n\n{listed}", reply_markup=CLOSE_MARKUP)

    report = ""
    for uid in targets:
        try:
            uid_int = int(uid)
        except ValueError:
            report += f"⚠️ Invalid ID: <code>{uid}</code>\n"
            continue

        if uid_int in banned_ids:
            await Seishiro.del_ban_user(uid_int)
            report += f"✅ Unbanned: <code>{uid_int}</code>\n"
        else:
            report += f"⚠️ Not in ban list: <code>{uid_int}</code>\n"

    await pro.edit(f"<b>🚫 Unban report:</b>\n\n{report}", reply_markup=CLOSE_MARKUP)


@Bot.on_message(filters.private & filters.command('banlist') & admin)
async def get_banuser_list(client: Client, message: Message):
    pro = await message.reply("⏳ <i>Fetching ban list...</i>", quote=True)
    banned_ids = await Seishiro.get_ban_users()

    if not banned_ids:
        return await pro.edit("<b>✅ No users in the ban list.</b>", reply_markup=CLOSE_MARKUP)

    result = "<b>🚫 Banned Users:</b>\n\n"
    for uid in banned_ids:
        await message.reply_chat_action(ChatAction.TYPING)
        try:
            user = await client.get_users(uid)
            user_link = f'<a href="tg://user?id={uid}">{user.first_name}</a>'
            result += f"• {user_link} — <code>{uid}</code>\n"
        except Exception:
            result += f"• <code>{uid}</code> — <i>could not fetch name</i>\n"

    await pro.edit(result, disable_web_page_preview=True, reply_markup=CLOSE_MARKUP)
