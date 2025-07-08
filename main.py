import telebot
from telebot import types
from pymongo import MongoClient
from datetime import datetime, timedelta
import re
import threading
import logging
import http.server
import socketserver
import os

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# تنظیمات ربات
TOKEN = "7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE"
ADMIN_ID = 5637609683
MONGO_URI = "mongodb+srv://mohsenfeizi1386:p%40ssw0rd%279%27%21@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"
PORT = 1000

# تنظیمات دیتابیس
client = MongoClient(MONGO_URI)
db = client["chatroom_db"]
users_collection = db["users"]
messages_collection = db["messages"]

# لیست کلمات ممنوعه برای نام کاربری
FORBIDDEN_NAMES = {"admin", "administrator", "mod", "moderator", "support"}

# متغیر برای وضعیت ربات
bot_active = True

# متن قوانین
RULES_TEXT = """
سلام کاربر @{}  
به ربات Chat Room خوش آمدید!  

اینجا می‌توانید به‌صورت ناشناس با دیگر اعضای گروه چت کنید، با هم آشنا شوید و لذت ببرید.  

اما قوانینی وجود دارد که باید رعایت کنید تا از ربات مسدود نشوید:  

1. این ربات صرفاً برای سرگرمی، چت و دوست‌یابی است. از ربات برای تبلیغات، درخواست پول یا موارد مشابه استفاده نکنید.  
2. ارسال گیف به‌دلیل شلوغ نشدن ربات ممنوع است. اما ارسال عکس، موسیقی و موارد مشابه آزاد است، به‌شرطی که محتوای غیراخلاقی نباشد.  
3. ربات دارای سیستم ضداسپم است. در صورت اسپم کردن، به‌مدت ۲ دقیقه محدود خواهید شد.  
4. به یکدیگر احترام بگذارید. اگر فحاشی یا محتوای غیراخلاقی دیدید، با ریپلای روی پیام و ارسال دستور /report به ادمین اطلاع دهید.  

ربات در نسخه اولیه است و آپدیت‌های جدید در راه است.  
دوستان خود را به ربات دعوت کنید تا تجربه بهتری از چت داشته باشید.  
موفق باشید!
"""

# ایجاد ربات
bot = telebot.TeleBot(TOKEN)

# هندلر برای دستور /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user = users_collection.find_one({"user_id": user_id})

    if user and user.get("registered", False):
        bot.reply_to(message, f"قبلاً ثبت‌نام کردی، خوش اومدی @{user['username']}!")
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("تأیید", callback_data="confirm_start"))
    bot.reply_to(
        message,
        "لطفاً برای ادامه، یک پیام به @netgoris ارسال کنید و سپس روی دکمه تأیید کلیک کنید.",
        reply_markup=keyboard
    )

# هندلر برای دکمه‌های شیشه‌ای
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    user = users_collection.find_one({"user_id": user_id})

    if call.data == "confirm_start":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("قوانین", callback_data="show_rules"))
        bot.send_message(
            call.message.chat.id,
            "آیا قوانین و مقررات را تأیید می‌کنید؟",
            reply_markup=keyboard
        )

    elif call.data == "show_rules":
        username = user.get("username", "کاربر") if user else "کاربر"
        bot.edit_message_text(
            RULES_TEXT.format(username),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("تأیید قوانین", callback_data="confirm_rules"))
        bot.send_message(
            call.message.chat.id,
            "لطفاً قوانین را تأیید کنید.",
            reply_markup=keyboard
        )

    elif call.data == "confirm_rules":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"state": "awaiting_username"}},
            upsert=True
        )
        bot.send_message(
            call.message.chat.id,
            "لطفاً نام کاریری خود را (به انگلیسی) ارسال کنید. از اسامی مانند admin خودداری کنید."
        )

