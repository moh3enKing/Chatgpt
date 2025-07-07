import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from flask import Flask, request
import requests
from pymongo import MongoClient
from datetime import datetime, timedelta
import re
import os
import logging
import ssl

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تنظیمات ربات
TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
ADMIN_ID = 5637609683
CHANNEL_ID = "@netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0&tls=true&tlsAllowInvalidCertificates=true"
WEBHOOK_URL = f"https://chatgpt-qg71.onrender.com/{TOKEN}"

# وب‌سرویس‌ها
CHAT_APIS = [
    "https://starsshoptl.ir/Ai/index.php?text={}",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text={}",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text={}"
]
INSTAGRAM_API = "https://pouriam.top/eyephp/instagram?url={}"
SPOTIFY_API = "http://api.cactus-dev.ir/spotify.php?url={}"
PINTEREST_API = "https://haji.s2025h.space/pin/?url={}&client_key=keyvip"
IMAGE_API = "https://v3.api-free.ir/image/?text={}"

# اتصال به MongoDB
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=30000, ssl_cert_reqs=ssl.CERT_NONE)
    db = client["telegram_bot"]
    users_collection = db["users"]
    spam_collection = db["spam"]
    client.server_info()  # تست اتصال
    logger.info("MongoDB connection successful")
except Exception as e:
    logger.error(f"MongoDB connection error: {e}")

# تنظیم ربات و Flask
bot = telebot.TeleBot(TOKEN)
application = Flask(__name__)

# تابع بررسی عضویت در کانال
def check_channel_membership(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

# تابع ایجاد کیبورد جوین
def join_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📢 کانال", url=f"https://t.me/{CHANNEL_ID[1:]}"))
    keyboard.add(InlineKeyboardButton("✅ تأیید", callback_data="check_join"))
    return keyboard

# تابع ایجاد کیبورد اصلی
def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📖 راهنما", "📞 پشتیبانی")
    return keyboard

# تابع ایجاد کیبورد ادمین
def admin_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("👥 تعداد کاربران", callback_data="user_count"))
    keyboard.add(InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="broadcast"))
    return keyboard

# تابع بررسی اسپم
def check_spam(user_id):
    now = datetime.now()
    user_spam = spam_collection.find_one({"user_id": user_id})
    if user_spam:
        messages = user_spam.get("messages", [])
        messages = [msg for msg in messages if now - msg["time"] < timedelta(minutes=2)]
        if len(messages) >= 4:
            return False, now - messages[-1]["time"]
        messages.append({"time": now})
        spam_collection.update_one({"user_id": user_id}, {"$set": {"messages": messages}}, upsert=True)
    else:
        spam_collection.insert_one({"user_id": user_id, "messages": [{"time": now}]})
    return True, None

# تابع دریافت پاسخ از وب‌سرویس چت
def get_chat_response(text):
    for api in CHAT_APIS:
        try:
            response = requests.get(api.format(text), timeout=5)
            if response.status_code == 200:
                return response.text.strip()
        except Exception as e:
            logger.error(f"Chat API error: {e}")
            continue
    return "❌ خطا در اتصال به سرور چت"

# تابع دانلود فایل
def download_file(url, service):
    try:
        if service == "instagram":
            response = requests.get(INSTAGRAM_API.format(url), timeout=10)
            data = response.json()
            if "links" in data:
                return data["links"][0], None
            return None, "❌ خطا: لینک اینستاگرام معتبر نیست"
        elif service == "spotify":
            response = requests.get(SPOTIFY_API.format(url), timeout=10)
            data = response.json()
            if data.get("ok") and "download_url" in data["data"]["track"]:
                return data["data"]["track"]["download_url"], None
            return None, "❌ خطا: لینک اسپاتیفای معتبر نیست"
        elif service == "pinterest":
            response = requests.get(PINTEREST_API.format(url), timeout=10)
            data = response.json()
            if data.get("status"):
                return data["download_url"], None
            return None, "❌ خطا: لینک پینترست معتبر نیست"
        elif service == "image":
            response = requests.get(IMAGE_API.format(url), timeout=10)
            data = response.json()
            if data.get("ok"):
                return data["result"], None
            return None, "❌ خطا: متن برای تولید تصویر معتبر نیست"
    except Exception as e:
        return None, f"❌ خطا در اتصال به سرور: {str(e)}"

# هندلر استارت
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    try:
        if not users_collection.find_one({"user_id": user_id}):
            users_collection.insert_one({"user_id": user_id, "first_start": datetime.now()})
            bot.send_message(ADMIN_ID, f"کاربر جدید: {message.from_user.username or message.from_user.first_name} ({user_id})")
        
        if not check_channel_membership(user_id):
            bot.send_message(message.chat.id, "لطفاً ابتدا در کانال ما عضو شوید:", reply_markup=join_keyboard())
        else:
            welcome_msg = (
                "🎉 خوش آمدید!\n"
                "تبریک! شما با موفقیت به ربات ما پیوستید. از امکانات هوش مصنوعی و دانلودرهای ما لذت ببرید! 😊\n"
                "برای اطلاعات بیشتر، دکمه راهنما را بزنید."
            )
            bot.send_message(message.chat.id, welcome_msg, reply_markup=main_keyboard())
    except Exception as e:
        logger.error(f"Start handler error: {e}")
        bot.send_message(message.chat.id, "❌ خطا در پردازش درخواست. لطفاً دوباره امتحان کنید.")

# هندلر بررسی جوین
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    user_id = call.from_user.id
    try:
        if check_channel_membership(user_id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            welcome_msg = (
                "🎉 خوش آمدید!\n"
                "تبریک! شما با موفقیت به ربات ما پیوستید. از امکانات هوش مصنوعی و دانلودرهای ما لذت ببرید! 😊\n"
                "برای اطلاعات بیشتر، دکمه راهنما را بزنید."
            )
            bot.send_message(call.message.chat.id, welcome_msg, reply_markup=main_keyboard())
        else:
            bot.answer_callback_query(call.id, "❌ لطفاً ابتدا در کانال عضو شوید!")
    except Exception as e:
        logger.error(f"Check join error: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در پردازش درخواست.")

# هندلر راهنما
@bot.message_handler(func=lambda message: message.text == "📖 راهنما")
def guide(message):
    guide_text = (
        "📚 **راهنمای استفاده از ربات**\n\n"
        "این ربات امکانات زیر را ارائه می‌دهد:\n"
        "🤖 **چت هوش مصنوعی**: هر متنی بنویسید، پاسخ هوشمند دریافت کنید.\n"
        "📥 **دانلودرها**:\n"
        "- اینستاگرام: لینک پست/استوری/ریلز (عکس یا ویدیو)\n"
        "- اسپاتیفای: لینک آهنگ (فایل MP3)\n"
        "- پینترست: لینک پین (عکس)\n"
        "- تولید تصویر: متن وارد کنید، تصویر دریافت کنید.\n\n"
        "⚠️ **قوانین و اخطارها**:\n"
        "1. از ارسال لینک‌های غیرمجاز (به جز اینستاگرام، اسپاتیفای، پینترست) خودداری کنید.\n"
        "2. ارسال بیش از ۴ پیام در ۲ دقیقه باعث مسدود شدن موقت می‌شود.\n"
        "3. از ارسال محتوای غیرقانونی یا توهین‌آمیز پرهیز کنید.\n\n Ascending: [object Object]
