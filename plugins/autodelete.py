"""
Global auto-cleaner.

Every message the bot itself sends (start message, /start replies, command
replies, admin panel messages, broadcasts, etc.) is scheduled for automatic
deletion 1 hour after it's sent.

Messages that are "share links" — the shareable get-link / batch-link /
channel-invite-link messages produced by plugins/filestore.py and
plugins/start.py — are deleted after 5 minutes instead, since links are
meant to be grabbed quickly and shouldn't linger in the chat.

This is implemented once, centrally, by wrapping the Bot (Client) instance's
own send/copy/edit methods right after it connects (see enable_global_auto_delete
in bot.py). Every plugin in the repo already calls things like
message.reply_text(...), message.reply_photo(...), msg.copy(...),
client.send_message(...) etc. — all of those funnel through the handful of
Client methods wrapped here, so nothing else in the codebase needs to change
for the "everything gets cleaned automatically" behaviour.

Two safety rails:
  * Anything sent into the file-store DB channel (client.db_channel) or the
    DATABASE_CHANNEL log channel is NEVER auto-deleted — those are permanent
    storage / logs, not chat clutter.
  * A call made directly against the Client (client.send_message(...),
    client.send_photo(...), etc.) can opt out with no_auto_delete=True, or
    force a custom delay with auto_delete_after=<seconds>. NOTE: pyrogram's
    Message convenience methods (message.reply_text, .reply, .reply_photo,
    .copy, .edit) have fixed signatures and do NOT forward unknown kwargs —
    passing auto_delete_after/no_auto_delete to those will raise a
    TypeError. For those call sites, get the returned Message back and call
    schedule_delete(client, msg, delay) or unschedule(msg) explicitly
    afterwards instead.
"""

import asyncio
import logging

from pyrogram.types import Message

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
DEFAULT_AUTO_DELETE_SECONDS = 60 * 60      # 1 hour — normal bot messages
SHARE_LINK_AUTO_DELETE_SECONDS = 5 * 60    # 5 minutes — share/invite links

# Client methods that create/return new message(s). Wrapping these covers
# essentially every outgoing message in the bot, because pyrogram's
# Message.reply_text / reply_photo / reply / copy() convenience methods all
# call back into these same Client methods under the hood.
_SEND_METHODS = [
    "send_message", "send_photo", "send_video", "send_audio",
    "send_document", "send_animation", "send_voice", "send_video_note",
    "send_sticker", "send_media_group", "copy_message",
]

# Methods that *edit* an existing message rather than create one. We only
# need to touch these when a caller explicitly wants to reschedule/opt out
# on edit (e.g. a "please wait..." placeholder that gets edited into a
# share-link message). Left alone, an edited message keeps whatever
# deletion schedule it already had from when it was first sent.
_EDIT_METHODS = ["edit_message_text", "edit_message_caption"]

# Heuristic fallback: even if a call site forgets to tag a share-link
# message with auto_delete_after=300, catch it here so links never linger
# for the full hour.
_SHARE_LINK_MARKERS = ("your link", "ʏᴏᴜʀ ʟɪɴᴋ", "batch link", "ʙᴀᴛᴄʜ ʟɪɴᴋ")


def _looks_like_share_link(message) -> bool:
    try:
        text = (message.text or message.caption or "") if message else ""
        lowered = text.lower()
        if any(marker.lower() in lowered for marker in _SHARE_LINK_MARKERS):
            return True
        if message and message.reply_markup and getattr(message.reply_markup, "inline_keyboard", None):
            for row in message.reply_markup.inline_keyboard:
                for btn in row:
                    url = getattr(btn, "url", None)
                    if url and "t.me" in url:
                        return True
    except Exception:
        pass
    return False


class _Scheduler:
    """Tracks one pending deletion task per (chat_id, message_id) so a
    message can be rescheduled (e.g. on edit) instead of double-scheduled."""

    def __init__(self):
        self._tasks = {}

    def schedule(self, client, chat_id, message_id, delay):
        key = (chat_id, message_id)
        old = self._tasks.get(key)
        if old and not old.done():
            old.cancel()
        self._tasks[key] = asyncio.create_task(self._run(client, chat_id, message_id, delay, key))

    def unschedule(self, chat_id, message_id):
        """Cancel any pending deletion for a message — it should never be
        auto-deleted (e.g. admin disabled the per-file timer)."""
        key = (chat_id, message_id)
        old = self._tasks.pop(key, None)
        if old and not old.done():
            old.cancel()

    async def _run(self, client, chat_id, message_id, delay, key):
        try:
            await asyncio.sleep(delay)
            await client.delete_messages(chat_id, message_id)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.debug(f"Auto-delete: couldn't delete {chat_id}/{message_id}: {e}")
        finally:
            self._tasks.pop(key, None)