# هندلر برای پیام‌های متنی
@bot.message_handler(content_types=['text'])
def handle_message(message):
    global bot_active
    if not bot_active and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "ربات در حال حاضر غیرفعال است.")
        return

    user_id = message.from_user.id
    user = users_collection.find_one({"user_id": user_id})

    # بررسی بن بودن کاربر
    if user and user.get("banned", False):
        bot.reply_to(message, "شما از ربات مسدود شده‌اید.")
        return

    # ثبت نام کاربر
    if not user or not user.get("registered", False):
        if user and user.get("state") == "awaiting_username":
            username = message.text.strip()
            if not re.match("^[a-zA-Z0-9_]+$", username):
                bot.reply_to(message, "نام کاربری باید به انگلیسی و بدون کاراکترهای خاص باشد.")
                return
            if username.lower() in FORBIDDEN_NAMES:
                bot.reply_to(message, "این نام کاربری مجاز نیست. نام دیگری انتخاب کنید.")
                return
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"username": username, "registered": True, "state": "active"}}
            )
            bot.reply_to(message, f"نام کاربری @{username} ثبت شد. حالا می‌توانید چت کنید!")
            return
        return

    # ضد اسپم
    now = datetime.utcnow()
    messages_collection.insert_one({
        "user_id": user_id,
        "timestamp": now,
        "message_id": message.message_id,
        "chat_id": message.chat.id
    })
    recent_messages = messages_collection.count_documents({
        "user_id": user_id,
        "timestamp": {"$gte": now - timedelta(seconds=10)}
    })
    if recent_messages > 5:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"muted_until": now + timedelta(minutes=2)}}
        )
        bot.reply_to(message, "شما به دلیل اسپم به مدت ۲ دقیقه محدود شدید.")
        return

    if user.get("muted_until") and user["muted_until"] > now:
        bot.reply_to(message, "شما موقتاً محدود شده‌اید. لطفاً کمی صبر کنید.")
        return

    # ارسال پیام به همه کاربران فعال
    username = user["username"] if user.get("registered") else "ادمین" if user_id == ADMIN_ID else "ناشناس"
    message_text = f"@{username}: {message.text}"
    if message.reply_to_message:
        reply_user = users_collection.find_one({"user_id": message.reply_to_message.from_user.id})
        reply_username = reply_user["username"] if reply_user and reply_user.get("registered") else "ناشناس"
        message_text = f"@{username} در پاسخ به @{reply_username}: {message.text}"

    active_users = users_collection.find({"registered": True})
    for active_user in active_users:
        if active_user["user_id"] != user_id:
            try:
                bot.send_message(
                    chat_id=active_user["user_id"],
                    text=message_text,
                    reply_to_message_id=message.reply_to_message.message_id if message.reply_to_message else None
                )
            except Exception as e:
                logger.error(f"Error sending message to {active_user['user_id']}: {e}")

# هندلر برای گیف
@bot.message_handler(content_types=['animation'])
def handle_gif(message):
    bot.reply_to(message, "ارسال گیف ممنوع است!")

# هندلر برای دستورات مدیریت
@bot.message_handler(commands=['ban'])
def ban(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "فقط ادمین می‌تواند از این دستور استفاده کند.")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "لطفاً روی پیام کاربر ریپلای کنید.")
        return
    target_user_id = message.reply_to_message.from_user.id
    users_collection.update_one(
        {"user_id": target_user_id},
        {"$set": {"banned": True}}
    )
    target_user = users_collection.find_one({"user_id": target_user_id})
    bot.reply_to(message, f"کاربر @{target_user['username']} بن شد.")

@bot.message_handler(commands=['unban'])
def unban(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "فقط ادمین می‌تواند از این دستور استفاده کند.")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "لطفاً روی پیام کاربر ریپلای کنید.")
        return
    target_user_id = message.reply_to_message.from_user.id
    users_collection.update_one(
        {"user_id": target_user_id},
        {"$set": {"banned": False}}
    )
    target_user = users_collection.find_one({"user_id": target_user_id})
    bot.reply_to(message, f"کاربر @{target_user['username']} آن‌بان شد.")

@bot.message_handler(commands=['report'])
def report(message):
    if not message.reply_to_message:
        bot.reply_to(message, "لطفاً روی پیام موردنظر ریپلای کنید.")
        return
    target_user_id = message.reply_to_message.from_user.id
    target_user = users_collection.find_one({"user_id": target_user_id})
    bot.send_message(
        chat_id=ADMIN_ID,
        text=f"گزارش از @{message.from_user.username}: پیام از @{target_user['username']}\nمتن: {message.reply_to_message.text}"
    )
    bot.reply_to(message, "گزارش شما به ادمین ارسال شد.")

@bot.message_handler(commands=['toggle'])
def toggle_bot(message):
    global bot_active
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "فقط ادمین می‌تواند ربات را روشن یا خاموش کند.")
        return
    bot_active = not bot_active
    status = "روشن" if bot_active else "خاموش"
    bot.reply_to(message, f"ربات {status} شد.")

# تابع برای پاک کردن پیام‌های قدیمی
def clean_old_messages():
    while True:
        messages_collection.delete_many({"timestamp": {"$lte": datetime.utcnow() - timedelta(hours=24)}})
        threading.Event().wait(3600)  # هر ساعت بررسی کن

# تنظیم وب‌هوک و سرور
def start_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    logger.info(f"Webhook set to {WEBHOOK_URL}/{TOKEN}")

    class WebhookHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path == f"/{TOKEN}":
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                update = telebot.types.Update.de_json(post_data.decode('utf-8'))
                bot.process_new_updates([update])
                self.send_response(200)
                self.end_headers()
            else:
                self.send_response(403)
                self.end_headers()

    server = socketserver.TCPServer(("0.0.0.0", PORT), WebhookHandler)
    server.serve_forever()

if __name__ == "__main__":
    # شروع تابع پاک‌سازی پیام‌ها در نخ جداگانه
    threading.Thread(target=clean_old_messages, daemon=True).start()
    # شروع وب‌هوک
    start_webhook()
