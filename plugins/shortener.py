"""
URL-Shortener verification gate — ported from ForYou (CodeXBotz-style ad
token system) and made fully bot-manageable + generalized:

  * ForYou hardcoded a 5-hour token and a single shortener (Publicearn.in).
    Here the shortener API key, website, tutorial link, verification
    message, forward/copy protection, and validity period (in DAYS) are
    all stored in Mongo and editable from /settings → Shortener Settings.
  * validity_days == 0 means "no grace period" — the user must pass the
    shortener check again for every single file/post, instead of getting
    N days of free access after one verification.
"""
import time
import asyncio
from functools import wraps

from pyrogram import filters, StopPropagation
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
)

from bot import Bot
from config import OWNER_ID
from database.database import Seishiro
from helper_func import shorten_url, encode

DAY_SECONDS = 86400


async def is_admin_user(user_id: int) -> bool:
    return user_id == OWNER_ID or await Seishiro.is_admin(user_id)


async def is_verified(user_id: int) -> bool:
    """True if the user currently holds a valid shortener pass."""
    settings = await Seishiro.get_shortener_settings()
    if not settings.get("enabled"):
        return True  # shortener switched off entirely -> everyone passes

    if await Seishiro.is_pro(user_id):
        return True  # premium users always skip the shortener

    days = int(settings.get("validity_days", 1))
    if days == 0:
        return False  # always re-verify, every single time

    expiry = await Seishiro.get_user_verify_expiry(user_id)
    return expiry > int(time.time())


async def send_verification(client: Bot, message: Message, reload_payload: str = None):
    """Send the 'please verify' message with the shortener link."""
    settings = await Seishiro.get_shortener_settings()
    user_id = message.from_user.id
    days = int(settings.get("validity_days", 1))

    reload_url = f"https://t.me/{client.username}?start={reload_payload}" if reload_payload else f"https://t.me/{client.username}"
    token_payload = await encode(f"verify-{user_id}-{int(time.time())}-{reload_payload or ''}")
    deep_link = f"https://t.me/{client.username}?start=vtok_{token_payload}"
    verify_url = await shorten_url(deep_link)

    buttons = [[InlineKeyboardButton("Vᴇʀɪꜰʏ ɴᴏᴡ", url=verify_url)]]
    if settings.get("tutorial_url"):
        buttons.append([InlineKeyboardButton("Hᴏᴡ ᴛᴏ ᴠᴇʀɪꜰʏ (ᴠɪᴅᴇᴏ ᴛᴜᴛᴏʀɪᴀʟ)", url=settings["tutorial_url"])])
    buttons.append([InlineKeyboardButton("Tʀʏ ᴀɢᴀɪɴ", url=reload_url)])

    text = settings.get("message", Seishiro.DEFAULT_SHORTENER["message"]).format(
        mention=message.from_user.mention,
        days="Unlimited re-verification (every post)" if days == 0 else f"{days} day{'s' if days != 1 else ''}",
    )

    pic = settings.get("pic")
    if pic:
        await client.send_photo(
            chat_id=message.chat.id,
            photo=pic,
            caption=text,
            reply_markup=InlineKeyboardMarkup(buttons),
            protect_content=bool(settings.get("protect_message", True)),
        )
    else:
        await client.send_message(
            chat_id=message.chat.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True,
            protect_content=bool(settings.get("protect_message", True)),
        )


def require_verification(func):
    """Decorator for delivery handlers: blocks and sends the verify
    message instead of running func() if the user hasn't passed the
    shortener check."""
    @wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        user_id = message.from_user.id
        if await is_admin_user(user_id):
            return await func(client, message, *args, **kwargs)
        if await is_verified(user_id):
            return await func(client, message, *args, **kwargs)
        reload_payload = message.command[1] if (message.command and len(message.command) > 1) else None
        await send_verification(client, message, reload_payload)
        return None
    return wrapper


