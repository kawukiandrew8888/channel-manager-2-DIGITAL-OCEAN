import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.errors import UserIsBlocked, FloodWait
from pymongo import MongoClient
from flask import Flask, Response

# Load environment variables
load_dotenv()

# Initialize Flask app
flask_app = Flask(__name__)

# Health check endpoint
@flask_app.route('/health')
def health_check():
    return Response("OK", status=200)

# Initialize MongoDB client
mongo_client = MongoClient(os.getenv("MONGO_URI"))
db = mongo_client["channel_manager"]
users_collection = db["users"]
channels_collection = db["channels"]
invites_collection = db["invites"]  # Collection for invite links
forwarded_messages_collection = db["forwarded_messages"]  # Collection for forwarded messages

# Initialize Pyrogram client
app = Client(
    "channel_manager_bot",
    api_id=os.getenv("API_ID"),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN")
)

# Admin ID
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Command to start the bot
@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    # Notify admin
    try:
        await client.send_message(
            ADMIN_ID,
            f"New user started the bot:\nID: {user_id}\nName: {user_name}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Accept User", callback_data=f"accept_{user_id}")],
                [InlineKeyboardButton("Reject User", callback_data=f"reject_{user_id}")]
            )]
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)  # Wait for the specified duration
        await start(client, message)  # Retry the function
    except Exception as e:
        print(f"Error in start command: {e}")

    await message.reply("𝐘𝐨𝐮𝐫 𝐫𝐞𝐪𝐮𝐞𝐬𝐭 𝐡𝐚𝐬 𝐛𝐞𝐞𝐧 𝐬𝐞𝐧𝐭 𝐭𝐨 𝐋-𝐅𝐋𝐈𝐗 𝐀𝐃𝐌𝐈𝐍, 𝐚𝐧𝐝 𝐩𝐥𝐞𝐚𝐬𝐞 𝐰𝐚𝐢𝐭 𝐟𝐨𝐫 𝐚𝐩𝐩𝐫𝐨𝐯𝐚𝐥.\n\n 𝐓𝐡𝐚𝐧𝐤 𝐲𝐨𝐮 🤝🤝")