_scheduler = _Scheduler()


def _is_protected_chat(app, chat_id) -> bool:
    """Storage/log channels — never auto-delete anything sent there."""
    try:
        db_channel = getattr(app, "db_channel", None)
        if db_channel and chat_id in (db_channel.id, getattr(db_channel, "username", None)):
            return True
        database_channel = getattr(app, "_database_channel_id", None)
        if database_channel and str(chat_id) == str(database_channel):
            return True
    except Exception:
        pass
    return False


def schedule_delete(client, message, delay=None):
    """Manually schedule any Message (or list of Messages) for deletion.
    Still exported for any code that wants to call it directly."""
    if not message:
        return
    messages = message if isinstance(message, (list, tuple)) else [message]
    for msg in messages:
        if not isinstance(msg, Message):
            continue
        if _is_protected_chat(client, msg.chat.id):
            continue
        d = delay if delay is not None else (
            SHARE_LINK_AUTO_DELETE_SECONDS if _looks_like_share_link(msg) else DEFAULT_AUTO_DELETE_SECONDS
        )
        _scheduler.schedule(client, msg.chat.id, msg.id, d)


def unschedule(message):
    """Cancel any pending auto-deletion for a Message (or list of Messages)
    scheduled by the global auto-cleaner — use this for messages that must
    never be auto-deleted (e.g. an admin-disabled per-file timer)."""
    if not message:
        return
    messages = message if isinstance(message, (list, tuple)) else [message]
    for msg in messages:
        if isinstance(msg, Message):
            _scheduler.unschedule(msg.chat.id, msg.id)


def enable_global_auto_delete(app):
    """Monkeypatch this Bot/Client instance so every message it sends is
    auto-cleaned. Call once, after app.db_channel has been resolved."""

    from config import DATABASE_CHANNEL
    app._database_channel_id = DATABASE_CHANNEL or None

    def _extract_chat_id(args, kwargs):
        if "chat_id" in kwargs:
            return kwargs["chat_id"]
        if args:
            return args[0]
        return None

    def _wrap_send(name, original):
        async def wrapper(*args, **kwargs):
            no_auto_delete = kwargs.pop("no_auto_delete", False)
            auto_delete_after = kwargs.pop("auto_delete_after", None)

            result = await original(*args, **kwargs)

            if no_auto_delete:
                return result

            chat_id = _extract_chat_id(args, kwargs)
            if chat_id is not None and _is_protected_chat(app, chat_id):
                return result

            results = result if isinstance(result, (list, tuple)) else [result]
            for msg in results:
                if not isinstance(msg, Message):
                    continue
                delay = auto_delete_after if auto_delete_after is not None else (
                    SHARE_LINK_AUTO_DELETE_SECONDS if _looks_like_share_link(msg) else DEFAULT_AUTO_DELETE_SECONDS
                )
                _scheduler.schedule(app, msg.chat.id, msg.id, delay)

            return result

        wrapper.__name__ = f"auto_delete_wrapped_{name}"
        return wrapper

    def _wrap_edit(name, original):
        async def wrapper(*args, **kwargs):
            no_auto_delete = kwargs.pop("no_auto_delete", False)
            auto_delete_after = kwargs.pop("auto_delete_after", None)

            result = await original(*args, **kwargs)

            if no_auto_delete or auto_delete_after is None:
                return result

            chat_id = _extract_chat_id(args, kwargs)
            if chat_id is not None and _is_protected_chat(app, chat_id):
                return result

            if isinstance(result, Message):
                _scheduler.schedule(app, result.chat.id, result.id, auto_delete_after)

            return result

        wrapper.__name__ = f"auto_delete_wrapped_{name}"
        return wrapper

    for method_name in _SEND_METHODS:
        original = getattr(app, method_name, None)
        if original is None:
            continue
        setattr(app, method_name, _wrap_send(method_name, original))

    for method_name in _EDIT_METHODS:
        original = getattr(app, method_name, None)
        if original is None:
            continue
        setattr(app, method_name, _wrap_edit(method_name, original))

    logger.info(
        f"Global auto-cleaner enabled: bot messages auto-delete after "
        f"{DEFAULT_AUTO_DELETE_SECONDS // 60}min, share-links after "
        f"{SHARE_LINK_AUTO_DELETE_SECONDS // 60}min."
    )
