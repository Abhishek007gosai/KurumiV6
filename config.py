import os
from os import environ
import logging
from logging.handlers import RotatingFileHandler

# --------------------------------------------
# Core Bot Credentials (get these from @BotFather / my.telegram.org)
# NEVER commit real values here — set them as environment variables instead.
# --------------------------------------------
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
APP_ID = int(os.environ.get("APP_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
OWNER = os.environ.get("OWNER", "")  # Owner username without @
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")

# --------------------------------------------
# File-Store DB Channel (from KurumiFileStoreV2)
# This is the private channel the bot uses to archive forwarded
# files/messages for the /filelink and /fbatch commands.
# --------------------------------------------
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))

# --------------------------------------------
# Link-Share restart-notification channel (from KafkaLinkBotV1)
# --------------------------------------------
DATABASE_CHANNEL = os.environ.get("DATABASE_CHANNEL", "")

# --------------------------------------------
PORT = os.environ.get("PORT", "8080")
# --------------------------------------------
DB_URL = os.environ.get("DATABASE_URL", os.environ.get("DB_URI", ""))
DB_NAME = os.environ.get("DATABASE_NAME", os.environ.get("DB_NAME", "cluster0"))
# Kept for backward compatibility with code that imports DB_URI/DB_NAME
DB_URI = DB_URL
# --------------------------------------------
FSUB_LINK_EXPIRY = int(os.environ.get("FSUB_LINK_EXPIRY", "300"))  # 0 means no expiry
BAN_SUPPORT = os.environ.get("BAN_SUPPORT", "https://t.me/YourSupportBot")
TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "100"))

START_PIC = os.environ.get("START_PIC", "https://i.ibb.co/0R9k9x4M/tmpbtpr7q0.jpg")
FORCE_PIC = os.environ.get("FORCE_PIC", "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg")
FSUB_PIC = os.environ.get("FSUB_PIC", "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg")
COMMAND_PHOTO = os.environ.get("COMMAND_PHOTO", "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg")
# --------------------------------------------

HELP_TXT = os.environ.get(
    "HELP_MESSAGE",
    "<b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ʏᴏᴜ ᴄᴀɴ ᴅᴏ sᴏ ʙʏ sᴜʙsᴄʀɪʙɪɴɢ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴛʜᴀɴᴋs Fᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ\n"
    "❏ ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅs\n├/start : sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ\n"
    "sɪᴍᴘʟʏ ᴄʟɪᴄᴋ ᴏɴ ʟɪɴᴋ ᴀɴᴅ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ᴊᴏɪɴ ʙᴏᴛʜ ᴄʜᴀɴɴᴇʟs ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ ᴛʜᴀᴛs ɪᴛ.</b>"
)
ABOUT_TXT = os.environ.get(
    "ABOUT_MESSAGE",
    "<b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴄᴏᴍᴍᴜɴɪᴛʏ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ʏᴏᴜ ᴄᴀɴ ᴅᴏ sᴏ ʙʏ sᴜʙsᴄʀɪʙɪɴɢ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ\nᴛʜᴀɴᴋs ғᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ</b>"
)
START_MSG = os.environ.get(
    "START_MESSAGE",
    "<b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴄᴏᴍᴍᴜɴɪᴛʏ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ʏᴏᴜ ᴄᴀɴ ᴅᴏ sᴏ ʙʏ sᴜʙsᴄʀɪʙɪɴɢ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ\nᴛʜᴀɴᴋs ғᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ</b>"
)
FORCE_MSG = os.environ.get(
    "FORCE_SUB_MESSAGE",
    "<b><blockquote>ʜᴇʟʟᴏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ <a href='https://t.me/Ecchi_Dex'>ᴇᴄᴄʜɪ ᴅᴇx</a></blockquote>ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ/ɢʀᴏᴜᴘ ғɪʀsᴛ, ᴘʟᴇᴀsᴇ sᴜʙsᴄʀɪʙᴇ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ᴛʜʀᴏᴜɢʜ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴀɴᴅ sᴛᴀʀᴛ ʙᴏᴛ ᴀɢᴀɪɴ<blockquote>ʜᴏᴡ ᴛᴏ ᴜsᴇ ʙᴏᴛ <a href=https://t.me/NexusTutorial/6>ᴛᴜᴛᴏʀɪᴀʟ ᴄʟɪᴄᴋ ʜᴇʀᴇ</a></blockquote></b>"
)

