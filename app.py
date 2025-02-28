from flask import Flask, Response
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.errors import UserIsBlocked
from pymongo import MongoClient

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
invites_collection = db["invites"]
forwarded_messages_collection = db["forwarded_messages"]
processed_messages_collection = db["processed_messages"]

# Create TTL index for auto-cleaning processed messages (7 days retention)
processed_messages_collection.create_index(
    "created_at",
    expireAfterSeconds=604800  # 7 days in seconds
)

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
    await client.send_message(
        ADMIN_ID,
        f"New user started the bot:\nID: {user_id}\nName: {user_name}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Accept User", callback_data=f"accept_{user_id}")],
            [InlineKeyboardButton("Reject User", callback_data=f"reject_{user_id}")]
        )
    )

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
        user_name = user.first_name
    except Exception as e:
        print(f"Error fetching user details: {e}")
        user_name = "Unknown User"

    # Delete the previous message sent to the admin
    await callback_query.message.delete()

    if data.startswith("accept"):
        # Generate invite links for all channels
        channels = channels_collection.find()
        invite_links = []
        for channel in channels:
            invite_link = await client.create_chat_invite_link(channel["channel_id"], member_limit=1)
            invite_links.append((channel["channel_name"], invite_link.invite_link))
            # Store the invite link in the database with the user ID
            invites_collection.insert_one({
                "invite_link": invite_link.invite_link,
                "channel_id": channel["channel_id"],
                "user_id": user_id,
                "created_at": datetime.now()
            })

        # Send invite links to the user
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(channel_name, url=invite_link)] for channel_name, invite_link in invite_links
        ])
        try:
            await client.send_message(user_id, "🟢 𝕮𝖔𝖓𝖌𝖗𝖆𝖙𝖚𝖑𝖆𝖙𝖎𝖔𝖓𝖘\n\n 𝐘𝐨𝐮𝐫 𝐫𝐞𝐪𝐮𝐞𝐬𝐭 𝐡𝐚𝐬 𝐛𝐞𝐞𝐧 𝐚𝐜𝐜𝐞𝐩𝐭𝐞𝐝 𝐚𝐧𝐝 𝐡𝐞𝐫𝐞 𝐚𝐫𝐞 𝐭𝐡𝐞 𝐢𝐧𝐯𝐢𝐭𝐞 𝐥𝐢𝐧𝐤𝐬 👇👇👇:", reply_markup=keyboard)
            await client.send_message(ADMIN_ID, f"User `{user_id}` with Name: `{user_name}` has received the acceptance message.")
        except UserIsBlocked:
            await client.send_message(ADMIN_ID, f"User `{user_id}` with Name: `{user_name}` has blocked the bot. Cannot send invite links.")

    elif data.startswith("reject"):
        keyboard1 = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("𝐋-𝐅𝐋𝐈𝐗 𝐀𝐃𝐌𝐈𝐍", url="https://t.me/lflixadmin")]
        ])
        try:
            await client.send_message(user_id, "⚠️ 𝐒𝐨𝐫𝐫𝐲 ❗️❗️ 😞😞 𝐘𝐨𝐮𝐫 𝐫𝐞𝐪𝐮𝐞𝐬𝐭 𝐡𝐚𝐬 𝐛𝐞𝐞𝐧 𝐫𝐞𝐣𝐞𝐜𝐭𝐞𝐝.\n\n ✅ 𝐘𝐨𝐮 𝐧𝐞𝐞𝐝 𝐭𝐨 𝐩𝐚𝐲 𝐲𝐨𝐮𝐫 𝐦𝐨𝐧𝐭𝐡𝐥𝐲 𝐬𝐮𝐛𝐬𝐜𝐫𝐢𝐩𝐭𝐢𝐨𝐧 𝐨𝐟 𝟓𝟎𝟎𝟎𝐔𝐆𝐗 𝐢𝐧 𝐨𝐫𝐝𝐞𝐫 𝐭𝐨 𝐠𝐞𝐭 𝐢𝐧𝐯𝐢𝐭𝐞𝐥𝐢𝐧𝐤𝐬\n\n ✅ 𝐏𝐀𝐘𝐌𝐄𝐍𝐓 : 𝟎𝟕𝟎𝟒𝟑𝟏𝟐𝟗𝟓𝟏(𝐀𝐧𝐝𝐫𝐞𝐰 𝐊𝐚𝐰𝐮𝐤𝐢)\n\n✅ 𝐒𝐞𝐧𝐝 𝐩𝐚𝐲𝐦𝐞𝐧𝐭 𝐯𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐭𝐢𝐨𝐧 𝐡𝐞𝐫𝐞 👇:", reply_markup=keyboard1)
            await client.send_message(ADMIN_ID, f"User `{user_id}` with Name: `{user_name}` has received the rejection message.")
        except UserIsBlocked:
            await client.send_message(ADMIN_ID, f"User `{user_id}` with Name: `{user_name}` has blocked the bot. Cannot send rejection message.")

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
            except Exception as e:
                print(f"Failed to revoke invite link {invite['invite_link']}: {e}")

        await asyncio.sleep(600)