# Callback query handler
@app.on_callback_query()
async def callback_query_handler(client: Client, callback_query: CallbackQuery):
    # Extract the user_id from the callback data
    data = callback_query.data
    user_id = int(data.split("_")[1])

    # Fetch the user's details using the user_id
    try:
        user = await client.get_users(user_id)
        user_name = user.first_name  # Get the user's first name
    except Exception as e:
        print(f"Error fetching user details: {e}")
        user_name = "Unknown User"  # Fallback in case of an error

    # Delete the previous message sent to the admin
    try:
        await callback_query.message.delete()
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await callback_query.message.delete()
    except Exception as e:
        print(f"Error deleting message: {e}")

    if data.startswith("accept"):
        # Generate invite links for all channels
        channels = channels_collection.find()
        invite_links = []
        for channel in channels:
            try:
                invite_link = await client.create_chat_invite_link(channel["channel_id"], member_limit=1)
                invite_links.append((channel["channel_name"], invite_link.invite_link))
                # Store the invite link in the database with the user ID
                invites_collection.insert_one({
                    "invite_link": invite_link.invite_link,
                    "channel_id": channel["channel_id"],
                    "user_id": user_id,  # Store the user ID
                    "created_at": datetime.now()
                })
            except FloodWait as e:
                await asyncio.sleep(e.value)
                continue  # Retry the loop iteration
            except Exception as e:
                print(f"Error creating invite link: {e}")

        # Send invite links to the user
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(channel_name, url=invite_link)] for channel_name, invite_link in invite_links
        ])
        try:
            await client.send_message(user_id, "🟢 𝕮𝖔𝖓𝖌𝖗𝖆𝖙𝖚𝖑𝖆𝖙𝖎𝖔𝖓𝖘\n\n 𝐘𝐨𝐮𝐫 𝐫𝐞𝐪𝐮𝐞𝐬𝐭 𝐡𝐚𝐬 𝐛𝐞𝐞𝐧 𝐚𝐜𝐜𝐞𝐩𝐭𝐞𝐝 𝐚𝐧𝐝 𝐡𝐞𝐫𝐞 𝐚𝐫𝐞 𝐭𝐡𝐞 𝐢𝐧𝐯𝐢𝐭𝐞 𝐥𝐢𝐧𝐤𝐬 👇👇👇:", reply_markup=keyboard)
            # Send confirmation to admin
            await client.send_message(ADMIN_ID, f"User `{user_id}` with Name: `{user_name}` has received the acceptance message.")
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await callback_query_handler(client, callback_query)  # Retry the function
        except UserIsBlocked:
            await client.send_message(ADMIN_ID, f"User `{user_id}` with Name: `{user_name}` has blocked the bot. Cannot send invite links.")
        except Exception as e:
            print(f"Error sending acceptance message: {e}")

    elif data.startswith("reject"):
        keyboard1 = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("𝐋-𝐅𝐋𝐈𝐗 𝐀𝐃𝐌𝐈𝐍", url="https://t.me/lflixadmin")]
        ])
        try:
            await client.send_message(user_id, "⚠️ 𝐒𝐨𝐫𝐫𝐲 ❗️❗️ 😞😞 𝐘𝐨𝐮𝐫 𝐫𝐞𝐪𝐮𝐞𝐬𝐭 𝐡𝐚𝐬 𝐛𝐞𝐞𝐧 𝐫𝐞𝐣𝐞𝐜𝐭𝐞𝐝.\n\n ✅ 𝐘𝐨𝐮 𝐧𝐞𝐞𝐝 𝐭𝐨 𝐩𝐚𝐲 𝐲𝐨𝐮𝐫 𝐦𝐨𝐧𝐭𝐡𝐥𝐲 𝐬𝐮𝐛𝐬𝐜𝐫𝐢𝐩𝐭𝐢𝐨𝐧 𝐨𝐟 𝟓𝟎𝟎𝟎𝐔𝐆𝐗 𝐢𝐧 𝐨𝐫𝐝𝐞𝐫 𝐭𝐨 𝐠𝐞𝐭 𝐢𝐧𝐯𝐢𝐭𝐞𝐥𝐢𝐧𝐤𝐬\n\n ✅ 𝐏𝐀𝐘𝐌𝐄𝐍𝐓 : 𝟎𝟕𝟎𝟒𝟑𝟏𝟐𝟗𝟓𝟏(𝐀𝐧𝐝𝐫𝐞𝐰 𝐊𝐚𝐰𝐮𝐤𝐢)\n\n✅ 𝐒𝐞𝐧𝐝 𝐩𝐚𝐲𝐦𝐞𝐧𝐭 𝐯𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐭𝐢𝐨𝐧 𝐡𝐞𝐫𝐞 👇:", reply_markup=keyboard1)
            # Send confirmation to admin
            await client.send_message(ADMIN_ID, f"User `{user_id}` with Name: `{user_name}` has received the rejection message.")
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await callback_query_handler(client, callback_query)  # Retry the function
        except UserIsBlocked:
            await client.send_message(ADMIN_ID, f"User `{user_id}` with Name: `{user_name}` has blocked the bot. Cannot send rejection message.")
        except Exception as e:
            print(f"Error sending rejection message: {e}")

    await callback_query.answer()

# Function to revoke expired invite links
async def revoke_expired_invites():
    while True:
        now = datetime.now()
        expired_invites = invites_collection.find({"created_at": {"$lte": now - timedelta(hours=1)}})

        for invite in expired_invites:
            try:
                await app.revoke_chat_invite_link(invite["channel_id"], invite["invite_link"])
                invites_collection.delete_one({"_id": invite["_id"]})
                print(f"Revoked expired invite link: {invite['invite_link']}")
            except FloodWait as e:
                await asyncio.sleep(e.value)
                continue  # Retry the loop iteration
            except Exception as e:
                print(f"Failed to revoke invite link {invite['invite_link']}: {e}")

        await asyncio.sleep(600)  # Check every 10 minutes

# Command to add a channel
@app.on_message(filters.command("addchannel") & filters.user(ADMIN_ID))
async def add_channel(client: Client, message: Message):
    if message.reply_to_message and message.reply_to_message.forward_from_chat:
        channel_id = message.reply_to_message.forward_from_chat.id
        channel_name = message.reply_to_message.forward_from_chat.title

        # Check if channel already exists
        if channels_collection.find_one({"channel_id": channel_id}):
            await message.reply("Channel already added.")
        else:
            channels_collection.insert_one({"channel_id": channel_id, "channel_name": channel_name})
            try:
                await message.reply(f"Channel '{channel_name}' added successfully.")
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await add_channel(client, message)  # Retry the function
            except Exception as e:
                print(f"Error adding channel: {e}")
    else:
        try:
            await message.reply("Please forward a message from the channel you want to add.")
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await add_channel(client, message)  # Retry the function
        except Exception as e:
            print(f"Error sending message: {e}")

