"""
/listchnl and /fsub_mode — quick command shortcuts requested to sit
alongside /add_admin /deladmin /admins.

Rather than reimplementing channel listing / request-fsub toggling a
second time, these just jump straight into the exact same menu screens
that already exist under /settings -> Fsub Menu (list_fsub_channels /
fsub_settings_menu callbacks in plugins/settings.py), so there's only
ever one source of truth for that logic.
"""
import re

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError, UserNotParticipant
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot import Bot
from config import OWNER_ID
from database.database import Seishiro


async def is_admin_user(user_id: int) -> bool:
    return user_id == OWNER_ID or await Seishiro.is_admin(user_id)


@Bot.on_message(filters.command("add_chnl") & filters.private)
async def add_chnl_command(client: Bot, message: Message):
    if not await is_admin_user(message.from_user.id):
        return await message.reply("Sᴏʀʀʏ... ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ")

    args = message.text.split()[1:]
    if not args:
        return await message.reply(
            "<b>Usᴀɢᴇ:</b> <code>/add_chnl -100XXXXXXXXXX</code>\n\n"
            "Sᴇɴᴅ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ/ɢʀᴏᴜᴘ ID ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴀᴅᴅ ᴀs ᴀ ꜰᴏʀᴄᴇ-sᴜʙ ᴄʜᴀɴɴᴇʟ. "
            "Tʜᴇ ʙᴏᴛ ᴍᴜsᴛ ᴀʟʀᴇᴀᴅʏ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ ᴛʜᴇʀᴇ."
        )

    if not re.match(r"^-100\d{10,}$", args[0]):
        return await message.reply("<b>Iɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ ID.</b> Mᴜsᴛ ʙᴇ ɪɴ ᴛʜᴇ ꜰᴏʀᴍᴀᴛ <code>-100XXXXXXXXXX</code>.")

    channel_id = int(args[0])
    pro = await message.reply("<b><i>Please wait..</i></b>")

    try:
        chat_member = await client.get_chat_member(channel_id, client.me.id)
        if chat_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return await pro.edit(
                f"<b>I ᴀᴍ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ ᴏꜰ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ.</b> Sᴛᴀᴛᴜs: {chat_member.status}. "
                "Pʟᴇᴀsᴇ ᴍᴀᴋᴇ ᴍᴇ ᴀɴ ᴀᴅᴍɪɴ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ."
            )
    except UserNotParticipant:
        return await pro.edit("<b>I ᴀᴍ ɴᴏᴛ ᴀ ᴍᴇᴍʙᴇʀ ᴏꜰ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ.</b> Pʟᴇᴀsᴇ ᴀᴅᴅ ᴍᴇ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ.")
    except RPCError as e:
        return await pro.edit(f"<b>Fᴀɪʟᴇᴅ ᴛᴏ ᴠᴇʀɪꜰʏ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ:</b>\n<code>{e}</code>")

    try:
        chat = await client.get_chat(channel_id)
        title = chat.title
    except Exception:
        title = str(channel_id)

    await Seishiro.add_fsub_channel(channel_id)
    await pro.edit(f"<b>Fᴏʀᴄᴇ-sᴜʙ ᴄʜᴀɴɴᴇʟ ᴀᴅᴅᴇᴅ:</b> {title} (<code>{channel_id}</code>)")


@Bot.on_message(filters.command("del_chnl") & filters.private)
async def del_chnl_command(client: Bot, message: Message):
    if not await is_admin_user(message.from_user.id):
        return await message.reply("Sᴏʀʀʏ... ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ")

    args = message.text.split()[1:]
    if not args:
        return await message.reply("<b>Usᴀɢᴇ:</b> <code>/del_chnl -100XXXXXXXXXX</code>")

    try:
        channel_id = int(args[0])
    except ValueError:
        return await message.reply("<b>Iɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ ID.</b>")

    await Seishiro.remove_fsub_channel(channel_id)
    await message.reply(f"<b>Cʜᴀɴɴᴇʟ</b> <code>{channel_id}</code> <b>ʜᴀs ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ ꜰᴏʀᴄᴇ-sᴜʙ.</b>")


@Bot.on_message(filters.command("listchnl") & filters.private)
async def listchnl_command(client: Bot, message: Message):
    if not await is_admin_user(message.from_user.id):
        return await message.reply("Sᴏʀʀʏ... ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ")
    await message.reply(
        "<b>📋 Force-Sub Channels</b>\n\nTap below to view the list.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Lɪsᴛ ᴄʜᴀɴɴᴇʟs", callback_data="list_fsub_channels")]]
        ),
    )


@Bot.on_message(filters.command("fsub_mode") & filters.private)
async def fsub_mode_command(client: Bot, message: Message):
    if not await is_admin_user(message.from_user.id):
        return await message.reply("Sᴏʀʀʏ... ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ")
    await message.reply(
        "<b>⚙️ Force-Sub Mode</b>\n\nTap below to open the Fsub menu (add/remove channels, "
        "toggle request-mode on/off).",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Fsᴜʙ ᴍᴇɴᴜ", callback_data="fsub_settings_menu")]]
        ),
    )