CMD_TXT = """<blockquote><b>» ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs:</b></blockquote>

<b>ʙᴏᴛ ᴍᴏᴅᴇ</b>
<b>›› /mode :</b> sᴡɪᴛᴄʜ ʙᴇᴛᴡᴇᴇɴ Lɪɴᴋ Sʜᴀʀᴇ ᴀɴᴅ Fɪʟᴇ Sᴛᴏʀᴇ ᴍᴏᴅᴇ

<b>ғɪʟᴇ ꜱᴛᴏʀᴇ (ᴏɴʟʏ ᴡᴏʀᴋs ɪɴ Fɪʟᴇ Sᴛᴏʀᴇ ᴍᴏᴅᴇ)</b>
<b>›› /genlink :</b> ɢᴇɴᴇʀᴀᴛᴇ ᴀ sʜᴀʀᴇᴀʙʟᴇ ʟɪɴᴋ ғᴏʀ ᴀ sɪɴɢʟᴇ ᴅʙ-ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ
<b>›› /batch :</b> ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʙᴀᴛᴄʜ ʟɪɴᴋ ғᴏʀ ᴀ ʀᴀɴɢᴇ ᴏғ ᴅʙ-ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛs
<b>›› /custom_batch :</b> ᴄᴏʟʟᴇᴄᴛ ᴀʀʙɪᴛʀᴀʀʏ ᴍᴇssᴀɢᴇs ɪɴᴛᴏ ᴀ ᴄᴜsᴛᴏᴍ ʙᴀᴛᴄʜ ʟɪɴᴋ
<b>›› /dlt_time :</b> sᴇᴛ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ ғᴏʀ sᴛᴏʀᴇᴅ ғɪʟᴇs
<b>›› /check_dlt_time :</b> ᴄʜᴇᴄᴋ ᴄᴜʀʀᴇɴᴛ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ
<b>›› /caption :</b> ᴛᴏɢɢʟᴇ/ᴇᴅɪᴛ ᴛʜᴇ ᴄᴜsᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ (ᴏғғ = ᴜsᴇs ᴇᴀᴄʜ ғɪʟᴇ's ᴏᴡɴ ᴄᴀᴘᴛɪᴏɴ)
<b>›› /stats :</b> ʙᴏᴛ ᴜᴘᴛɪᴍᴇ
<b>›› /users :</b> ᴛᴏᴛᴀʟ ᴜsᴇʀs ᴄᴏᴜɴᴛ

<b>sʜᴏʀᴛᴇɴᴇʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ</b>
<b>›› /shortener :</b> ᴏᴘᴇɴ ᴛʜᴇ sʜᴏʀᴛᴇɴᴇʀ sᴇᴛᴛɪɴɢs (ᴀᴘɪ, sɪᴛᴇ, ᴛᴜᴛᴏʀɪᴀʟ, ᴍᴇssᴀɢᴇ, ᴘʀᴏᴛᴇᴄᴛɪᴏɴ, ᴠᴀʟɪᴅɪᴛʏ ᴅᴀʏs)
<b>›› /addpremium /delpremium /premiumusers :</b> ɢʀᴀɴᴛ ᴜsᴇʀs ᴀ sʜᴏʀᴛᴇɴᴇʀ-ғʀᴇᴇ ᴘᴀss (ᴏᴡɴᴇʀ ᴏɴʟʏ)

<b>ʟɪɴᴋ ꜱʜᴀʀᴇ (ᴏɴʟʏ ᴡᴏʀᴋs ɪɴ Lɪɴᴋ Sʜᴀʀᴇ ᴍᴏᴅᴇ)</b>
<b>›› /settings :</b> ᴏᴘᴇɴ ᴛʜᴇ ɪɴᴛᴇʀᴀᴄᴛɪᴠᴇ sᴇᴛᴛɪɴɢs ᴍᴇɴᴜ (ᴄʜᴀɴɴᴇʟs, ғsᴜʙ, ʙᴀɴs, sʜᴏʀᴛᴇɴᴇʀ, ᴄᴀᴘᴛɪᴏɴ, ᴍᴏᴅᴇ)
<b>›› /listchnl :</b> ʟɪsᴛ ғᴏʀᴄᴇ-sᴜʙ ᴄʜᴀɴɴᴇʟs
<b>›› /fsub_mode :</b> ᴏᴘᴇɴ ᴛʜᴇ ғᴏʀᴄᴇ-sᴜʙ ᴍᴇɴᴜ (ᴀᴅᴅ/ʀᴇᴍᴏᴠᴇ ᴄʜᴀɴɴᴇʟs, ᴛᴏɢɢʟᴇ ʀᴇǫᴜᴇsᴛ ᴍᴏᴅᴇ)

<b>ꜱʜᴀʀᴇᴅ ᴀᴅᴍɪɴ ᴛᴏᴏʟꜱ</b>
<b>›› /broadcast :</b> ʙʀᴏᴀᴅᴄᴀsᴛ ᴀ ᴍᴇssᴀɢᴇ ᴛᴏ ᴀʟʟ ᴜsᴇʀs (ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇssᴀɢᴇ)
<b>›› /pbroadcast :</b> ʙʀᴏᴀᴅᴄᴀsᴛ ᴀɴᴅ ᴘɪɴ
<b>›› /dbroadcast :</b> ʙʀᴏᴀᴅᴄᴀsᴛ ᴡɪᴛʜ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ
<b>›› /ban /unban /banlist :</b> ᴍᴀɴᴀɢᴇ ʙᴀɴɴᴇᴅ ᴜsᴇʀs (ᴀʟsᴏ ᴀᴠᴀɪʟᴀʙʟᴇ ᴠɪᴀ /settings)
<b>›› /add_admin /deladmin /admins :</b> ᴍᴀɴᴀɢᴇ ʙᴏᴛ ᴀᴅᴍɪɴs
"""
# --------------------------------------------
CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", "")
PROTECT_CONTENT = os.environ.get("PROTECT_CONTENT", "False") == "True"
# --------------------------------------------
BOT_STATS_TEXT = "<b>BOT UPTIME</b>\n{uptime}"
USER_REPLY_TEXT = "Sᴏʀʀʏ... ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ"
# --------------------------------------------

LOG_FILE_NAME = "combinedbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(LOG_FILE_NAME, maxBytes=50000000, backupCount=10),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
