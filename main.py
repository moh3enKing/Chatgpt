import os
from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from flask import Flask, request
from pymongo import MongoClient
import re

# ------------------- تنظیمات اولیه -------------------
API_ID = 123456     # از my.telegram.org بگیر
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "توکن شما"
ADMIN_ID = 5637609683
JOIN_CHANNEL = "netgoris"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"
MONGODB_URI = "mongodb+srv://mohsenfeizi1386:p%40ssw0rd%279%27%21@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# ------------------- اتصال به دیتابیس -------------------
mongo = MongoClient(MONGODB_URI)
db = mongo.chatroom
users = db.users
settings = db.settings

# ------------------- ربات تلگرام -------------------
bot = Client("anon_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ------------------- وب هوک برای Render -------------------
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot Running"

@app.route("/" + BOT_TOKEN, methods=["POST"])
def webhook():
    update = request.get_json()
    bot.process_update(update)
    return "OK"

# ------------------- کیبوردها -------------------

def join_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{JOIN_CHANNEL}")],
        [InlineKeyboardButton("✅ عضویت انجام شد", callback_data="check_join")]
    ])

def rules_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 قوانین", callback_data="show_rules")]
    ])

def confirm_rules_keyboard():
    return types.ReplyKeyboardMarkup([[types.KeyboardButton("✅ تایید قوانین")]], resize_keyboard=True)

# ------------------- متن قوانین -------------------

RULES_TEXT = """
سلام کاربر عزیز 👤  
به ربات Chat Room خوش آمدید.

در اینجا می‌توانید به‌صورت ناشناس با سایر کاربران گفتگو کنید، اما رعایت قوانین الزامی است:

1. استفاده فقط برای چت و سرگرمی است. تبلیغات و درخواست مالی ممنوع!
2. ارسال گیف مجاز نیست. عکس، موسیقی و... بلامانع؛ محتوای غیر اخلاقی ممنوع!
3. اسپم ممنوع. در صورت اسپم، سکوت ۲ دقیقه‌ای دریافت می‌کنید.
4. احترام الزامی است. برای گزارش فحاشی یا محتوای خلاف، پیام را ریپلای و دستور «گزارش» ارسال کنید.

با تایید قوانین، نام خود را (به انگلیسی) برای شروع چت ارسال کنید.
"""

# ------------------- بررسی عضویت در کانال -------------------

async def is_joined(user_id):
    try:
        member = await bot.get_chat_member(JOIN_CHANNEL, user_id)
        return member.status in ["member", "creator", "administrator"]
    except:
        return False

# ------------------- استارت -------------------

@bot.on_message(filters.command("start"))
async def start(client, message):
    user = users.find_one({"_id": message.from_user.id})

    if not user:
        await message.reply("برای استفاده از ربات ابتدا در کانال عضو شوید 👇", reply_markup=join_keyboard())
    else:
        await message.reply("👋 قبلاً ثبت‌نام کرده‌اید، خوش آمدید!\nمی‌توانید شروع به چت کنید.")

# ------------------- بررسی عضویت -------------------

@bot.on_callback_query(filters.regex("check_join"))
async def check_join(client, callback_query):
    user_id = callback_query.from_user.id
    if await is_joined(user_id):
        await callback_query.message.delete()
        await callback_query.message.reply("✅ اکنون قوانین را مشاهده و تایید کنید:", reply_markup=rules_keyboard())
    else:
        await callback_query.answer("⛔️ هنوز عضو کانال نشده‌اید.", show_alert=True)

# ------------------- نمایش قوانین -------------------

@bot.on_callback_query(filters.regex("show_rules"))
async def show_rules(client, callback_query):
    await callback_query.message.edit_text(RULES_TEXT)
    await bot.send_message(callback_query.from_user.id, "📌 لطفاً قوانین را تایید کنید.", reply_markup=confirm_rules_keyboard())

# ------------------- تایید قوانین و دریافت نام -------------------

@bot.on_message(filters.text("✅ تایید قوانین"))
async def confirm_rules(client, message):
    await message.reply("لطفاً یک نام انگلیسی برای خود وارد کنید (نباید شامل admin باشد):")
    users.update_one({"_id": message.from_user.id}, {"$set": {"stage": "name"}}, upsert=True)

@bot.on_message(filters.private & filters.text)
async def handle_name_or_message(client, message):
    user = users.find_one({"_id": message.from_user.id}) or {}
    stage = user.get("stage")

    if stage == "name":
        name = message.text.strip()
        if not re.match(r"^[A-Za-z0-9 _-]{3,20}$", name) or "admin" in name.lower():
            await message.reply("❌ نام نامعتبر است یا شامل 'admin' می‌باشد. دوباره تلاش کنید.")
            return
        if re.search(r"[\u0600-\u06FF]", name):
            await message.reply("⚠️ لطفاً فقط از حروف انگلیسی استفاده کنید.")
            return

        users.update_one({"_id": message.from_user.id}, {"$set": {"name": name, "stage": None, "banned": False}})
        await message.reply(f"✅ نام شما با موفقیت ثبت شد: **{name}**\nاکنون می‌توانید چت را آغاز کنید.")

    elif not user.get("banned", False):
        if not user.get("name"):
            await message.reply("⛔️ ابتدا باید قوانین را تایید و نام وارد کنید.")
            return

        if message.media and message.document and message.document.mime_type == "video/mp4":
            await message.reply("❌ ارسال گیف ممنوع است.")
            return

        forward_text = f"👤 {user['name']}\n\n{message.text}"
        for u in users.find({"banned": False}):
            try:
                await bot.send_message(u["_id"], forward_text, reply_to_message_id=None)
            except:
                pass

# ------------------- مدیریت -------------------

@bot.on_message(filters.user(ADMIN_ID) & filters.reply)
async def admin_commands(client, message):
    command = message.text.lower()
    target_id = message.reply_to_message.from_user.id

    if command == "بن":
        users.update_one({"_id": target_id}, {"$set": {"banned": True}})
        await message.reply("❌ کاربر بن شد.")
    elif command == "آنبن":
        users.update_one({"_id": target_id}, {"$set": {"banned": False}})
        await message.reply("✅ کاربر آزاد شد.")
    elif command == "خاموش":
        settings.update_one({"_id": "bot"}, {"$set": {"on": False}}, upsert=True)
        await message.reply("⛔️ ربات خاموش شد.")
    elif command == "روشن":
        settings.update_one({"_id": "bot"}, {"$set": {"on": True}}, upsert=True)
        await message.reply("✅ ربات فعال شد.")

# ------------------- راه‌اندازی -------------------

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    # تنظیم Webhook برای Render
    bot.run()
