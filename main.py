import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from flask import Flask, request
import requests
import certifi
from pymongo import MongoClient
from datetime import datetime, timedelta
import re
import os
import logging

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO, filename='bot.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# تنظیمات ربات
TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
ADMIN_ID = 5637609683
CHANNEL_ID = "@netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=false&tls=true"
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
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=30000,
        ssl=True
    )
    db = client["telegram_bot"]
    users_collection = db["users"]
    spam_collection = db["spam"]
    client.server_info()  # تست اتصال
    logger.info("MongoDB connection successful")
except Exception as e:
    logger.error(f"MongoDB connection error: {str(e)}")
    raise  # برای تست، خطا رو پرت می‌کنه

# تنظیم ربات و Flask
bot = telebot.TeleBot(TOKEN)
application = Flask(__name__)

# تابع بررسی عضویت در کانال
def check_channel_membership(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking membership for user {user_id}: {str(e)}")
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
    try:
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
    except Exception as e:
        logger.error(f"Spam check error for user {user_id}: {str(e)}")
        return False, None

# تابع دریافت پاسخ از وب‌سرویس چت
def get_chat_response(text):
    for api in CHAT_APIS:
        try:
            response = requests.get(api.format(text), timeout=5)
            if response.status_code == 200:
                return response.text.strip()
        except Exception as e:
            logger.error(f"Chat API error for text {text}: {str(e)}")
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
        # بررسی اتصال به MongoDB
        if not client.server_info():
            logger.error("MongoDB not connected during start command")
            bot.send_message(message.chat.id, "❌ خطا در اتصال به دیتابیس. لطفاً بعداً امتحان کنید.")
            return

        # ثبت کاربر جدید
        if not users_collection.find_one({"user_id": user_id}):
            users_collection.insert_one({"user_id": user_id, "first_start": datetime.now()})
            try:
                bot.send_message(ADMIN_ID, f"کاربر جدید: {message.from_user.username or message.from_user.first_name} ({user_id})")
            except Exception as e:
                logger.error(f"Error sending new user notification to admin {ADMIN_ID}: {str(e)}")

        # بررسی عضویت در کانال
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
        logger.error(f"Start handler error for user {user_id}: {str(e)}")
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
        logger.error(f"Check join error for user {user_id}: {str(e)}")
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
        "3. از ارسال محتوای غیرقانونی یا توهین‌آمیز پرهیز کنید.\n\n"
        "📞 برای پشتیبانی، دکمه پشتیبانی را بزنید."
    )
    try:
        bot.edit_message_text(guide_text, message.chat.id, message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🙏 ما همیشه در خدمتیم", callback_data="final_message")))
    except:
        bot.send_message(message.chat.id, guide_text, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🙏 ما همیشه در خدمتیم", callback_data="final_message")))

# هندلر پیام نهایی
@bot.callback_query_handler(func=lambda call: call.data == "final_message")
def final_message(call):
    final_text = (
        "🙏 **ما همیشه در خدمت شما هستیم!**\n"
        "از همراهی شما سپاسگزاریم. هر زمان نیاز به کمک داشتید، با پشتیبانی تماس بگیرید! 😊"
    )
    try:
        bot.edit_message_text(final_text, call.message.chat.id, call.message.message_id, reply_markup=main_keyboard())
    except Exception as e:
        logger.error(f"Final message error for user {call.from_user.id}: {str(e)}")

# هندلر پشتیبانی
@bot.message_handler(func=lambda message: message.text == "📞 پشتیبانی")
def support(message):
    try:
        users_collection.update_one({"user_id": message.from_user.id}, {"$set": {"support_mode": True}}, upsert=True)
        bot.send_message(message.chat.id, "لطفاً پیام خود را برای پشتیبانی ارسال کنید یا برای خروج /cancel را بزنید.", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        logger.error(f"Support handler error for user {message.from_user.id}: {str(e)}")

# هندلر لغو پشتیبانی
@bot.message_handler(commands=["cancel"])
def cancel_support(message):
    try:
        users_collection.update_one({"user_id": message.from_user.id}, {"$set": {"support_mode": False}})
        bot.send_message(message.chat.id, "پشتیبانی لغو شد.", reply_markup=main_keyboard())
    except Exception as e:
        logger.error(f"Cancel support error for user {message.from_user.id}: {str(e)}")

# هندلر پاسخ ادمین
@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID and message.reply_to_message)
def admin_reply(message):
    try:
        user_id = message.reply_to_message.forward_from.id if message.reply_to_message.forward_from else None
        if user_id:
            bot.send_message(user_id, message.text, reply_to_message_id=message.reply_to_message.message_id)
            users_collection.update_one({"user_id": user_id}, {"$set": {"support_mode": False}})
            bot.send_message(user_id, "پشتیبانی به پایان رسید.", reply_markup=main_keyboard())
            bot.send_message(ADMIN_ID, "پاسخ برای کاربر ارسال شد.")
    except Exception as e:
        logger.error(f"Admin reply error for user {user_id}: {str(e)}")

# هندلر پنل ادمین
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    try:
        if message.from_user.id == ADMIN_ID:
            bot.send_message(message.chat.id, "پنل مدیریت:", reply_markup=admin_keyboard())
        else:
            bot.send_message(message.chat.id, "❌ دسترسی غیرمجاز!")
    except Exception as e:
        logger.error(f"Admin panel error for user {message.from_user.id}: {str(e)}")

# هندلر تعداد کاربران
@bot.callback_query_handler(func=lambda call: call.data == "user_count")
def user_count(call):
    try:
        if call.from_user.id == ADMIN_ID:
            count = users_collection.count_documents({})
            bot.send_message(call.message.chat.id, f"تعداد کاربران: {count}")
        else:
            bot.answer_callback_query(call.id, "❌ دسترسی غیرمجاز!")
    except Exception as e:
        logger.error(f"User count error for user {call.from_user.id}: {str(e)}")

# هندلر ارسال پیام همگانی
@bot.callback_query_handler(func=lambda call: call.data == "broadcast")
def broadcast(call):
    try:
        if call.from_user.id == ADMIN_ID:
            bot.send_message(ADMIN_ID, "لطفاً متن پیام همگانی را ارسال کنید:")
            users_collection.update_one({"user_id": ADMIN_ID}, {"$set": {"broadcast_mode": True}}, upsert=True)
        else:
            bot.answer_callback_query(call.id, "❌ دسترسی غیرمجاز!")
    except Exception as e:
        logger.error(f"Broadcast error for user {call.from_user.id}: {str(e)}")

# هندلر دریافت پیام همگانی
@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID and users_collection.find_one({"user_id": ADMIN_ID, "broadcast_mode": True}))
def send_broadcast(message):
    try:
        users = users_collection.find()
        for user in users:
            try:
                bot.send_message(user["user_id"], message.text)
            except:
                continue
        users_collection.update_one({"user_id": ADMIN_ID}, {"$set": {"broadcast_mode": False}})
        bot.send_message(ADMIN_ID, "پیام همگانی ارسال شد.")
    except Exception as e:
        logger.error(f"Send broadcast error for admin {ADMIN_ID}: {str(e)}")

# هندلر پیام‌های متنی
@bot.message_handler(content_types=["text"])
def handle_text(message):
    user_id = message.from_user.id
    try:
        if not check_channel_membership(user_id):
            bot.send_message(message.chat.id, "لطفاً ابتدا در کانال ما عضو شوید:", reply_markup=join_keyboard())
            return

        # بررسی پشتیبانی
        if users_collection.find_one({"user_id": user_id, "support_mode": True}):
            bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
            return

        # بررسی اسپم
        can_send, time_left = check_spam(user_id)
        if not can_send:
            seconds = int(time_left.total_seconds())
            bot.send_message(message.chat.id, f"⛔ لطفاً {seconds} ثانیه صبر کنید (حداکثر ۴ پیام در ۲ دقیقه).")
            return

        # تشخیص لینک
        text = message.text
        instagram_pattern = r"(https?://(www\.)?instagram\.com/(p|reel|stories)/.+)"
        spotify_pattern = r"(https?://open\.spotify\.com/track/.+)"
        pinterest_pattern = r"(https?://(www\.)?pinterest\.com/pin/.+)"

        if re.match(instagram_pattern, text):
            msg = bot.send_message(message.chat.id, "⏳ در حال پردازش...")
            file_url, error = download_file(text, "instagram")
            bot.delete_message(message.chat.id, msg.message_id)
            if error:
                bot.send_message(message.chat.id, error)
            else:
                bot.send_document(message.chat.id, file_url)
        elif re.match(spotify_pattern, text):
            msg = bot.send_message(message.chat.id, "⏳ در حال پردازش...")
            file_url, error = download_file(text, "spotify")
            bot.delete_message(message.chat.id, msg.message_id)
            if error:
                bot.send_message(message.chat.id, error)
            else:
                bot.send_audio(message.chat.id, file_url)
        elif re.match(pinterest_pattern, text):
            msg = bot.send_message(message.chat.id, "⏳ در حال پردازش...")
            file_url, error = download_file(text, "pinterest")
            bot.delete_message(message.chat.id, msg.message_id)
            if error:
                bot.send_message(message.chat.id, error)
            else:
                bot.send_photo(message.chat.id, file_url)
        else:
            msg = bot.send_message(message.chat.id, "…")
            response = get_chat_response(text)
            bot.edit_message_text(response, message.chat.id, msg.message_id)
    except Exception as e:
        logger.error(f"Text handler error for user {user_id}: {str(e)}")
        bot.send_message(message.chat.id, "❌ خطا در پردازش درخواست. لطفاً دوباره امتحان کنید.")

# روت اصلی برای تست
@application.route("/", methods=["GET"])
def index():
    return "Webhook is running!", 200

# روت Flask برای وب‌هوک
@application.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_json())
        bot.process_new_updates([update])
        return "", 200
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return "", 500

# تنظیم وب‌هوک
def set_webhook():
    try:
        bot.remove_webhook()
        if bot.set_webhook(url=WEBHOOK_URL):
            logger.info("Webhook set successfully")
        else:
            logger.error("Failed to set webhook")
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")

# اجرای وب‌هوک
if __name__ == "__main__":
    set_webhook()
    application.run(host="0.0.0.0", port=1000)
