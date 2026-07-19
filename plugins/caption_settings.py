"""
Caption Settings — admin-manageable from /settings → Caption Settings.

OFF (default): delivered files keep whatever caption they already have in
the DB channel (untouched).
ON: every delivered document caption is replaced with the custom text,
which can use {filename} and {previouscaption} placeholders.
"""
import asyncio
from pyrogram import filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot import Bot
from config import OWNER_ID
from database.database import Seishiro


async def is_admin_user(user_id: int) -> bool:
    return user_id == OWNER_ID or await Seishiro.is_admin(user_id)


def _fmt_menu(c: dict) -> str:
    return (
        "<b>📝 Caption Settings</b>\n\n"
        f"<b>Status:</b> {'✅ Custom caption ON' if c.get('enabled') else '❌ OFF — using each file’s own caption'}\n"
        f"<b>Custom caption text:</b>\n<code>{c.get('text')}</code>\n\n"
        "Placeholders you can use: <code>{filename}</code>, <code>{previouscaption}</code>\n\n"
        "Tap a button below to edit."
    )


def _menu_markup(c: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Tᴜʀɴ ᴏꜰꜰ (ᴜsᴇ ᴅᴇꜰᴀᴜʟᴛ ᴄᴀᴘᴛɪᴏɴ)" if c.get("enabled") else "Tᴜʀɴ ᴏɴ (ᴜsᴇ ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ)",
            callback_data="cap_toggle_enabled")],
        [InlineKeyboardButton("Sᴇᴛ ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ ᴛᴇxᴛ", callback_data="cap_set_text")],
        [InlineKeyboardButton("« Bᴀᴄᴋ", callback_data="settings_main")],
    ])


@Bot.on_message(filters.command("caption") & filters.private)
async def caption_command(client: Bot, message: Message):
    if not await is_admin_user(message.from_user.id):
        return await message.reply("Sᴏʀʀʏ... ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ")
    c = await Seishiro.get_caption_settings()
    await message.reply(_fmt_menu(c), reply_markup=_menu_markup(c))


@Bot.on_callback_query(filters.regex("^cap_") | filters.regex("^caption_menu$"), group=3)
async def caption_settings_callback(client: Bot, cq: CallbackQuery):
    if not await is_admin_user(cq.from_user.id):
        return await cq.answer("You're not an admin.", show_alert=True)

    data = cq.data
    c = await Seishiro.get_caption_settings()

    if data == "caption_menu":
        return await cq.message.edit_text(_fmt_menu(c), reply_markup=_menu_markup(c))

    if data == "cap_toggle_enabled":
        await Seishiro.update_caption_settings(enabled=not c.get("enabled"))
        c = await Seishiro.get_caption_settings()
        await cq.answer(f"Custom caption {'enabled' if c['enabled'] else 'disabled'}.")
        return await cq.message.edit_text(_fmt_menu(c), reply_markup=_menu_markup(c))

    if data == "cap_set_text":
        await cq.answer()
        try:
            reply = await client.ask(
                chat_id=cq.from_user.id,
                text=(
                    "Send the new <b>custom caption text</b>.\n\n"
                    "Placeholders: <code>{filename}</code>, <code>{previouscaption}</code>\n\n"
                    "Send /cancel to abort."
                ),
                timeout=120,
            )
        except asyncio.TimeoutError:
            return
        if reply.text and reply.text.strip() == "/cancel":
            await reply.reply("Cancelled.")
        else:
            await Seishiro.update_caption_settings(text=reply.text)
            await reply.reply("✅ Saved.")
        c = await Seishiro.get_caption_settings()
        return await client.send_message(chat_id=cq.from_user.id, text=_fmt_menu(c), reply_markup=_menu_markup(c))
