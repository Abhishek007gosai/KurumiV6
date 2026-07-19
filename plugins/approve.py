import asyncio
from bot import Bot
from config import *
from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest
from pyrogram.errors import (
    UserNotParticipant,
    UserAlreadyParticipant,
)

AUTO_APPROVE_ENABLED = True


@Client.on_chat_join_request(filters.group | filters.channel)
async def auto_approve(client: Bot, message: ChatJoinRequest):
    if not AUTO_APPROVE_ENABLED:
        return

    chat = message.chat
    user = message.from_user

    print(f"{user.first_name} requested to join {chat.title}")

    await asyncio.sleep(2)

    # Check if the user is already a member
    try:
        member = await client.get_chat_member(chat.id, user.id)
        if member.status in ["member", "administrator", "creator"]:
            print(f"User {user.id} is already a participant.")
            return
    except UserNotParticipant:
        pass
    except Exception as e:
        print(f"Error checking membership: {e}")
        return

    # Approve join request
    try:
        await client.approve_chat_join_request(
            chat_id=chat.id,
            user_id=user.id
        )
        print(f"Approved join request for {user.first_name} ({user.id})")
    except UserAlreadyParticipant:
        print(f"User {user.id} is already a participant.")
        return
    except Exception as e:
        print(f"Error approving join request: {e}")
        return

    # Send only approval message
    try:
        await client.send_message(
            chat_id=user.id,
            text=(
                f"✅ <b>Your request to join <code>{chat.title}</code> has been approved.</b>\n\n"
                f"You can now access the channel."
            ),
        )
        print(f"Sent approval message to {user.first_name} ({user.id})")
    except Exception as e:
        print(f"Error sending approval message: {e}")
