# Ported from KurumiFileStoreV2 (plugins/admin.py), adapted to the
# merged bot's database.database.Seishiro instance.

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot import Bot
from config import OWNER_ID
from database.database import Seishiro
from helper_func import admin


@Bot.on_message(filters.command('add_admin') & filters.private & filters.user(OWNER_ID))
async def add_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>Please wait..</i></b>", quote=True)
    admin_ids = await Seishiro.get_all_admins()
    admins = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Cʟᴏsᴇ", callback_data="close")]])

    if not admins:
        return await pro.edit(
            "<b>You need to provide user ID(s) to add as admin.</b>\n\n"
            "<b>Usage:</b>\n<code>/add_admin [user_id]</code>\n\n"
            "<b>Example:</b>\n<code>/add_admin 1234567890 9876543210</code>",
            reply_markup=reply_markup
        )

    admin_list, valid_ids, check = "", [], 0
    for id in admins:
        try:
            id_int = int(id)
        except ValueError:
            admin_list += f"<blockquote><b>Invalid ID: <code>{id}</code></b></blockquote>\n"
            continue

        if id_int in admin_ids:
            admin_list += f"<blockquote><b>ID <code>{id}</code> already exists.</b></blockquote>\n"
            continue

        valid_ids.append(id_int)
        admin_list += f"<b><blockquote>(ID: <code>{id}</code>) added.</blockquote></b>\n"
        check += 1

    if check == len(valid_ids) and valid_ids:
        for id in valid_ids:
            await Seishiro.add_admin(id)
        await pro.edit(f"<b>✅ Admin(s) added successfully:</b>\n\n{admin_list}", reply_markup=reply_markup)
    else:
        await pro.edit(f"<b>⚠️ Some IDs were not added:</b>\n\n{admin_list.strip()}", reply_markup=reply_markup)


@Bot.on_message(filters.command(['deladmin', 'del_admin']) & filters.private & filters.user(OWNER_ID))
async def delete_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>Please wait..</i></b>", quote=True)
    admin_ids = await Seishiro.get_all_admins()
    admins = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Cʟᴏsᴇ", callback_data="close")]])

    if not admins:
        return await pro.edit(
            "<b>Please provide valid admin ID(s) to remove.</b>\n\n"
            "<code>/deladmin [user_id]</code> — remove specific IDs\n"
            "<code>/deladmin all</code> — remove all admins",
            reply_markup=reply_markup
        )

    if len(admins) == 1 and admins[0].lower() == "all":
        if admin_ids:
            for id in admin_ids:
                await Seishiro.del_admin(id)
            ids = "\n".join(f"<blockquote><code>{a}</code> ✅</blockquote>" for a in admin_ids)
            return await pro.edit(f"<b>⛔️ All admin IDs have been removed:</b>\n{ids}", reply_markup=reply_markup)
        return await pro.edit("<b><blockquote>No admin IDs to remove.</blockquote></b>", reply_markup=reply_markup)

    if admin_ids:
        passed = ''
        for admin_id in admins:
            try:
                id = int(admin_id)
            except ValueError:
                passed += f"<blockquote><b>Invalid ID: <code>{admin_id}</code></b></blockquote>\n"
                continue

            if id in admin_ids:
                await Seishiro.del_admin(id)
                passed += f"<blockquote><code>{id}</code> ✅ Removed</blockquote>\n"
            else:
                passed += f"<blockquote><b>ID <code>{id}</code> not found in admin list.</b></blockquote>\n"

        await pro.edit(f"<b>⛔️ Admin removal result:</b>\n\n{passed}", reply_markup=reply_markup)
    else:
        await pro.edit("<b><blockquote>No admin IDs available to delete.</blockquote></b>", reply_markup=reply_markup)


@Bot.on_message(filters.command('admins') & filters.private & admin)
async def get_admins(client: Client, message: Message):
    pro = await message.reply("<b><i>Please wait..</i></b>", quote=True)
    admin_ids = await Seishiro.get_all_admins()

    if not admin_ids:
        admin_list = "<b><blockquote>❌ No admins found.</blockquote></b>"
    else:
        admin_list = "\n".join(f"<b><blockquote>ID: <code>{id}</code></blockquote></b>" for id in admin_ids)

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Cʟᴏsᴇ", callback_data="close")]])
    await pro.edit(f"<b>⚡ Current Admin List:</b>\n\n{admin_list}", reply_markup=reply_markup)
