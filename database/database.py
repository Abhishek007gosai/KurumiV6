import motor.motor_asyncio
import base64
import logging
from datetime import datetime, date
from typing import List, Optional
from config import * 

logging.basicConfig(level=logging.INFO)


class Master:
    def __init__(self, DB_URL, DB_NAME):
        self.dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URL)
        self.database = self.dbclient[DB_NAME]

        # Initialize all collections
        self.user_data = self.database['users']
        self.channel_data = self.database['channels']
        self.admins_data = self.database['admins']
        self.del_timer_data = self.database['del_timer']
        self.ban_data = self.database['ban_data']
        self.fsub_data = self.database['fsub']
        self.rqst_fsub_data = self.database['request_forcesub']
        self.settings_data = self.database['bot_settings']
        self.verify_data = self.database['shortener_verify']
        self.rqst_fsub_Channel_data = self.database['request_forcesub_channel']

        # Main collection reference (for backward compatibility)
        self.col = self.user_data

    def new_user(self, id, username=None):
        return dict(
            _id=int(id),
            username=username.lower() if username else None,
            join_date=date.today().isoformat(),
            ban_status=dict(
                is_banned=False,
                ban_duration=0,
                banned_on=date.max.isoformat(),
                ban_reason='',
            )
        )

    async def add_user(self, b, m):
        u = m.from_user
        if not await self.is_user_exist(u.id):
            user = self.new_user(u.id, u.username)
            try:
                await self.user_data.insert_one(user)
                logging.info(f"New user added: {u.id}")
                # Uncomment if send_log function exists
                # await send_log(b, u)
            except Exception as e:
                logging.error(f"Error adding user {u.id}: {e}")
        else:
            logging.info(f"User {u.id} already exists")

    async def is_user_exist(self, id):
        try:
            user = await self.user_data.find_one({"_id": int(id)})
            return bool(user)
        except Exception as e:
            logging.error(f"Error checking if user {id} exists: {e}")
            return False

    async def get_all_users(self):
        try:
            all_users = self.user_data.find({})
            return all_users
        except Exception as e:
            logging.error(f"Error getting all users: {e}")
            return None

    async def total_users_count(self):
        try:
            count = await self.user_data.count_documents({})
            return count
        except Exception as e:
            logging.error(f"Error counting users: {e}")
            return 0

    async def delete_user(self, user_id):
        try:
            await self.user_data.delete_many({"_id": int(user_id)})
        except Exception as e:
            logging.error(f"Error deleting user {user_id}: {e}")

    async def is_user_banned(self, user_id):
        try:
            user = await self.ban_data.find_one({"_id": user_id})
            if user and user.get("ban_status", {}).get("is_banned", False):
                return user
        except Exception as e:
            logging.error(f"Error in checking ban status {user_id}: {e}")

    async def is_admin(self, user_id: int) -> bool:
        """Check if a user is an admin."""
        try:
            _id = int(user_id)
            return bool(await self.admins_data.find_one({"_id": user_id}))
        except Exception as e:
            logging.error(f"Error checking admin status for {user_id}: {e}")
            return False

    async def add_admin(self, user_id: int) -> bool:
        """Add a user as admin."""
        try:
            _id = int(user_id)
            await self.admins_data.update_one(
                {"_id": user_id},
                {"$set": {"_id": user_id, "added_at": datetime.utcnow()}},
                upsert=True
            )
            return True
        except Exception as e:
            logging.error(f"Error adding admin {user_id}: {e}")
            return False

    async def remove_admin(self, user_id: int) -> bool:
        """Remove a user from admins."""
        try:
            result = await self.admins_data.delete_one({"_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            logging.error(f"Error removing admin {user_id}: {e}")
            return False

    async def list_admins(self) -> list:
        """List all admin user IDs."""
        try:
            admins = await self.admins_data.find({}).to_list(None)
            return [admin["_id"] for admin in admins]
        except Exception as e:
            logging.error(f"Error listing admins: {e}")
            return []
            
    async def get_encoded_link(self, channel_id: int) -> Optional[str]:
        """Get the encoded link for a channel."""
        if not isinstance(channel_id, int):
            logging.error(f"Invalid channel_id: {channel_id}")
            return None

        try:
            channel = await self.channel_data.find_one({"channel_id": channel_id, "status": "active"})
            if channel and "encoded_link" in channel:
                logging.info(f"Retrieved encoded_link for channel {channel_id}: {channel['encoded_link']}")
                return channel["encoded_link"]
            else:
                logging.warning(f"No encoded_link found for channel {channel_id}")
                return None
        except Exception as e:
            logging.error(f"Error getting encoded link for channel {channel_id}: {e}")
            return None

    async def get_encoded_link2(self, channel_id: int) -> Optional[str]:
        """Get the secondary encoded link for a channel."""
        if not isinstance(channel_id, int):
            logging.error(f"Invalid channel_id: {channel_id}")
            return None

        try:
            channel = await self.channel_data.find_one({"channel_id": channel_id, "status": "active"})
            if channel and "req_encoded_link" in channel:
                logging.info(f"Retrieved req_encoded_link for channel {channel_id}: {channel['req_encoded_link']}")
                return channel["req_encoded_link"]
            else:
                logging.warning(f"No req_encoded_link found for channel {channel_id}")
                return None
        except Exception as e:
            logging.error(f"Error getting secondary encoded link for channel {channel_id}: {e}")
            return None

    async def save_channel(self, channel_id: int) -> bool:
        """Save a channel to the database with invite link expiration."""
        if not isinstance(channel_id, int):
            logging.error(f"Invalid channel_id: {channel_id}")
            return False

        try:
            # Generate encoded links using standard base64 encoding
            string_bytes = str(channel_id).encode("ascii")
            base64_bytes = base64.urlsafe_b64encode(string_bytes)
            encoded_link = (base64_bytes.decode("ascii")).strip("=")
            req_encoded_link = encoded_link  # Same encoding for both
            
            await self.channel_data.update_one(
                {"channel_id": channel_id},
                {
                    "$set": {
                        "channel_id": channel_id,
                        "encoded_link": encoded_link,
                        "req_encoded_link": req_encoded_link,
                        "invite_link_expiry": None,
                        "created_at": datetime.utcnow(),
                        "status": "active"
                    }
                },
                upsert=True
            )
            logging.info(f"Saved channel {channel_id} with encoded_link: {encoded_link}")
            return True
        except Exception as e:
            logging.error(f"Error saving channel {channel_id}: {e}")
            return False

    async def get_channels(self) -> List[int]:
        """Get all active channel IDs from the database."""
        try:
            channels = await self.channel_data.find({"status": "active"}).to_list(None)
            valid_channels = [ch["channel_id"] for ch in channels if "channel_id" in ch]
            if not valid_channels:
                logging.info(f"No valid channels found in database. Total documents checked: {len(channels)}")
            return valid_channels
        except Exception as e:
            logging.error(f"Error fetching channels: {e}")
            return []

    async def show_channels(self) -> List[int]:
        """Alias for get_channels - used by reqChannel_exist."""
        return await self.get_channels()

    async def delete_channel(self, channel_id: int) -> bool:
        """Delete a channel from the database."""
        try:
            result = await self.channel_data.delete_one({"channel_id": channel_id})
            return result.deleted_count > 0
        except Exception as e:
            logging.error(f"Error deleting channel {channel_id}: {e}")
            return False

    async def save_encoded_link(self, channel_id: int) -> Optional[str]:
        """Save an encoded link for a channel and return it."""
        if not isinstance(channel_id, int):
            logging.error(f"Invalid channel_id: {channel_id}")
            return None

        try:
            # Use the same encoding method as helper_func.py
            string_bytes = str(channel_id).encode("ascii")
            base64_bytes = base64.urlsafe_b64encode(string_bytes)
            encoded_link = (base64_bytes.decode("ascii")).strip("=")
            
            await self.channel_data.update_one(
                {"channel_id": channel_id},
                {
                    "$set": {
                        "channel_id": channel_id,
                        "encoded_link": encoded_link,
                        "status": "active",
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            logging.info(f"Saved encoded link for channel {channel_id}: {encoded_link}")
            return encoded_link
        except Exception as e:
            logging.error(f"Error saving encoded link for channel {channel_id}: {e}")
            return None

    async def get_channel_by_encoded_link(self, encoded_link: str) -> Optional[int]:
        """Get a channel ID by its encoded link - with fallback decoding."""
        if not isinstance(encoded_link, str):
            logging.error("get_channel_by_encoded_link: encoded_link is not a string")
            return None

        try:
            logging.info(f"[NORMAL LINK] Searching for channel with encoded_link: {encoded_link}")
            
            # First try: Search by encoded_link field
            channel = await self.channel_data.find_one({"encoded_link": encoded_link, "status": "active"})
            
            if channel and "channel_id" in channel:
                logging.info(f"[NORMAL LINK] Found channel by encoded_link: {channel['channel_id']}")
                return channel["channel_id"]
            
            # Second try: Decode the base64 string to get channel_id
            logging.warning(f"[NORMAL LINK] Not found in DB, trying to decode: {encoded_link}")
            try:
                # Use the same decoding method as helper_func.py
                base64_string = encoded_link.strip("=")
                base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
                string_bytes = base64.urlsafe_b64decode(base64_bytes)
                decoded_string = string_bytes.decode("ascii")
                decoded_id = int(decoded_string)
                logging.info(f"[NORMAL LINK] Successfully decoded channel_id: {decoded_id}")
                
                # Try to find channel by channel_id
                channel = await self.channel_data.find_one({"channel_id": decoded_id})
                
                if channel:
                    logging.info(f"[NORMAL LINK] Channel {decoded_id} exists in DB, updating encoded_link")
                    # Update the encoded_link field for this channel
                    await self.channel_data.update_one(
                        {"channel_id": decoded_id},
                        {
                            "$set": {
                                "encoded_link": encoded_link,
                                "status": "active",
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    return decoded_id
                else:
                    logging.warning(f"[NORMAL LINK] Channel {decoded_id} not found in DB, creating it")
                    # Create the channel entry using the same encoding
                    string_bytes = str(decoded_id).encode("ascii")
                    base64_bytes = base64.urlsafe_b64encode(string_bytes)
                    new_encoded_link = (base64_bytes.decode("ascii")).strip("=")
                    
                    await self.channel_data.update_one(
                        {"channel_id": decoded_id},
                        {
                            "$set": {
                                "channel_id": decoded_id,
                                "encoded_link": new_encoded_link,
                                "req_encoded_link": new_encoded_link,
                                "status": "active",
                                "created_at": datetime.utcnow()
                            }
                        },
                        upsert=True
                    )
                    return decoded_id
                    
            except Exception as decode_error:
                logging.error(f"[NORMAL LINK] Failed to decode base64 '{encoded_link}': {decode_error}")
            
            return None
            
        except Exception as e:
            logging.error(f"[NORMAL LINK] Error fetching channel by encoded link {encoded_link}: {e}")
            return None

    async def save_encoded_link2(self, channel_id: int, encoded_link: str) -> Optional[str]:
        """Save a secondary encoded link for a channel."""
        if not isinstance(channel_id, int) or not isinstance(encoded_link, str):
            logging.error(f"Invalid input: channel_id={channel_id}, encoded_link={encoded_link}")
            return None

        try:
            await self.channel_data.update_one(
                {"channel_id": channel_id},
                {
                    "$set": {
                        "channel_id": channel_id,
                        "req_encoded_link": encoded_link,
                        "status": "active",
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            logging.info(f"Saved req_encoded link for channel {channel_id}: {encoded_link}")
            return encoded_link
        except Exception as e:
            logging.error(f"Error saving secondary encoded link for channel {channel_id}: {e}")
            return None

    async def get_channel_by_encoded_link2(self, encoded_link: str) -> Optional[int]:
        """Get a channel ID by its secondary encoded link - with fallback decoding."""
        if not isinstance(encoded_link, str):
            logging.error("get_channel_by_encoded_link2: encoded_link is not a string")
            return None

        try:
            logging.info(f"[REQUEST LINK] Searching for channel with req_encoded_link: {encoded_link}")
            
            # First try: Search by req_encoded_link field
            channel = await self.channel_data.find_one({"req_encoded_link": encoded_link, "status": "active"})
            
            if channel and "channel_id" in channel:
                logging.info(f"[REQUEST LINK] Found channel by req_encoded_link: {channel['channel_id']}")
                return channel["channel_id"]
            
            # Second try: Decode the base64 string to get channel_id
            logging.warning(f"[REQUEST LINK] Not found in DB, trying to decode: {encoded_link}")
            try:
                # Use the same decoding method as helper_func.py
                base64_string = encoded_link.strip("=")
                base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
                string_bytes = base64.urlsafe_b64decode(base64_bytes)
                decoded_string = string_bytes.decode("ascii")
                decoded_id = int(decoded_string)
                logging.info(f"[REQUEST LINK] Successfully decoded channel_id: {decoded_id}")
                
                # Try to find channel by channel_id
                channel = await self.channel_data.find_one({"channel_id": decoded_id})
                
                if channel:
                    logging.info(f"[REQUEST LINK] Channel {decoded_id} exists in DB, updating req_encoded_link")
                    # Update the req_encoded_link field for this channel
                    await self.channel_data.update_one(
                        {"channel_id": decoded_id},
                        {
                            "$set": {
                                "req_encoded_link": encoded_link,
                                "status": "active",
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    return decoded_id
                else:
                    logging.warning(f"[REQUEST LINK] Channel {decoded_id} not found in DB, creating it")
                    # Create the channel entry using the same encoding
                    string_bytes = str(decoded_id).encode("ascii")
                    base64_bytes = base64.urlsafe_b64encode(string_bytes)
                    new_encoded_link = (base64_bytes.decode("ascii")).strip("=")
                    
                    await self.channel_data.update_one(
                        {"channel_id": decoded_id},
                        {
                            "$set": {
                                "channel_id": decoded_id,
                                "encoded_link": new_encoded_link,
                                "req_encoded_link": new_encoded_link,
                                "status": "active",
                                "created_at": datetime.utcnow()
                            }
                        },
                        upsert=True
                    )
                    return decoded_id
                    
            except Exception as decode_error:
                logging.error(f"[REQUEST LINK] Failed to decode base64 '{encoded_link}': {decode_error}")
            
            return None
            
        except Exception as e:
            logging.error(f"[REQUEST LINK] Error fetching channel by secondary encoded link {encoded_link}: {e}")
            return None

    async def save_invite_link(self, channel_id: int, invite_link: str, is_request: bool) -> bool:
        """Save the current invite link for a channel and its type."""
        if not isinstance(channel_id, int) or not isinstance(invite_link, str):
            logging.error(f"Invalid input: channel_id={channel_id}, invite_link={invite_link}")
            return False

        try:
            await self.channel_data.update_one(
                {"channel_id": channel_id},
                {
                    "$set": {
                        "current_invite_link": invite_link,
                        "is_request_link": is_request,
                        "invite_link_created_at": datetime.utcnow(),
                        "status": "active"
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logging.error(f"Error saving invite link for channel {channel_id}: {e}")
            return False

    async def get_current_invite_link(self, channel_id: int) -> Optional[dict]:
        """Get the current invite link and its type for a channel."""
        if not isinstance(channel_id, int):
            return None

        try:
            channel = await self.channel_data.find_one({"channel_id": channel_id, "status": "active"})
            if channel and "current_invite_link" in channel:
                return {
                    "invite_link": channel["current_invite_link"],
                    "is_request": channel.get("is_request_link", False)
                }
            return None
        except Exception as e:
            logging.error(f"Error fetching current invite link for channel {channel_id}: {e}")
            return None

    async def add_fsub_channel(self, channel_id: int) -> bool:
        """Add a channel to the FSub list."""
        if not isinstance(channel_id, int):
            logging.error(f"Invalid channel_id: {channel_id}")
            return False

        try:
            result = await self.fsub_data.update_one(
                {"channel_id": channel_id},
                {
                    "$set": {
                        "channel_id": channel_id,
                        "created_at": datetime.utcnow(),
                        "status": "active",
                        "mode": "off"
                    }
                },
                upsert=True
            )
            return result.matched_count == 0
        except Exception as e:
            logging.error(f"Error adding FSub channel {channel_id}: {e}")
            return False

    async def remove_fsub_channel(self, channel_id: int) -> bool:
        """Remove a channel from the FSub list."""
        try:
            result = await self.fsub_data.delete_one({"channel_id": channel_id})
            return result.deleted_count > 0
        except Exception as e:
            logging.error(f"Error removing FSub channel {channel_id}: {e}")
            return False

    async def get_fsub_channels(self) -> List[int]:
        """Get all active FSub channel IDs."""
        try:
            channels = await self.fsub_data.find({"status": "active"}).to_list(None)
            return [channel["channel_id"] for channel in channels if "channel_id" in channel]
        except Exception as e:
            logging.error(f"Error fetching FSub channels: {e}")
            return []

    async def get_channel_mode(self, channel_id: int):
        """Get current mode of a channel."""
        data = await self.fsub_data.find_one({'channel_id': channel_id})
        return data.get("mode", "off") if data else "off"

    async def set_channel_mode(self, channel_id: int, mode: str):
        """Set mode of a channel."""
        await self.fsub_data.update_one(
            {'channel_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )

    async def set_channel_mode_all(self, mode: str) -> dict:
        """
        Set mode for all FSub channels at once.

        Args:
            mode: The mode to set ('on' or 'off')

        Returns:
            dict: Result with success status and count of updated channels
        """
        try:
            # Validate mode
            if mode not in ['on', 'off']:
                logging.error(f"Invalid mode: {mode}. Must be 'on' or 'off'")
                return {
                    "success": False,
                    "updated_count": 0,
                    "message": "Invalid mode. Must be 'on' or 'off'"
                }

            # Update all active FSub channels
            result = await self.fsub_data.update_many(
                {"status": "active"},
                {
                    "$set": {
                        "mode": mode,
                        "mode_updated_at": datetime.utcnow()
                    }
                }
            )

            logging.info(f"Bulk mode update: Set {result.modified_count} channels to '{mode}' mode")

            return {
                "success": True,
                "updated_count": result.modified_count,
                "matched_count": result.matched_count,
                "message": f"Successfully set {result.modified_count} channel(s) to '{mode}' mode"
            }

        except Exception as e:
            logging.error(f"Error setting mode for all channels: {e}")
            return {
                "success": False,
                "updated_count": 0,
                "message": f"Error: {str(e)}"
            }

    async def get_channel_mode_all(self) -> dict:
        """
        Get the mode status of all FSub channels.

        Returns:
            dict: Contains mode statistics and list of channels with their modes
        """
        try:
            channels = await self.fsub_data.find({"status": "active"}).to_list(None)

            if not channels:
                return {
                    "success": True,
                    "total_channels": 0,
                    "on_count": 0,
                    "off_count": 0,
                    "channels": [],
                    "message": "No FSub channels found"
                }

            channel_modes = []
            on_count = 0
            off_count = 0

            for channel in channels:
                channel_id = channel.get("channel_id")
                mode = channel.get("mode", "off")

                if mode == "on":
                    on_count += 1
                else:
                    off_count += 1

                channel_modes.append({
                    "channel_id": channel_id,
                    "mode": mode
                })

            return {
                "success": True,
                "total_channels": len(channels),
                "on_count": on_count,
                "off_count": off_count,
                "channels": channel_modes,
                "message": f"Found {len(channels)} channel(s): {on_count} ON, {off_count} OFF"
            }

        except Exception as e:
            logging.error(f"Error getting mode for all channels: {e}")
            return {
                "success": False,
                "total_channels": 0,
                "on_count": 0,
                "off_count": 0,
                "channels": [],
                "message": f"Error: {str(e)}"
            }

    async def req_user(self, channel_id: int, user_id: int):
        """Add the user to the set of users for a specific channel."""
        try:
            await self.rqst_fsub_Channel_data.update_one(
                {'channel_id': int(channel_id)},
                {'$addToSet': {'user_ids': int(user_id)}},
                upsert=True
            )
        except Exception as e:
            logging.error(f"[DB ERROR] Failed to add user to request list: {e}")

    async def del_req_user(self, channel_id: int, user_id: int):
        """Remove a user from the channel set."""
        await self.rqst_fsub_Channel_data.update_one(
            {'channel_id': channel_id},
            {'$pull': {'user_ids': user_id}}
        )

    async def req_user_exist(self, channel_id: int, user_id: int):
        """Check if the user exists in the set of the channel's users."""
        try:
            found = await self.rqst_fsub_Channel_data.find_one({
                'channel_id': int(channel_id),
                'user_ids': int(user_id)
            })
            return bool(found)
        except Exception as e:
            logging.error(f"[DB ERROR] Failed to check request list: {e}")
            return False

    async def reqChannel_exist(self, channel_id: int):
        """Check if a channel exists using show_channels."""
        channel_ids = await self.show_channels()
        return channel_id in channel_ids

    async def get_original_link(self, channel_id: int) -> Optional[str]:
        """Get the original link stored for a channel (used by /genlink)."""
        if not isinstance(channel_id, int):
            return None
        try:
            channel = await self.channel_data.find_one({"channel_id": channel_id, "status": "active"})
            return channel.get("original_link") if channel else None
        except Exception as e:
            logging.error(f"Error fetching original link for channel {channel_id}: {e}")
            return None

    # =====================================================================
    # Compatibility / additional methods
    # (ported from KurumiFileStoreV2 so its plugins work against this DB)
    # =====================================================================

    async def present_user(self, user_id: int) -> bool:
        """Alias of is_user_exist, matching KurumiFileStoreV2's naming."""
        return await self.is_user_exist(user_id)

    async def del_user(self, user_id: int):
        """Alias of delete_user, matching KurumiFileStoreV2's naming."""
        await self.delete_user(user_id)

    async def full_userbase(self) -> List[int]:
        """Return every known user id (used by broadcast/users commands)."""
        try:
            docs = await self.user_data.find({}, {"_id": 1}).to_list(length=None)
            return [doc["_id"] for doc in docs]
        except Exception as e:
            logging.error(f"Error fetching full userbase: {e}")
            return []

    async def admin_exist(self, admin_id: int) -> bool:
        """Alias of is_admin, matching KurumiFileStoreV2's naming."""
        return await self.is_admin(admin_id)

    async def del_admin(self, admin_id: int) -> bool:
        """Alias of remove_admin, matching KurumiFileStoreV2's naming."""
        return await self.remove_admin(admin_id)

    async def get_all_admins(self) -> List[int]:
        """Alias of list_admins, matching KurumiFileStoreV2's naming."""
        return await self.list_admins()

    # ---- Auto-delete timer (used by /dlt_time & /check_dlt_time) ----
    async def set_del_timer(self, value: int):
        existing = await self.del_timer_data.find_one({})
        if existing:
            await self.del_timer_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.del_timer_data.insert_one({'value': value})

    async def get_del_timer(self) -> int:
        data = await self.del_timer_data.find_one({})
        if data:
            return data.get('value', 0)
        return 0

    # ---- Simple ban list (used by /ban /unban /banlist and shared with
    #      the ban_menu UI in plugins/settings.py — same ban_data collection
    #      and same ban_status.is_banned schema, just with helper wrappers) ----
    async def ban_user_exist(self, user_id: int) -> bool:
        doc = await self.ban_data.find_one({"_id": user_id})
        return bool(doc and doc.get("ban_status", {}).get("is_banned", False))

    async def add_ban_user(self, user_id: int, reason: str = "No reason provided"):
        await self.ban_data.update_one(
            {"_id": user_id},
            {"$set": {
                "ban_status.is_banned": True,
                "ban_status.ban_reason": reason,
                "ban_status.banned_on": date.today().isoformat(),
            }},
            upsert=True
        )

    async def del_ban_user(self, user_id: int):
        await self.ban_data.update_one(
            {"_id": user_id},
            {"$set": {
                "ban_status.is_banned": False,
                "ban_status.ban_reason": "",
                "ban_status.banned_on": None,
            }}
        )

    async def get_ban_users(self) -> List[int]:
        try:
            docs = await self.ban_data.find({"ban_status.is_banned": True}, {"_id": 1}).to_list(length=None)
            return [doc["_id"] for doc in docs]
        except Exception as e:
            logging.error(f"Error fetching banned users: {e}")
            return []

    # ------------------------------------------------------------------
    # Shortener settings — everything admin-manageable from inside the bot
    # ------------------------------------------------------------------
    DEFAULT_SHORTENER = {
        'enabled': False,
        'api_key': '',
        'site_url': 'shortxlinks.com/',
        'tutorial_url': 'https://t.me/+wekKcN1tjbAxY2U1',
        'message': (
            "<b><blockquote>ʏᴏᴜʀ ᴀᴅs ᴛᴏᴋᴇɴ ɪs ᴇxᴘɪʀᴇᴅ ᴘʟᴇᴀsᴇ ᴠᴇʀɪғʏ ᴛᴏ ʀᴇɢᴀɪɴ ᴀᴄᴄᴇss ᴛᴏ ᴛʜᴇ ʙᴏᴛs</blockquote>"
            "ᴡʜᴀᴛ ɪs ᴛʜᴇ ᴛᴏᴋᴇɴ?ᴛʜɪs ɪs ᴀɴ ᴀᴅs ᴛᴏᴋᴇɴ. ᴘᴀssɪɴɢ ᴏɴᴇ ᴀᴅ ᴀʟʟᴏᴡs ʏᴏᴜ ᴛᴏ ᴜsᴇ ᴛʜᴇ ᴏᴜʀ ʙᴏᴛs</b>"
        ),
        'protect_message': True,
        'validity_days': 1,
        'pic': None,
    }

    async def get_shortener_settings(self) -> dict:
        doc = await self.settings_data.find_one({'_id': 'shortener'})
        data = dict(self.DEFAULT_SHORTENER)
        if doc:
            data.update({k: v for k, v in doc.items() if k != '_id'})
        return data

    async def update_shortener_settings(self, **kwargs):
        if not kwargs:
            return
        await self.settings_data.update_one(
            {'_id': 'shortener'}, {'$set': kwargs}, upsert=True
        )

    # ------------------------------------------------------------------
    # Per-user shortener verification state
    # ------------------------------------------------------------------
    async def set_user_verified(self, user_id: int, expiry_ts: int):
        await self.verify_data.update_one(
            {'_id': user_id}, {'$set': {'expiry': expiry_ts}}, upsert=True
        )

    async def get_user_verify_expiry(self, user_id: int) -> int:
        doc = await self.verify_data.find_one({'_id': user_id})
        return doc.get('expiry', 0) if doc else 0

    # ------------------------------------------------------------------
    # Caption settings
    # ------------------------------------------------------------------
    DEFAULT_CAPTION_SETTINGS = {
        'enabled': False,
        'text': "{filename}",
    }

    async def get_caption_settings(self) -> dict:
        doc = await self.settings_data.find_one({'_id': 'caption'})
        data = dict(self.DEFAULT_CAPTION_SETTINGS)
        if doc:
            data.update({k: v for k, v in doc.items() if k != '_id'})
        return data

    async def update_caption_settings(self, **kwargs):
        if not kwargs:
            return
        await self.settings_data.update_one(
            {'_id': 'caption'}, {'$set': kwargs}, upsert=True
        )

    # ------------------------------------------------------------------
    # Premium / Pro users — bypass the shortener verification entirely.
    # Ported from KurumiFileStoreV2 (Yato branch) plugins/pro_users.py.
    # ------------------------------------------------------------------
    async def add_pro(self, user_id: int, expiry_date=None):
        await self.settings_data.update_one(
            {'_id': f'pro_{user_id}'},
            {'$set': {'user_id': user_id, 'type': 'pro', 'expiry': expiry_date}},
            upsert=True
        )

    async def remove_pro(self, user_id: int):
        await self.settings_data.delete_one({'_id': f'pro_{user_id}'})

    async def is_pro(self, user_id: int) -> bool:
        doc = await self.settings_data.find_one({'_id': f'pro_{user_id}'})
        if not doc:
            return False
        expiry = doc.get('expiry')
        if expiry and expiry < datetime.utcnow():
            await self.remove_pro(user_id)
            return False
        return True

    async def get_expiry_date(self, user_id: int):
        doc = await self.settings_data.find_one({'_id': f'pro_{user_id}'})
        return doc.get('expiry') if doc else None

    async def get_pros_list(self) -> List[int]:
        docs = await self.settings_data.find({'type': 'pro'}).to_list(length=None)
        return [d['user_id'] for d in docs]


Seishiro = Master(DB_URL, DB_NAME)
# Backward-compatible alias: KurumiFileStoreV2 plugins import `db` from
# database.database — point it at the same Seishiro instance so both
# bots' plugins share one live connection/state.
db = Seishiro
