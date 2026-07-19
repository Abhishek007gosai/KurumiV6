import pyrogram.utils
from bot import Bot

# Raises pyrogram's minimum recognized channel ID so very large/negative
# channel IDs (common on some servers) aren't misread as invalid.
pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

if __name__ == "__main__":
    Bot().run()