# Command to add a channel
@app.on_message(filters.command("addchannel") & filters.user(ADMIN_ID))
async def add_channel(client: Client, message: Message):
    if message.reply_to_message and message.reply_to_message.forward_from_chat:
        channel_id = message.reply_to_message.forward_from_chat.id
        channel_name = message.reply_to_message.forward_from_chat.title

        if channels_collection.find_one({"channel_id": channel_id}):
            await message.reply("Channel already added.")
        else:
            channels_collection.insert_one({"channel_id": channel_id, "channel_name": channel_name})
            await message.reply(f"Channel '{channel_name}' added successfully.")
    else:
        await message.reply("Please forward a message from the channel you want to add.")

# Command to remove a channel
@app.on_message(filters.command("removechannel") & filters.user(ADMIN_ID))
async def remove_channel(client: Client, message: Message):
    if message.reply_to_message and message.reply_to_message.forward_from_chat:
        channel_id = message.reply_to_message.forward_from_chat.id

        result = channels_collection.delete_one({"channel_id": channel_id})
        if result.deleted_count > 0:
            await message.reply("Channel removed successfully.")
        else:
            await message.reply("Channel not found.")
    else:
        await message.reply("Please forward a message from the channel you want to remove.")

# Command to list all channels
@app.on_message(filters.command("listchannels") & filters.user(ADMIN_ID))
async def list_channels(client: Client, message: Message):
    channels = channels_collection.find()
    if channels:
        channel_list = "\n".join([f"{channel['channel_name']} (ID: {channel['channel_id']})" for channel in channels])
        await message.reply(f"Added channels:\n{channel_list}")
    else:
        await message.reply("No channels added.")

