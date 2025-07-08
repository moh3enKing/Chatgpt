import os
import re
import time
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pymongo import MongoClient
import telebot
from telebot import types

# ================== تنظیمات ====================
TOKEN = "7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE"
WEBHOOK_URL = f"https://chatgpt-qg71.onrender.com/{TOKEN}/"
CHANNEL_ID = "@netgoris"
ADMIN_ID = 5637609683
PORT = 1000
DB_PASSWORD = "p%40ssw0rd%279%27%21"

# ================== اتصال به MongoDB ====================
client = MongoClient(f"mongodb+srv://mohsenfeizi1386:{DB_PASSWORD}@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["chat_room"]
users = db["users"]

# ================== ربات و وب‌سرور ====================
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = FastAPI()

# ================== متغیرها ====================
bot_status = {"enabled": True}
user_messages = {}
SPAM_LIMIT = 4
SPAM_TIME = 120
BANNED_NAMES = ["admin", "mod", "owner", "support", "ادمین", "مدیر", "پشتیبان"]

# ================== توابع کمکی ====================
def is_user_in_channel(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ["member", "administrator", "creator"]
    except:
        return False

def is_english(text):
    return bool(re.match(r"^[A-Za-z0-9 _-]+$", text))

def contains_graphic_characters(text):
    return any(ord(c) > 127 for c in text)

def extract_sender_name_from_text(text):
    match = re.search(r"<b>(.*?)</b>", text)
    return match.group(1).strip() if match else None

# ================== START ====================
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    user = users.find_one({"user_id": user_id})
    if user and user.get("name"):
        bot.send_message(user_id, f"🌟 خوش آمدی {user['name']}!\nمی‌تونی چت رو شروع کنی.")
        return

    if not is_user_in_channel(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"))
        markup.add(types.InlineKeyboardButton("✅ تایید عضویت", callback_data="confirm_join"))
        bot.send_message(user_id, "🔐 برای استفاده، اول عضو کانال شو:", reply_markup=markup)
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📜 قوانین", callback_data="show_rules"))
    bot.send_message(user_id, "📘 آیا قوانین را تایید می‌کنید؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "confirm_join")
def confirm_join(c):
    if not is_user_in_channel(c.from_user.id):
        bot.answer_callback_query(c.id, "⛔️ هنوز عضو نشدی.")
        return
    try:
        bot.delete_message(c.message.chat.id, c.message.message_id)
    except:
        pass
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📜 قوانین", callback_data="show_rules"))
    bot.send_message(c.from_user.id, "📘 آیا قوانین ربات را تایید می‌کنید؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "show_rules")
def show_rules(c):
    rules = f"""سلام کاربر @{c.from_user.username or 'user'}

به ربات Chat Room خوش آمدید.

اینجا شما آزاد هستید که به صورت ناشناس با دیگر اعضا چت کنید.

📌 قوانین:

1️⃣ تبلیغات، درخواست پول ممنوع ❌  
2️⃣ ارسال گیف ممنوع. عکس و موزیک آزاده، ولی محتوای غیر اخلاقی ممنوع  
3️⃣ ضد اسپم فعال است: اسپم = سکوت ۲ دقیقه  
4️⃣ احترام متقابل واجب! ریپلای و گزارش تخلف برای ادمین

دوستانتون رو دعوت کنید. نسخه اولیه ربات هست و آپدیت میشه :)
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✅ تایید قوانین")
    bot.edit_message_text(rules, c.from_user.id, c.message.message_id)
    bot.send_message(c.from_user.id, "📌 لطفاً قوانین را تایید کنید:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "✅ تایید قوانین")
def ask_name(m):
    markup = types.ForceReply(selective=False)
    bot.send_message(m.chat.id, "📝 لطفاً یک نام انگلیسی برای خودت وارد کن:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.reply_to_message and "نام انگلیسی" in m.reply_to_message.text)
def handle_name(m):
    name = m.text.strip()
    if not is_english(name):
        return bot.send_message(m.chat.id, "❌ فقط حروف انگلیسی مجازن.")
    if contains_graphic_characters(name):
        return bot.send_message(m.chat.id, "⚠️ لطفاً فونت ساده بنویس.")
    if any(b in name.lower() for b in BANNED_NAMES):
        return bot.send_message(m.chat.id, "⛔️ این اسم مجاز نیست.")

    users.update_one({"user_id": m.from_user.id}, {"$set": {"user_id": m.from_user.id, "name": name, "banned": False, "muted": False}}, upsert=True)
    bot.send_message(m.chat.id, f"✅ نامت ثبت شد: {name}\nحالا می‌تونی چت کنی!")

# ================== چت ناشناس + کنترل‌ها ====================
@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "voice", "audio", "video", "document", "animation", "sticker"])
def chat(m):
    uid = m.from_user.id
    user = users.find_one({"user_id": uid})
    if not user or not user.get("name"):
        return bot.send_message(uid, "⛔️ اول ثبت‌نام کن /start")

    if not bot_status["enabled"] and uid != ADMIN_ID:
        return

    if user.get("banned"):
        return bot.send_message(uid, "🚫 بن شدی.")

    if m.content_type == "animation" or (m.document and m.document.mime_type == "image/gif"):
        return bot.send_message(uid, "❌ گیف ممنوعه.")

    # ضد اسپم
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

# ================== بن / آنبن و کنترل ربات ====================
@bot.message_handler(func=lambda m: m.reply_to_message and m.text.lower() in ["بن", "آنبن"])
def admin_ban(m):
    if m.from_user.id != ADMIN_ID:
        return
    target_name = extract_sender_name_from_text(m.reply_to_message.text or m.reply_to_message.caption or "")
    if not target_name:
        return bot.reply_to(m, "❌ نام کاربر پیدا نشد.")
    user = users.find_one({"name": target_name})
    if not user:
        return bot.reply_to(m, "❌ کاربر موجود نیست.")
    if m.text.lower() == "بن":
        users.update_one({"user_id": user["user_id"]}, {"$set": {"banned": True}})
        bot.reply_to(m, f"🚫 {target_name} بن شد.")
    else:
        users.update_one({"user_id": user["user_id"]}, {"$set": {"banned": False}})
        bot.reply_to(m, f"✅ {target_name} آزاد شد.")

@bot.message_handler(commands=["خاموش", "روشن"])
def toggle(m):
    if m.from_user.id != ADMIN_ID:
        return
    bot_status["enabled"] = m.text == "/روشن"
    bot.reply_to(m, "🟢 فعال شد." if bot_status["enabled"] else "🔴 خاموش شد.")

# ================== FastAPI Webhook ====================
@app.post(f"/{TOKEN}/")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    update = telebot.types.Update.de_json(data)
    background_tasks.add_task(bot.process_new_updates, [update])
    return JSONResponse({"ok": True})

def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

if __name__ == "__main__":
    set_webhook()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
