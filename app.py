import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.errors import UserIsBlocked
from pymongo import MongoClient
from flask import Flask, jsonify  # Import Flask and jsonify

# Load environment variables
load_dotenv()

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

# Initialize Flask app
flask_app = Flask(__name__)

# Health check route
@flask_app.route('/health', methods=['GET'])
def health_check():
    return jsonify(status="OK"), 200  # Always return 200 OK

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
        ])
    )

    await message.reply("𝐘𝐨𝐮𝐫 𝐫𝐞𝐪𝐮𝐞𝐬𝐭 𝐡𝐚𝐬 𝐛𝐞𝐞𝐧 𝐬𝐞𝐧𝐭 𝐭𝐨 𝐋-𝐅𝐋𝐈𝐗 𝐀𝐃𝐌𝐈𝐍, 𝐚𝐧𝐝 𝐩𝐥𝐞𝐚𝐬𝐞 𝐰𝐚𝐢𝐭 𝐟𝐨𝐫 𝐚𝐩𝐩𝐫𝐨𝐯𝐚𝐥.\n\n 𝐓𝐡𝐚𝐧𝐤 𝐲𝐨𝐮 🤝🤝")

# (Rest of your existing code remains unchanged)

# Run the bot and Flask server
if __name__ == "__main__":
    # Start the Pyrogram client
    app.start()

    # Start background tasks after the client is initialized
    loop = asyncio.get_event_loop()
    loop.create_task(check_and_remove_users())
    loop.create_task(revoke_expired_invites())

    # Start Flask server
    flask_app.run(host='0.0.0.0', port=8000)  # Run Flask on TCP port 8000

    # Keep the bot running
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # Stop the Pyrogram client
        app.stop()
