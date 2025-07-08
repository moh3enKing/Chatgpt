import os
import re
import time
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
import telebot
from telebot import types
from pymongo import MongoClient

# ====== تنظیمات =======
TOKEN = "7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE"
CHANNEL_ID = "@netgoris"
ADMIN_ID = 5637609683
DB_PASSWORD = "p%40ssw0rd%279%27%21"

WEBHOOK_URL_BASE = "https://chatgpt-qg71.onrender.com"
WEBHOOK_URL_PATH = f"/{TOKEN}/"

# ====== راه‌اندازی ربات =======
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ====== اتصال به MongoDB =======
client = MongoClient(f"mongodb+srv://mohsenfeizi1386:{DB_PASSWORD}@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["chat_room"]
users = db["users"]

# ====== متغیرها =======
bot_status = {"enabled": True}
user_messages = {}
SPAM_LIMIT = 4
SPAM_TIME = 120
BANNED_NAMES = ["admin", "mod", "owner", "support", "ادمین", "مدیر", "پشتیبان"]

app = FastAPI()

# ==== توابع کمکی ====

def is_user_in_channel(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'creator', 'administrator']
    except Exception:
        return False

def is_english(text):
    return bool(re.match(r'^[A-Za-z0-9_\-\s]+$', text))

def contains_graphic_characters(text):
    for c in text:
        if ord(c) > 127:
            return True
    return False

def extract_sender_name_from_text(text):
    match = re.search(r"<b>(.*?)</b>", text)
    return match.group(1).strip() if match else None

# ======= هندل /start =======
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    user = users.find_one({"user_id": user_id})

    if user and user.get("name"):
        bot.send_message(user_id, f"🌟 خوش آمدید مجدد {user['name']}!\nمیتوانید چت را شروع کنید.")
        return

    if not is_user_in_channel(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"))
        markup.add(types.InlineKeyboardButton("✅ تایید عضویت", callback_data="confirm_join"))
        bot.send_message(user_id, "🔐 لطفاً ابتدا در کانال زیر عضو شوید:", reply_markup=markup)
        return

    send_rules_confirm(message)

@bot.callback_query_handler(func=lambda call: call.data == "confirm_join")
def confirm_join(call):
    user_id = call.from_user.id
    if not is_user_in_channel(user_id):
        bot.answer_callback_query(call.id, "⛔️ هنوز عضو کانال نیستید!")
        return
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📜 قوانین", callback_data="show_rules"))
    bot.send_message(user_id, "📘 آیا قوانین ربات را تایید می‌کنید؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_rules")
def show_rules(call):
    user_id = call.from_user.id
    rules = f"""سلام کاربر @{call.from_user.username or 'user'}
به ربات Chat Room خوش آمدید.

اینجا شما آزاد هستید که به صورت ناشناس با دیگر اعضای گروه در ارتباط باشید، چت کنید و با هم آشنا شوید.

اما قوانینی وجود دارد که باید رعایت شوند تا از ربات مسدود نشوید:

1️⃣ این ربات صرفاً برای سرگرمی و چت کردن است؛ از آن برای تبلیغات یا درخواست پول استفاده نکنید.
2️⃣ ارسال گیف در ربات ممنوع است. ارسال عکس و موسیقی آزاد است اما محتوای غیراخلاقی ممنوع.
3️⃣ ربات دارای ضد اسپم است؛ ارسال زیاد باعث سکوت ۲ دقیقه‌ای می‌شود.
4️⃣ به یکدیگر احترام بگذارید؛ تخلف را با ریپلای و دستور (گزارش) اطلاع دهید.

📢 دوستان‌تان را به ربات دعوت کنید و لذت ببرید.
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✅ تایید قوانین")
    bot.edit_message_text(rules, user_id, call.message.message_id)
    bot.send_message(user_id, "📌 لطفاً قوانین را با دکمه زیر تایید کنید:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "✅ تایید قوانین")
def ask_name(m):
    markup = types.ForceReply(selective=False)
    bot.send_message(m.chat.id, "📝 لطفاً یک نام انگلیسی برای خودتان انتخاب کنید:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.reply_to_message and "نام انگلیسی" in m.reply_to_message.text)
def handle_name(m):
    name = m.text.strip()
    if not is_english(name):
        return bot.send_message(m.chat.id, "❌ فقط حروف انگلیسی ساده مجاز است.")
    if contains_graphic_characters(name):
        return bot.send_message(m.chat.id, "⚠️ لطفاً از فونت ساده استفاده کنید.")
    if any(b in name.lower() for b in BANNED_NAMES):
        return bot.send_message(m.chat.id, "⛔️ این نام مجاز نیست.")

    users.update_one({"user_id": m.from_user.id}, {"$set": {"user_id": m.from_user.id, "name": name, "banned": False, "muted": False}}, upsert=True)
    bot.send_message(m.chat.id, f"✅ ثبت‌نام با نام {name} کامل شد. حالا می‌توانید پیام ارسال کنید!")

import threading

@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'voice', 'audio', 'video', 'document', 'animation', 'sticker'])
def handle_all_messages(message):
    user_id = message.from_user.id

    if not bot_status["enabled"] and user_id != ADMIN_ID:
        return

    user = users.find_one({"user_id": user_id})
    if not user or not user.get("name"):
        return bot.send_message(user_id, "⛔️ لطفاً ابتدا با /start ثبت‌نام کنید.")

    if user.get("banned"):
        return bot.send_message(user_id, "🚫 شما بن شده‌اید.")

    # ممنوعیت گیف
    if message.content_type == "animation" or (message.document and message.document.mime_type == "image/gif"):
        return bot.send_message(user_id, "❌ ارسال گیف مجاز نیست.")

    # ضد اسپم
    now = time.time()
    timestamps = user_messages.get(user_id, [])
    timestamps = [t for t in timestamps if now - t < SPAM_TIME]
    if len(timestamps) >= SPAM_LIMIT:
        users.update_one({"user_id": user_id}, {"$set": {"muted": True}})
        return bot.send_message(user_id, "🚷 به دلیل اسپم، ۲ دقیقه سکوت داده شده‌اید.")
    user_messages[user_id] = timestamps + [now]
    if user.get("muted"):
        return

    name = user['name']
    content = f"<b>{name}:</b>"

    if message.reply_to_message:
        content = "💬 پاسخ به پیام بالا\n\n" + content

    # ارسال پیام به همه به صورت ناشناس
    chat_id = message.chat.id

    if message.content_type == "text":
        content += f"\n{message.text}"
        bot.send_message(chat_id, content)
    elif message.content_type == "photo":
        bot.send_photo(chat_id, message.photo[-1].file_id, caption=content)
    elif message.content_type == "voice":
        bot.send_voice(chat_id, message.voice.file_id, caption=content)
    elif message.content_type == "audio":
        bot.send_audio(chat_id, message.audio.file_id, caption=content)
    elif message.content_type == "video":
        bot.send_video(chat_id, message.video.file_id, caption=content)
    elif message.content_type == "document":
        bot.send_document(chat_id, message.document.file_id, caption=content)
    elif message.content_type == "sticker":
        bot.send_sticker(chat_id, message.sticker.file_id)

# بن و آنبن با ریپلای
@bot.message_handler(func=lambda m: m.reply_to_message and m.text.lower() in ["بن", "آنبن"])
def handle_ban_unban(m):
    if m.from_user.id != ADMIN_ID:
        return bot.reply_to(m, "⛔️ فقط ادمین.")

    target_name = extract_sender_name_from_text(m.reply_to_message.text or m.reply_to_message.caption or "")
    if not target_name:
        return bot.reply_to(m, "❌ نام کاربر قابل شناسایی نیست.")

    user = users.find_one({"name": target_name})
    if not user:
        return bot.reply_to(m, "❌ کاربر یافت نشد.")

    if m.text.lower() == "بن":
        users.update_one({"user_id": user["user_id"]}, {"$set": {"banned": True}})
        bot.reply_to(m, f"🚫 کاربر <b>{target_name}</b> بن شد.")
    else:
        users.update_one({"user_id": user["user_id"]}, {"$set": {"banned": False}})
        bot.reply_to(m, f"✅ کاربر <b>{target_name}</b> آزاد شد.")

# روشن / خاموش
@bot.message_handler(commands=["خاموش", "روشن"])
def toggle(m):
    if m.from_user.id != ADMIN_ID:
        return
    if m.text == "/خاموش":
        bot_status["enabled"] = False
        bot.reply_to(m, "🔴 ربات غیرفعال شد.")
    else:
        bot_status["enabled"] = True
        bot.reply_to(m, "🟢 ربات فعال شد.")

# راه‌اندازی webhook و فست‌API

@app.post(WEBHOOK_URL_PATH)
async def webhook(request: Request, background_tasks: BackgroundTasks):
    json_str = await request.body()
    json_dict = json_str.decode("utf-8")
    from telebot import types as tb_types
    update = telebot.types.Update.de_json(json_dict)
    background_tasks.add_task(bot.process_new_updates, [update])
    return JSONResponse(content={"status": "ok"})

def set_webhook():
    webhook_url = WEBHOOK_URL_BASE + WEBHOOK_URL_PATH
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)

if __name__ == "__main__":
    set_webhook()
    uvicorn.run(app, host="0.0.0.0", port=1000)