# ----------------------------------------------------------------------
# /start vtok_<payload> — completes verification after the shortener redirect
# ----------------------------------------------------------------------
@Bot.on_message(filters.command("start") & filters.private & filters.regex(r"^/start vtok_"), group=-1)
async def verify_token_start(client: Bot, message: Message):
    from helper_func import decode
    user_id = message.from_user.id
    try:
        payload = message.text.split(" ", 1)[1][5:]  # strip "vtok_"
        decoded = await decode(payload)
        _, uid_str, ts_str, reload_payload = decoded.split("-", 3)
        if int(uid_str) != user_id:
            await message.reply(
                "This verification link isn't for you — it belongs to another account.",
            )
            raise StopPropagation
    except StopPropagation:
        raise
    except Exception:
        await message.reply("Invalid or corrupted verification link.")
        raise StopPropagation

    settings = await Seishiro.get_shortener_settings()
    days = int(settings.get("validity_days", 1))
    expiry = 0 if days == 0 else int(time.time()) + days * DAY_SECONDS
    await Seishiro.set_user_verified(user_id, expiry)

    if days == 0:
        note = "Your access is now unlocked <b>for this one link</b>. You'll need to verify again next time."
    else:
        note = f"You're verified for the next <b>{days} day{'s' if days != 1 else ''}</b>. No need to verify again until then."

    await message.reply(
        f"<b>Verification successful!</b>\n\n{note}",
        disable_web_page_preview=True,
    )

    # Immediately deliver the file/link the user originally clicked instead
    # of making them tap another button — reload_payload is the raw base64
    # /start argument from the original link (e.g. a "get-..." file-store
    # payload, or a plain channel-invite payload).
    if reload_payload:
        try:
            inner_decoded = await decode(reload_payload)
        except Exception:
            inner_decoded = None

        if inner_decoded and inner_decoded.startswith("get-") and client.db_channel:
            from plugins.start import deliver_stored_files
            await deliver_stored_files(client, message, inner_decoded, reload_arg=reload_payload)
            raise StopPropagation

        # Not a file-store payload — fall back to a reload button so the
        # normal /start deep-link flow (channel invite links, etc.) can run.
        reload_url = f"https://t.me/{client.username}?start={reload_payload}"
        await message.reply(
            "Tap below to continue:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Gᴏ ʙᴀᴄᴋ ᴛᴏ ʏᴏᴜʀ ꜰɪʟᴇ/ʟɪɴᴋ", url=reload_url)]]
            ),
        )
    raise StopPropagation


# ----------------------------------------------------------------------
# /settings → Shortener Settings submenu
# ----------------------------------------------------------------------
def _fmt_menu(s: dict) -> str:
    days_text = "0 (verify every single time)" if int(s.get("validity_days", 1)) == 0 else f"{s.get('validity_days', 1)} day(s)"
    return (
        "<b>🔗 Shortener Settings</b>\n\n"
        f"<b>Status:</b> {'✅ ON' if s.get('enabled') else '❌ OFF'}\n"
        f"<b>API Key:</b> <code>{s.get('api_key') or 'not set'}</code>\n"
        f"<b>Website:</b> <code>{s.get('site_url') or 'not set'}</code>\n"
        f"<b>Tutorial Video:</b> <code>{s.get('tutorial_url') or 'not set'}</code>\n"
        f"<b>Verify Image:</b> <code>{'set' if s.get('pic') else 'not set'}</code>\n"
        f"<b>Verify validity:</b> <code>{days_text}</code>\n"
        f"<b>Forward/Copy protection on verify msg:</b> {'✅ ON' if s.get('protect_message') else '❌ OFF'}\n\n"
        "Tap a button below to edit."
    )


def _menu_markup(s: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Tᴜʀɴ ᴏꜰꜰ" if s.get("enabled") else "Tᴜʀɴ ᴏɴ",
            callback_data="sc_toggle_enabled")],
        [InlineKeyboardButton("Sᴇᴛ ᴀᴘɪ ᴋᴇʏ", callback_data="sc_set_api_key"),
         InlineKeyboardButton("Sᴇᴛ ᴡᴇʙsɪᴛᴇ", callback_data="sc_set_site_url")],
        [InlineKeyboardButton("Sᴇᴛ ᴛᴜᴛᴏʀɪᴀʟ ᴠɪᴅᴇᴏ", callback_data="sc_set_tutorial_url")],
        [InlineKeyboardButton("Sᴇᴛ ᴠᴇʀɪꜰʏ ᴍᴇssᴀɢᴇ", callback_data="sc_set_message")],
        [InlineKeyboardButton("Sᴇᴛ ᴠᴇʀɪꜰʏ ɪᴍᴀɢᴇ", callback_data="sc_set_pic")],
        [InlineKeyboardButton("Dɪsᴀʙʟᴇ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ" if s.get("protect_message") else "Eɴᴀʙʟᴇ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ",
            callback_data="sc_toggle_protect")],
        [InlineKeyboardButton("Sᴇᴛ ᴠᴀʟɪᴅɪᴛʏ ᴅᴀʏs (ᴏᴡɴᴇʀ)", callback_data="sc_set_days")],
        [InlineKeyboardButton("« Bᴀᴄᴋ", callback_data="settings_main")],
    ])