# Command to remove a channel
@app.on_message(filters.command("removechannel") & filters.user(ADMIN_ID))
async def remove_channel(client: Client, message: Message):
    if message.reply_to_message and message.reply_to_message.forward_from_chat:
        channel_id = message.reply_to_message.forward_from_chat.id

        # Remove channel from database
        result = channels_collection.delete_one({"channel_id": channel_id})
        if result.deleted_count > 0:
            try:
                await message.reply("Channel removed successfully.")
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await remove_channel(client, message)  # Retry the function
            except Exception as e:
                print(f"Error removing channel: {e}")
        else:
            try:
                await message.reply("Channel not found.")
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await remove_channel(client, message)  # Retry the function
            except Exception as e:
                print(f"Error sending message: {e}")
    else:
        try:
            await message.reply("Please forward a message from the channel you want to remove.")
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await remove_channel(client, message)  # Retry the function
        except Exception as e:
            print(f"Error sending message: {e}")

# Command to list all channels
@app.on_message(filters.command("listchannels") & filters.user(ADMIN_ID))
async def list_channels(client: Client, message: Message):
    channels = channels_collection.find()
    if channels:
        channel_list = "\n".join([f"{channel['channel_name']} (ID: {channel['channel_id']})" for channel in channels])
        try:
            await message.reply(f"Added channels:\n{channel_list}")
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await list_channels(client, message)  # Retry the function
        except Exception as e:
            print(f"Error listing channels: {e}")
    else:
        try:
            await message.reply("No channels added.")
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await list_channels(client, message)  # Retry the function
        except Exception as e:
            print(f"Error sending message: {e}")

# Command to set removal date for a user based on number of days
@app.on_message(filters.command("setremoval") & filters.user(ADMIN_ID))
async def set_removal(client: Client, message: Message):
    if len(message.command) > 2:
        user_id = int(message.command[1])
        days = int(message.command[2])
        removal_date = datetime.now() + timedelta(days=days)
        warn_date = removal_date - timedelta(days=1)

        # Format the removal date to include both date and time
        removal_date_str = removal_date.strftime("%Y-%m-%d at %H:%M:%S")

        # Update user's removal date
        users_collection.update_one({"user_id": user_id}, {"$set": {"removal_date": removal_date, "warn_date": warn_date}}, upsert=True)

        # Notify user with the actual date and time of removal
        try:
            await client.send_message(user_id, f"You will be removed from the channel on {removal_date_str}.")
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await set_removal(client, message)  # Retry the function
        except UserIsBlocked:
            await client.send_message(ADMIN_ID, f"User {user_id} has blocked the bot. Cannot send removal date notification.")
        except Exception as e:
            print(f"Error sending removal date: {e}")
        await message.reply(f"Removal date set for user {user_id} on {removal_date_str}.")
    else:
        try:
            await message.reply("Usage: /setremoval <user_id> <days>")
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await set_removal(client, message)  # Retry the function
        except Exception as e:
            print(f"Error sending message: {e}")

# Function to check and remove users
async def check_and_remove_users():
    while True:
        now = datetime.now()
        users_to_warn = users_collection.find({"warn_date": {"$lte": now}, "warned": {"$exists": False}})
        users_to_remove = users_collection.find({"removal_date": {"$lte": now}})

        # Warn users 24 hours before removal
        for user in users_to_warn:
            user_id = user["user_id"]
            try:
                await app.send_message(chat_id=user_id, text="⚠️ You will be removed from L-FLIX 👑 Premium channel in 24 hours.\n\n Contact admin 👉 @lflixadmin")
                users_collection.update_one({"user_id": user_id}, {"$set": {"warned": True}})
            except FloodWait as e:
                await asyncio.sleep(e.value)
                continue  # Retry the loop iteration
            except UserIsBlocked:
                await app.send_message(ADMIN_ID, f"User {user_id} has blocked the bot. Cannot send warning.")
            except Exception as e:
                print(f"Failed to send warning to {user_id}: {e}")

        # Remove users
        for user in users_to_remove:
            user_id = user["user_id"]
            channels = channels_collection.find()

            for channel in channels:
                try:
                    # Find all invite links associated with the user for this channel
                    invites = invites_collection.find({"channel_id": channel["channel_id"], "user_id": user_id})
                    for invite in invites:
                        # Revoke the invite link before banning the user
                        await app.revoke_chat_invite_link(channel["channel_id"], invite["invite_link"])
                        invites_collection.delete_one({"_id": invite["_id"]})
                        print(f"Revoked invite link for user {user_id} in channel {channel['channel_id']}: {invite['invite_link']}")

                    # Ban the user
                    await app.ban_chat_member(chat_id=channel["channel_id"], user_id=user_id)
                    print(f"Banned user {user_id} from channel {channel['channel_id']}")

                    # Unban the user to remove them from the banned list
                    await app.unban_chat_member(chat_id=channel["channel_id"], user_id=user_id)
                    print(f"Unbanned user {user_id} from channel {channel['channel_id']}")
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    continue  # Retry the loop iteration
                except Exception as e:
                    print(f"Failed to process user {user_id} in channel {channel['channel_id']}: {e}")

            try:
                await app.send_message(chat_id=user_id, text="You have been removed from the L-FLIX 👑 Premium channels.\n\n Contact admin 👉 @lflixadmin")
            except FloodWait as e:
                await asyncio.sleep(e.value)
                continue  # Retry the loop iteration
            except UserIsBlocked:
                await app.send_message(ADMIN_ID, f"User {user_id} has blocked the bot. Cannot send removal notification.")
            except Exception as e:
                print(f"Failed to send message to {user_id}: {e}")

            # Delete the user from the users collection
            users_collection.delete_one({"user_id": user_id})

        await asyncio.sleep(60)  # Check every minute