# Command to set removal date for a user
@app.on_message(filters.command("setremoval") & filters.user(ADMIN_ID))
async def set_removal(client: Client, message: Message):
    if len(message.command) > 2:
        user_id = int(message.command[1])
        days = int(message.command[2])
        removal_date = datetime.now() + timedelta(days=days)
        warn_date = removal_date - timedelta(days=1)

        removal_date_str = removal_date.strftime("%Y-%m-%d at %H:%M:%S")

        users_collection.update_one({"user_id": user_id}, {"$set": {"removal_date": removal_date, "warn_date": warn_date}}, upsert=True)

        try:
            await client.send_message(user_id, f"You will be removed from the channel on {removal_date_str}.")
        except UserIsBlocked:
            await client.send_message(ADMIN_ID, f"User {user_id} has blocked the bot. Cannot send removal date notification.")
        await message.reply(f"Removal date set for user {user_id} on {removal_date_str}.")
    else:
        await message.reply("Usage: /setremoval <user_id> <days>")

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
                    # Revoke invite links
                    invites = invites_collection.find({"channel_id": channel["channel_id"], "user_id": user_id})
                    for invite in invites:
                        await app.revoke_chat_invite_link(channel["channel_id"], invite["invite_link"])
                        invites_collection.delete_one({"_id": invite["_id"]})

                    # Ban and unban to remove from channel
                    await app.ban_chat_member(chat_id=channel["channel_id"], user_id=user_id)
                    await app.unban_chat_member(chat_id=channel["channel_id"], user_id=user_id)
                except Exception as e:
                    print(f"Failed to process user {user_id} in channel {channel['channel_id']}: {e}")

            try:
                await app.send_message(chat_id=user_id, text="You have been removed from the L-FLIX 👑 Premium channels.\n\n Contact admin 👉 @lflixadmin")
            except UserIsBlocked:
                await app.send_message(ADMIN_ID, f"User {user_id} has blocked the bot. Cannot send removal notification.")
            except Exception as e:
                print(f"Failed to send message to {user_id}: {e}")

            # Delete user record
            users_collection.delete_one({"user_id": user_id})

        await asyncio.sleep(60)

# Command to broadcast message to all users
@app.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast(client: Client, message: Message):
    if message.reply_to_message:
        users = users_collection.find()
        for user in users:
            try:
                await message.reply_to_message.copy(user["user_id"])
            except UserIsBlocked:
                continue
            except Exception as e:
                print(f"Failed to send broadcast to {user['user_id']}: {e}")
        await message.reply("Broadcast sent to all users.")
    else:
        await message.reply("Please reply to a message to broadcast it.")

# Handle user messages with duplication check
@app.on_message(filters.private & ~filters.command("start"))
async def forward_user_message(client: Client, message: Message):
    if message.from_user.id != ADMIN_ID:
        # Check for existing processed message
        if processed_messages_collection.find_one({"message_id": message.id}):
            print(f"Message {message.id} already processed.")
            return

        # Forward to admin and store metadata
        forwarded_message = await message.forward(ADMIN_ID)
        forwarded_messages_collection.insert_one({
            "forwarded_message_id": forwarded_message.id,
            "user_id": message.from_user.id
        })

        # Mark as processed with timestamp
        processed_messages_collection.insert_one({
            "message_id": message.id,
            "created_at": datetime.now()
        })
        print(f"Message {message.id} processed and forwarded.")

        await message.reply("𝒀𝒐𝒖𝒓 𝒎𝒆𝒔𝒔𝒂𝒈𝒆 𝒉𝒂𝒔 𝒃𝒆𝒆𝒏 𝒇𝒐𝒓𝒘𝒂𝒓𝒅𝒆𝒅 𝒕𝒐 𝒕𝒉𝒆 𝒂𝒅𝒎𝒊𝒏. 👍")

# Handle admin replies to forwarded messages
@app.on_message(filters.private & filters.user(ADMIN_ID) & filters.reply)
async def admin_reply(client: Client, message: Message):
    forwarded_message = forwarded_messages_collection.find_one(
        {"forwarded_message_id": message.reply_to_message.id}
    )
    
    if forwarded_message:
        try:
            await client.send_message(
                forwarded_message["user_id"],
                message.text
            )
            await message.reply("Reply sent to user.")
        except UserIsBlocked:
            await message.reply("❌ User has blocked the bot.")
    else:
        await message.reply("⚠️ No linked user found for this message.")

# Server initialization
if __name__ == "__main__":
    # Start Flask server in separate thread
    from threading import Thread
    flask_thread = Thread(target=lambda: flask_app.run(host='0.0.0.0', port=8000))
    flask_thread.daemon = True
    flask_thread.start()

    # Start Pyrogram client
    app.start()
    
    # Start background tasks
    loop = asyncio.get_event_loop()
    loop.create_task(check_and_remove_users())
    loop.create_task(revoke_expired_invites())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()
