import telebot
from telebot import types
from flask import Flask, request
import requests
import time
from pymongo import MongoClient
import threading

# ----------- تنظیمات -----------
TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
CHANNEL = "@netgoris"
ADMIN_ID = 5637609683
MONGO_URL = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com/"  # دامنه هاست

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
db = MongoClient(MONGO_URL).bot_db
users = db.users
support_sessions = {}
spam_tracker = {}

# ----------- ضداسپم -----------
def is_spamming(user_id):
    now = time.time()
    if user_id not in spam_tracker:
        spam_tracker[user_id] = []
    spam_tracker[user_id] = [t for t in spam_tracker[user_id] if now - t < 120]
    spam_tracker[user_id].append(now)
    return len(spam_tracker[user_id]) > 4

# ----------- چک عضویت -----------
def is_joined(user_id):
    try:
        status = bot.get_chat_member(CHANNEL, user_id).status
        return status in ["member", "administrator", "creator"]
    except:
        return False

# ----------- استارت -----------
@bot.message_handler(commands=["start"])
def start(message):
    user = users.find_one({"_id": message.chat.id})
    if not user:
        users.insert_one({"_id": message.chat.id, "banned": False})
        bot.send_message(ADMIN_ID, f"کاربر جدید استارت زد:\n{message.from_user.first_name}\nID: {message.chat.id}")

    if is_joined(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📋 راهنما", callback_data="help"))
        bot.send_message(message.chat.id, "🎉 خوش آمدید به ربات ما!\nاز دکمه‌های زیر استفاده کنید:", reply_markup=markup)
    else:
        join_markup = types.InlineKeyboardMarkup()
        join_markup.add(types.InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL.replace('@','')}"))
        join_markup.add(types.InlineKeyboardButton("✅ تایید عضویت", callback_data="check_join"))
        bot.send_message(message.chat.id, "🔒 برای استفاده از ربات لطفا عضو کانال شوید:", reply_markup=join_markup)

# ----------- دکمه‌ها -----------
@bot.callback_query_handler(func=lambda c: True)
def callback(c):
    if c.data == "check_join":
        if is_joined(c.from_user.id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📋 راهنما", callback_data="help"))
            bot.edit_message_text("✅ عضویت تایید شد!\n🎉 خوش آمدید.", c.message.chat.id, c.message.message_id, reply_markup=markup)
        else:
            bot.answer_callback_query(c.id, "⚠️ ابتدا عضو کانال شوید.")

    if c.data == "help":
        help_text = (
            "📚 راهنمای ربات:\n\n"
            "✔️ ارسال متن = دریافت پاسخ هوش مصنوعی\n"
            "✔️ ارسال لینک اینستاگرام، اسپاتیفای، پینترست = دانلود مستقیم\n"
            "✔️ ارسال متن تصویر = ساخت عکس با متن\n"
            "\n📌 قوانین:\n"
            "❗ ارسال بیش از ۴ پیام در ۲ دقیقه = سکوت موقت\n"
            "❗ استفاده غیرمجاز ممنوع!\n"
            "\n🤖 ربات همیشه در خدمت شماست ✨"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back"))
        bot.edit_message_text(help_text, c.message.chat.id, c.message.message_id, reply_markup=markup)

    if c.data == "back":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📋 راهنما", callback_data="help"))
        bot.edit_message_text("🎉 مجدداً خوش آمدید!\nاز دکمه‌ها استفاده کنید:", c.message.chat.id, c.message.message_id, reply_markup=markup)

# ----------- پشتیبانی خصوصی -----------
@bot.message_handler(func=lambda m: m.text == "💬 پشتیبانی")
def support(message):
    support_sessions[message.chat.id] = True
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "✍️ پیام خود را بنویسید:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.chat.id in support_sessions)
def handle_support(message):
    if message.text == "/cancel":
        del support_sessions[message.chat.id]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💬 پشتیبانی")
        bot.send_message(message.chat.id, "❌ پشتیبانی لغو شد.", reply_markup=markup)
    else:
        bot.send_message(ADMIN_ID, f"📩 پیام جدید:\n{message.text}\n👤 از: {message.chat.id}", reply_markup=types.ForceReply(selective=True))
        del support_sessions[message.chat.id]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💬 پشتیبانی")
        bot.send_message(message.chat.id, "✅ پیام ارسال شد، منتظر پاسخ باشید.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.reply_to_message and str(m.reply_to_message.text).startswith("📩 پیام جدید"))
def admin_reply(message):
    target_id = int(message.reply_to_message.text.split("👤 از: ")[1])
    bot.send_message(target_id, f"🛠️ پاسخ مدیر:\n{message.text}")

# ----------- پردازش پیام‌ها -----------
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    if is_spamming(message.chat.id):
        return

    user = users.find_one({"_id": message.chat.id})
    if user and user.get("banned"):
        return

    if "instagram.com" in message.text:
        url = f"https://pouriam.top/eyephp/instagram?url={message.text}"
        r = requests.get(url).json()
        links = r.get("links", [])
        for link in links:
            bot.send_message(message.chat.id, link)

    elif "spotify.com" in message.text:
        url = f"http://api.cactus-dev.ir/spotify.php?url={message.text}"
        r = requests.get(url).json()
        if r["ok"]:
            bot.send_message(message.chat.id, r["data"]["download_url"])

    elif "pin.it" in message.text or "pinterest.com" in message.text:
        url = f"https://haji.s2025h.space/pin/?url={message.text}&client_key=keyvip"
        r = requests.get(url).json()
        if r["status"]:
            bot.send_message(message.chat.id, r["download_url"])

    elif message.text.startswith("عکس "):
        text = message.text.replace("عکس ", "")
        r = requests.get(f"https://v3.api-free.ir/image/?text={text}").json()
        bot.send_photo(message.chat.id, r["result"])

    else:
        ai_urls = [
            f"https://starsshoptl.ir/Ai/index.php?text={message.text}",
            f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={message.text}",
            f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={message.text}"
        ]
        for url in ai_urls:
            try:
                r = requests.get(url, timeout=10).text
                if r.strip():
                    bot.send_message(message.chat.id, r)
                    break
            except:
                continue

# ----------- پنل مدیریت -----------
@bot.message_handler(commands=["ban"])
def ban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.reply_to(message, "🎯 آیدی عددی کاربر را بفرستید:")
    bot.register_next_step_handler(msg, process_ban)

def process_ban(message):
    users.update_one({"_id": int(message.text)}, {"$set": {"banned": True}})
    bot.send_message(int(message.text), "🚫 شما توسط مدیریت مسدود شدید.")

@bot.message_handler(commands=["unban"])
def unban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.reply_to(message, "🎯 آیدی عددی کاربر را بفرستید:")
    bot.register_next_step_handler(msg, process_unban)

def process_unban(message):
    users.update_one({"_id": int(message.text)}, {"$set": {"banned": False}})
    bot.send_message(int(message.text), "✅ محدودیت شما برداشته شد.")

# ----------- وب‌هوک ----------
@app.route('/', methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "OK"

# ----------- ران برنامه ----------
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 5000}).start()