# Command to broadcast a message to all users
@app.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast(client: Client, message: Message):
    if message.reply_to_message:
        users = users_collection.find()
        for user in users:
            try:
                await message.reply_to_message.copy(user["user_id"])
            except FloodWait as e:
                await asyncio.sleep(e.value)
                continue  # Retry the loop iteration
            except UserIsBlocked:
                continue  # Skip users who have blocked the bot
            except Exception as e:
                print(f"Failed to send broadcast to {user['user_id']}: {e}")
        try:
            await message.reply("Broadcast sent to all users.")
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await broadcast(client, message)  # Retry the function
        except Exception as e:
            print(f"Error sending broadcast confirmation: {e}")
    else:
        try:
            await message.reply("Please reply to a message to broadcast it.")
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await broadcast(client, message)  # Retry the function
        except Exception as e:
            print(f"Error sending message: {e}")

# Handle user messages and forward them to the admin
@app.on_message(filters.private & ~filters.command("start"))
async def forward_user_message(client: Client, message: Message):
    if message.from_user.id != ADMIN_ID:
        # Forward the message to the admin
        try:
            forwarded_message = await message.forward(ADMIN_ID)
            # Store the user ID with the forwarded message ID in the database
            forwarded_messages_collection.insert_one({
                "forwarded_message_id": forwarded_message.id,
                "user_id": message.from_user.id
            })
            await message.reply("𝒀𝒐𝒖𝒓 𝒎𝒆𝒔𝒔𝒂𝒈𝒆 𝒉𝒂𝒔 𝒃𝒆𝒆𝒏 𝒇𝒐𝒓𝒘𝒂𝒓𝒅𝒆𝒅 𝒕𝒐 𝒕𝒉𝒆 𝒂𝒅𝒎𝒊𝒏. 👍")
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await forward_user_message(client, message)  # Retry the function
        except Exception as e:
            print(f"Error forwarding message: {e}")

# Handle admin replies to user messages
@app.on_message(filters.private & filters.user(ADMIN_ID) & filters.reply)
async def admin_reply(client: Client, message: Message):
    # Get the forwarded message ID from the reply
    forwarded_message_id = message.reply_to_message.id
    print(f"Admin replied to message ID: {forwarded_message_id}")  # Debug log

    # Retrieve the user ID from the database
    forwarded_message = forwarded_messages_collection.find_one({"forwarded_message_id": forwarded_message_id})
    
    if forwarded_message:
        user_id = forwarded_message["user_id"]
        print(f"Found user ID: {user_id} for forwarded message ID: {forwarded_message_id}")  # Debug log

        try:
            # Send the admin's reply as a new message to the user
            await client.send_message(user_id, message.text)
            await message.reply("Your reply has been sent to the user.")
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await admin_reply(client, message)  # Retry the function
        except UserIsBlocked:
            await message.reply("The user has blocked the bot. Cannot send the reply.")
        except Exception as e:
            await message.reply(f"Failed to send the reply: {e}")
    else:
        print(f"No forwarded message found for ID: {forwarded_message_id}")  # Debug log
        try:
            await message.reply("Please reply to a forwarded message to reply to the user.")
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await admin_reply(client, message)  # Retry the function
        except Exception as e:
            print(f"Error sending message: {e}")

# Run the bot and Flask server
if __name__ == "__main__":
    # Start the Flask server in a separate thread
    from threading import Thread
    flask_thread = Thread(target=lambda: flask_app.run(host='0.0.0.0', port=8000))
    flask_thread.daemon = True
    flask_thread.start()

    # Start the Pyrogram client
    app.start()

    # Start background tasks after the client is initialized
    loop = asyncio.get_event_loop()
    loop.create_task(check_and_remove_users())
    loop.create_task(revoke_expired_invites())

    # Keep the bot running
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # Stop the Pyrogram client
        app.stop()
