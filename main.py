from flask import Flask, request
from pyrogram import Client, filters
from pymongo import MongoClient
import os

# 🔧 مشخصات ربات
API_ID = 2802662
API_HASH = "b8a41227faa1766d1dc3122e4c04c794"
BOT_TOKEN = "7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE"
OWNER_ID = 5637609683  # آیدی عددی صاحب ربات

# 🔧 مشخصات دیتابیس
MONGO_URL = "mongodb+srv://mohsenfeizi1386:p%40s%20sw0%20rd%279%27%21@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# ⚙️ اتصال به دیتابیس
mongo = MongoClient(MONGO_URL)
db = mongo["chatroom_db"]
users_col = db["users"]  # ذخیره اسم‌ها
banned_col = db["banned"]  # لیست بن شده‌ها

# ⚙️ کلاینت ربات
app = Client("chat_room_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ⚙️ سرور Flask برای هاست Render
server = Flask(__name__)

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    await message.reply("✅ ربات فعال است.")

# 🟢 روت اصلی هاست Render
@server.route("/", methods=["GET", "POST"])
def webhook():
    return "Online", 200

if __name__ == "__main__":
    # اجرای ربات
    app.start()
    print("ربات فعال شد ✅")

    # اجرای هاست Flask روی پورت 1000
    server.run(host="0.0.0.0", port=1000)
