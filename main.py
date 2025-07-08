from flask import Flask, request
import telebot
from telebot import types
from pymongo import MongoClient
import os
import re
import time
from collections import defaultdict

BOT_TOKEN = "7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE"
FORCE_JOIN_CHANNEL = "@netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:p%40ssw0rd%2729%27%21@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
OWNER_ID = 5637609683
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)
client = MongoClient(MONGO_URI)
db = client["chatroom_bot"]

spam_tracker = defaultdict(list)
mute_until = {}
stored_messages = {}
banned_ids = set()
bot_enabled = True

def has_joined(user_id):
    try:
        status = bot.get_chat_member(chat_id=FORCE_JOIN_CHANNEL, user_id=user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def is_english(text):
    return bool(re.fullmatch(r'[A-Za-z0-9\s]+', text.strip()))

def is_name_valid(name):
    return is_english(name) and "admin" not in name.lower()

def is_name_taken(name):
    return db.users.find_one({"display_name": name.lower()}) is not None

def save_user(user_id, username, name):
    db.users.insert_one({
        "user_id": user_id,
        "username": username,
        "display_name": name
    })

@bot.message_handler(commands=['start'])
def start_handler(msg):
    uid = msg.from_user.id
    if db.banned_users.find_one({"user_id": uid}) or uid in banned_ids:
        return
    if db.users.find_one({"user_id": uid}):
        bot.send_message(msg.chat.id, "✅ قبلاً ثبت‌نام کردی.")
        return
    if not has_joined(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{FORCE_JOIN_CHANNEL[1:]}"),
            types.InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join")
        )
        bot.send_message(msg.chat.id, f"🌐 لطفاً ابتدا عضو کانال {FORCE_JOIN_CHANNEL} شو:", reply_markup=markup)
    else:
        show_rules_button(msg.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def recheck_join(call):
    if has_joined(call.from_user.id):
        bot.edit_message_text("✅ عضو شدی. حالا قوانین رو بخون:", call.message.chat.id, call.message.message_id)
        show_rules_button(call.message.chat.id)
    else:
        bot.answer_callback_query(call.id, "❌ هنوز عضو کانال نیستی!")

def show_rules_button(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📜 قوانین", callback_data="show_rules"))
    bot.send_message(chat_id, "📘 لطفاً قوانین زیر را بخون:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "show_rules")
def show_rules(call):
    rules = """
👋 سلام! خوش اومدی.

🔹 اینجا یه چت‌روم نیمه‌ناشناس برای گپ دوستانه‌ست. قوانین:

1️⃣ فقط گفت‌وگوی سالم؛ تبلیغ ممنوع  
2️⃣ گیف = ممنوع | عکس، آهنگ = اوکی  
3️⃣ اسپم = سکوت ۲ دقیقه  
4️⃣ احترام واجبه. تخلف → ریپورت با "گزارش"

✅ بیا یک اسم انگلیسی وارد کن و شروع کنیم!
"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ تایید قوانین", callback_data="accept_rules"))
    bot.edit_message_text(rules, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "accept_rules")
def ask_name(call):
    bot.send_message(call.message.chat.id, "📝 یه نام فقط انگلیسی بنویس (نباید 'admin' توش باشه):")
    bot.register_next_step_handler(call.message, name_step)

def name_step(msg):
    name = msg.text.strip()
    if not is_name_valid(name):
        bot.send_message(msg.chat.id, "❌ فقط حروف انگلیسی مجازن و 'admin' نباید باشه.")
        bot.register_next_step_handler(msg, name_step)
        return
    if is_name_taken(name):
        bot.send_message(msg.chat.id, "❌ این اسم تکراریه. یکی دیگه انتخاب کن:")
        bot.register_next_step_handler(msg, name_step)
        return
    save_user(msg.from_user.id, msg.from_user.username, name)
    bot.send_message(msg.chat.id, f"✅ خوش اومدی {name}!")

@bot.message_handler(content_types=['text', 'photo', 'audio', 'document', 'video'])
def handle_messages(msg):
    uid = msg.from_user.id
    now = time.time()
    if not bot_enabled or uid in banned_ids or db.banned_users.find_one({"user_id": uid}):
        return
    if uid in mute_until and now < mute_until[uid]:
        return
    spam_tracker[uid].append(now)
    spam_tracker[uid] = [t for t in spam_tracker[uid] if now - t < 1]
    if len(spam_tracker[uid]) > 3:
        mute_until[uid] = now + 120
        bot.send_message(msg.chat.id, "⛔️ اسپم = سکوت ۲ دقیقه")
        return

    user = db.users.find_one({"user_id": uid})
    name = user["display_name"] if user else "ناشناس"
    stored_messages[msg.message_id] = {"text": msg.text if msg.text else "رسانه", "name": name}

    if msg.reply_to_message and msg.reply_to_message.message_id in stored_messages:
        quoted = stored_messages[msg.reply_to_message.message_id]
        reply = f"📨 پاسخ به {quoted['name']}:\n\"{quoted['text']}\"\n\n🗣 {name}:\n"
    else:
        reply = f"🗣 {name}:\n"

    if msg.text:
        bot.send_message(msg.chat.id, reply + msg.text)
    elif msg.caption:
        bot.send_message(msg.chat.id, reply + msg.caption)

@bot.message_handler(content_types=['animation'])
def block_gif(msg):
    bot.delete_message(msg.chat.id, msg.message_id)
    bot.send_message(msg.chat.id, "❌ ارسال گیف مجاز نیست.")

@bot.message_handler(func=lambda m: m.reply_to_message and m.text.lower() == "گزارش")
def handle_report(m):
    try:
        bot.forward_message(OWNER_ID, m.chat.id, m.reply_to_message.message_id)
        bot.send_message(OWNER_ID, f"📣 گزارش جدید از @{m.from_user.username or 'کاربر'}")
        bot.send_message(m.chat.id, "✅ پیام گزارش شد.")
    except:
        bot.send_message(m.chat.id, "❌ گزارش ارسال نشد.")

@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and m.reply_to_message)
def admin_reply_control(m):
    target = m.reply_to_message.from_user.id
    if m.text.lower() == "بن":
        banned_ids.add(target)
        db.banned_users.insert_one({"user_id": target})
        bot.send_message(m.chat.id, "🚫 کاربر بن شد.")
    elif m.text.lower() == "آنبن":
        banned_ids.discard(target)
        db.banned_users.delete_one({"user_id": target})
        bot.send_message(m.chat.id, "✅ کاربر آزاد شد.")

@bot.message_handler(commands=['on', 'off'])
def toggle_bot(m):
    global bot_enabled
    if m.from_user.id != OWNER_ID:
        return
    bot_enabled = m.text == "/on"
    bot.send_message(m.chat.id, f"⚙️ ربات الان {'فعاله ✅' if bot_enabled else 'خاموشه 📴'}")

@app.route(f'/{BOT_TOKEN}', methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok", 200

@app.route("/")
def index():
    return "ربات فعاله ✅"

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