@Bot.on_message(filters.command("shortener") & filters.private)
async def shortener_command(client: Bot, message: Message):
    if not await is_admin_user(message.from_user.id):
        return await message.reply("Sᴏʀʀʏ... ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ")
    s = await Seishiro.get_shortener_settings()
    await message.reply(_fmt_menu(s), reply_markup=_menu_markup(s), disable_web_page_preview=True)


@Bot.on_callback_query(filters.regex("^sc_") | filters.regex("^shortener_menu$"), group=3)
async def shortener_settings_callback(client: Bot, cq: CallbackQuery):
    if not await is_admin_user(cq.from_user.id):
        return await cq.answer("You're not an admin.", show_alert=True)

    data = cq.data
    s = await Seishiro.get_shortener_settings()

    if data == "shortener_menu":
        return await cq.message.edit_text(_fmt_menu(s), reply_markup=_menu_markup(s), disable_web_page_preview=True)

    if data == "sc_toggle_enabled":
        await Seishiro.update_shortener_settings(enabled=not s.get("enabled"))
        s = await Seishiro.get_shortener_settings()
        await cq.answer(f"Shortener {'enabled' if s['enabled'] else 'disabled'}.")
        return await cq.message.edit_text(_fmt_menu(s), reply_markup=_menu_markup(s), disable_web_page_preview=True)

    if data == "sc_toggle_protect":
        await Seishiro.update_shortener_settings(protect_message=not s.get("protect_message"))
        s = await Seishiro.get_shortener_settings()
        await cq.answer("Protection setting updated.")
        return await cq.message.edit_text(_fmt_menu(s), reply_markup=_menu_markup(s), disable_web_page_preview=True)

    if data == "sc_set_days" and cq.from_user.id != OWNER_ID:
        return await cq.answer("Only the bot owner can change validity days.", show_alert=True)

    if data == "sc_set_pic":
        await cq.answer()
        try:
            reply = await client.ask(
                chat_id=cq.from_user.id,
                text="Send the <b>image</b> to use on the verification message, or /clear to remove it, or /cancel to abort.",
                filters=(filters.photo | filters.text),
                timeout=120,
            )
        except asyncio.TimeoutError:
            return
        if reply.text and reply.text.strip() == "/cancel":
            await reply.reply("Cancelled.")
        elif reply.text and reply.text.strip() == "/clear":
            await Seishiro.update_shortener_settings(pic=None)
            await reply.reply("✅ Verify image removed.")
        elif reply.photo:
            await Seishiro.update_shortener_settings(pic=reply.photo.file_id)
            await reply.reply("✅ Verify image saved.")
        else:
            await reply.reply("❌ Please send a photo. Nothing was changed.")
        s = await Seishiro.get_shortener_settings()
        return await client.send_message(
            chat_id=cq.from_user.id, text=_fmt_menu(s), reply_markup=_menu_markup(s), disable_web_page_preview=True,
        )

    prompts = {
        "sc_set_api_key": ("Send the new <b>Shortener API key</b>.\n\nSend /cancel to abort.", "api_key", str),
        "sc_set_site_url": ("Send the new <b>Shortener website</b> (e.g. <code>publicearn.in</code>, no https://).\n\nSend /cancel to abort.", "site_url", str),
        "sc_set_tutorial_url": ("Send the <b>video tutorial link</b> (e.g. a Telegram post/YouTube link).\n\nSend /cancel to abort.", "tutorial_url", str),
        "sc_set_message": ("Send the new <b>verification message</b>. You can use <code>{mention}</code> and <code>{days}</code> placeholders. HTML formatting supported.\n\nSend /cancel to abort.", "message", str),
        "sc_set_days": ("Send the <b>validity in days</b> as a number.\n\n<b>0</b> = user must verify again for every single post.\n\nSend /cancel to abort.", "validity_days", int),
    }
    if data in prompts:
        prompt_text, field, cast = prompts[data]
        await cq.answer()
        try:
            reply = await client.ask(chat_id=cq.from_user.id, text=prompt_text, timeout=120)
        except asyncio.TimeoutError:
            return
        if reply.text and reply.text.strip() == "/cancel":
            await reply.reply("Cancelled.")
        else:
            try:
                value = cast(reply.text.strip())
                if field == "validity_days" and value < 0:
                    raise ValueError
                await Seishiro.update_shortener_settings(**{field: value})
                await reply.reply("✅ Saved.")
            except Exception:
                await reply.reply("❌ Invalid value, nothing was changed.")
        s = await Seishiro.get_shortener_settings()
        return await client.send_message(
            chat_id=cq.from_user.id, text=_fmt_menu(s), reply_markup=_menu_markup(s), disable_web_page_preview=True,
        )
