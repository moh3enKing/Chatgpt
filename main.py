import os
from flask import Flask, request
import telebot
from telebot import types
from pymongo import MongoClient
import re
import time

# ===== تنظیمات =====
TOKEN = "7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE"
WEBHOOK_URL = f"https://chatgpt-qg71.onrender.com/{TOKEN}"
PORT = int(os.environ.get("PORT", 1000))
CHANNEL_ID = "@netgoris"
ADMIN_ID = 5637609683
DB_PASSWORD = "p%40ssw0rd%279%27%21"

# ===== اتصال به MongoDB =====
client = MongoClient(
    f"mongodb+srv://mohsenfeizi1386:{DB_PASSWORD}@cluster0.ounkvru.mongodb.net/"
    "?retryWrites=true&w=majority&appName=Cluster0"
)
db = client["chat_room"]
users = db["users"]

# ===== راه‌اندازی ربات و Flask =====
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

bot_status = {"enabled": True}
user_messages = {}
SPAM_LIMIT = 4
SPAM_TIME = 120
BANNED_NAMES = ["admin", "mod", "owner", "support", "ادمین", "مدیر", "پشتیبان"]

def is_user_in_channel(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ["member", "administrator", "creator"]
    except:
        return False

def is_english(text):
    return bool(re.match(r'^[A-Za-z0-9 _-]+$', text))

def contains_graphic_characters(text):
    return any(ord(c) > 127 for c in text)

def extract_sender_name(text):
    match = re.search(r"<b>(.*?)</b>", text)
    return match.group(1).strip() if match else None

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "🤖 Bot is running!"

@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    user = users.find_one({"user_id": uid})
    if user and user.get("name"):
        bot.send_message(uid, f"🌟 خوش آمدی {user['name']}! می‌تونی چت شروع کنی.")
        return

    if not is_user_in_channel(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"))
        markup.add(types.InlineKeyboardButton("✅ تایید عضویت", callback_data="confirm_join"))
        bot.send_message(uid, "🔐 لطفاً ابتدا در کانال عضو شو:", reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📜 قوانین", callback_data="show_rules"))
        bot.send_message(uid, "📘 قوانین را تایید می‌کنی؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "confirm_join")
def confirm_join(c):
    uid = c.from_user.id
    if not is_user_in_channel(uid):
        bot.answer_callback_query(c.id, "⛔️ هنوز عضو نیستی.")
        return
    try: bot.delete_message(c.message.chat.id, c.message.message_id)
    except: pass
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📜 قوانین", callback_data="show_rules"))
    bot.send_message(uid, "📘 قوانین را تایید می‌کنی؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "show_rules")
def show_rules(c):
    uid = c.from_user.id
    rules = (
        f"سلام کاربر @{c.from_user.username or 'user'}\n\n"
        "به ربات Chat Room خوش آمدید!\n\n"
        "📌 قوانین:\n"
        "1️⃣ تبلیغات یا درخواست پول ممنوع است\n"
        "2️⃣ ارسال گیف ممنوع؛ عکس و موسیقی آزاد است\n"
        "3️⃣ ضد اسپم فعال است؛ اسپم = سکوت ۲ دقیقه\n"
        "4️⃣ احترام بگذارید؛ تخلف را با ریپلای و گزارش اطلاع دهید\n\n"
        "دوستانت رو دعوت کن. نسخه اولیه است و آپدیت خواهد شد."
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✅ تایید قوانین")
    bot.edit_message_text(rules, uid, c.message.message_id)
    bot.send_message(uid, "📌 قوانین را با دکمه زیر تایید کنید:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "✅ تایید قوانین")
def ask_name(m):
    bot.send_message(m.chat.id, "📝 لطفاً یک نام انگلیسی برای خودت وارد کن:", reply_markup=types.ForceReply())

@bot.message_handler(func=lambda m: m.reply_to_message and "نام انگلیسی" in m.reply_to_message.text)
def handle_name(m):
    name = m.text.strip()
    if not is_english(name):
        return bot.send_message(m.chat.id, "❌ فقط حروف و اعداد انگلیسی مجازند.")
    if contains_graphic_characters(name):
        return bot.send_message(m.chat.id, "⚠️ لطفاً فونت ساده استفاده کن.")
    if any(b in name.lower() for b in BANNED_NAMES):
        return bot.send_message(m.chat.id, "⛔️ این اسم مجاز نیست، نام دیگری انتخاب کن.")

    users.update_one(
        {"user_id": m.from_user.id},
        {"$set": {"user_id": m.from_user.id, "name": name, "banned": False, "muted": False}},
        upsert=True
    )
    bot.send_message(m.chat.id, f"✅ نام {name} ثبت شد! حالا می‌تونی چت شروع کنی.")

@bot.message_handler(func=lambda m: True, content_types=["text","photo","voice","audio","video","document","animation","sticker"])
def chat(m):
    uid = m.from_user.id
    user = users.find_one({"user_id": uid})
    if not user or not user.get("name"):
        return bot.send_message(uid, "⛔️ ابتدا ثبت‌نام کن (/start)")

    if not bot_status["enabled"] and uid != ADMIN_ID:
        return

    if user.get("banned"):
        return bot.send_message(uid, "🚫 شما بن شده‌اید.")

    if m.content_type == "animation" or (m.document and m.document.mime_type == "image/gif"):
        return bot.send_message(uid, "❌ ارسال گیف ممنوع است.")

    now = time.time()
    timestamps = user_messages.get(uid, [])
    timestamps = [t for t in timestamps if now - t < SPAM_TIME]
    if len(timestamps) >= SPAM_LIMIT:
        users.update_one({"user_id": uid}, {"$set": {"muted": True}})
        return bot.send_message(uid, "🚷 اسپم نکن! ۲ دقیقه سکوت گرفتی.")
    user_messages[uid] = timestamps + [now]
    if user.get("muted"):
        return

    name = user["name"]
    content = f"<b>{name}:</b>"

    if m.reply_to_message:
        content = "💬 پاسخ به پیام بالا\n\n" + content

    if m.content_type == "text":
        content += f"\n{m.text}"
        bot.send_message(m.chat.id, content)
    elif m.content_type == "photo":
        bot.send_photo(m.chat.id, m.photo[-1].file_id, caption=content)
    elif m.content_type == "voice":
        bot.send_voice(m.chat.id, m.voice.file_id, caption=content)
    elif m.content_type == "audio":
        bot.send_audio(m.chat.id, m.audio.file_id, caption=content)
    elif m.content_type == "video":
        bot.send_video(m.chat.id, m.video.file_id, caption=content)
    elif m.content_type == "document":
        bot.send_document(m.chat.id, m.document.file_id, caption=content)
    elif m.content_type == "sticker":
        bot.send_sticker(m.chat.id, m.sticker.file_id)

@bot.message_handler(func=lambda m: m.reply_to_message and m.text.lower() in ["بن","آنبن"])
def admin_ban(m):
    if m.from_user.id != ADMIN_ID:
        return
    target = extract_sender_name(m.reply_to_message.text or m.reply_to_message.caption or "")
    if not target:
        return bot.reply_to(m, "❌ نام کاربر قابل شناسایی نیست.")
    u = users.find_one({"name": target})
    if not u:
        return bot.reply_to(m, "❌ کاربر یافت نشد.")
    if m.text.lower() == "بن":
        users.update_one({"user_id": u["user_id"]}, {"$set": {"banned": True}})
        bot.reply_to(m, f"🚫 {target} بن شد.")
    else:
        users.update_one({"user_id": u["user_id"]}, {"$set": {"banned": False}})
        bot.reply_to(m, f"✅ {target} آزاد شد.")

@bot.message_handler(commands=["خاموش","روشن"])
def toggle(m):
    if m.from_user.id != ADMIN_ID:
        return
    bot_status["enabled"] = (m.text == "/روشن")
    bot.reply_to(m, "🟢 ربات فعال شد." if bot_status["enabled"] else "🔴 ربات خاموش شد.")

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=PORT)
