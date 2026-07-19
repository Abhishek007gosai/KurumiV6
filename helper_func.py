import base64
import re
import asyncio
import aiohttp
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.filters import Filter
from config import *
from database.database import Seishiro

async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = (base64_bytes.decode("ascii")).strip("=")
    return base64_string

async def decode(base64_string):
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes)
    string = string_bytes.decode("ascii")
    return string

def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    hmm = len(time_list)
    for x in range(hmm):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time


def get_exp_time(seconds: int) -> str:
    periods = [('days', 86400), ('hours', 3600), ('mins', 60), ('secs', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)} {period_name} '
    return result.strip() or "0 secs"


# =====================================================================
# Ported from KurumiFileStoreV2 — shared admin filter + file-store
# helpers used by plugins/filestore.py, plugins/admin.py,
# plugins/banuser.py, plugins/broadcast.py and plugins/useless.py.
# =====================================================================

async def check_admin(filter, client, update):
    """True for the OWNER or anyone in the admins collection."""
    try:
        user_id = update.from_user.id
        return any([user_id == OWNER_ID, await Seishiro.admin_exist(user_id)])
    except Exception as e:
        print(f"! Exception in check_admin: {e}")
        return False


admin = filters.create(check_admin)


async def get_messages(client, message_ids):
    """Fetch a list of messages from the file-store DB channel."""
    messages = []
    total_messages = 0
    while total_messages != len(message_ids):
        temb_ids = message_ids[total_messages:total_messages + 200]
        try:
            msgs = await client.get_messages(chat_id=client.db_channel.id, message_ids=temb_ids)
        except FloodWait as e:
            await asyncio.sleep(e.x)
            msgs = await client.get_messages(chat_id=client.db_channel.id, message_ids=temb_ids)
        except Exception as e:
            print(f"Error fetching messages: {e}")
            msgs = []
        total_messages += len(temb_ids)
        messages.extend(msgs)
    return messages


async def get_message_id(client, message):
    """Extract a DB-channel message id from a forwarded post or its link."""
    if not client.db_channel:
        return 0
    if message.forward_from_chat:
        if message.forward_from_chat.id == client.db_channel.id:
            return message.forward_from_message_id
        return 0
    elif message.forward_sender_name:
        return 0
    elif message.text:
        pattern = r"https://t.me/(?:c/)?(.*)/(\d+)"
        matches = re.match(pattern, message.text)
        if not matches:
            return 0
        channel_id = matches.group(1)
        msg_id = int(matches.group(2))
        if channel_id.isdigit():
            if f"-100{channel_id}" == str(client.db_channel.id):
                return msg_id
        else:
            if channel_id == client.db_channel.username:
                return msg_id
    return 0


async def shorten_url(long_url: str) -> str:
    """Shorten a URL using the admin-configured shortener API/site.
    Ported & generalized from ForYou's helper.shorten_url (was hardcoded
    to Publicearn.in — now reads api_key + site_url from the database so
    it's fully bot-manageable). Falls back to the original URL if the
    shortener isn't configured or the request fails.
    """
    settings = await Seishiro.get_shortener_settings()
    api_key = settings.get("api_key")
    site_url = settings.get("site_url")
    if not api_key or not site_url:
        return long_url

    site = site_url.rstrip("/")
    request_url = f"https://{site}/api?api={api_key}&url={long_url}&format=text"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(request_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                text = (await resp.text()).strip()
                if text.startswith("http"):
                    return text
    except Exception:
        pass
    return long_url
