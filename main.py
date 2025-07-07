import telebot
from telebot import types
from flask import Flask, request
import re
from pymongo import MongoClient
import os

# ====== تنظیمات ======
BOT_TOKEN = "7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE"
OWNER_ID = 5637609683
FORCE_JOIN_CHANNEL = "@netgoris"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"
PORT = 100
MONGO_URI = "mongodb+srv://mohsenfeizi1386:p%40s sw0 rd%279%27%21@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
client = MongoClient(MONGO_URI)
db = client["chatroom_bot"]

# ====== توابع کمکی ======

def is_english_name(text):
    return bool(re.fullmatch(r'[A-Za-z0-9\s]+', text.strip()))

def is_name_taken(name):
    return db.users.find_one({"display_name": name}) is not None

def save_user(user_id, username, name):
    db.users.insert_one({
        "user_id": user_id,
        "username": username,
        "display_name": name
    })

def has_joined(user_id):
    try:
        status = bot.get_chat_member(chat_id=FORCE_JOIN_CHANNEL, user_id=user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

# ====== هندلر استارت ======

@bot.message_handler(commands=['start'])
def start_handler(message):
    if not has_joined(message.from_user.id):
        join_msg = f"🌟 برای استفاده از ربات، ابتدا عضو کانال شوید: {FORCE_JOIN_CHANNEL}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{FORCE_JOIN_CHANNEL[1:]}"))
        bot.send_message(message.chat.id, join_msg, reply_markup=markup)
        return

    rules_button = types.InlineKeyboardMarkup()
    rules_button.add(types.InlineKeyboardButton("📜 قوانین", callback_data="show_rules"))
    bot.send_message(message.chat.id, "✅ لطفاً قوانین را مطالعه نمایید:", reply_markup=rules_button)

# ====== هندلر قوانین ======

@bot.callback_query_handler(func=lambda c: c.data == "show_rules")
def show_rules(call):
    rules = f"""
سلام کاربر @{call.from_user.username or 'دوست عزیز'}  
به ربات Chat Room خوش اومدی 🌟

اینجا آزادی که به‌صورت ناشناس با سایر اعضا چت کنی.  
اما قوانینی هست که باید رعایت کنی:

1» فقط برای چت و آشناییه. تبلیغ یا درخواست پول ممنوعه.  
2» ارسال گیف ممنوع؛ عکس و موسیقی آزاد با محتوای سالم.  
3» اسپم = سکوت ۲ دقیقه‌ای  
4» احترام؛ توهین = گزارش با دستور (گزارش)

🚨 آپدیت‌های جدید در راهه، دوستانتو دعوت کن!
"""
    confirm = types.InlineKeyboardMarkup()
    confirm.add(types.InlineKeyboardButton("✅ تایید قوانین", callback_data="accept_rules"))
    bot.edit_message_text(rules, call.message.chat.id, call.message.message_id, reply_markup=confirm)

# ====== تایید قوانین ======

@bot.callback_query_handler(func=lambda c: c.data == "accept_rules")
def accept_rules(call):
    bot.send_message(call.message.chat.id, "✅ قوانین تایید شد. لطفاً یک نام نمایشی **فقط به انگلیسی** ارسال کنید:")
    bot.register_next_step_handler(call.message, name_step)

def name_step(msg):
    name = msg.text.strip()
    if not is_english_name(name):
        bot.send_message(msg.chat.id, "❌ فقط از حروف انگلیسی استفاده کن. دوباره امتحان کن:")
        bot.register_next_step_handler(msg, name_step)
        return

    if is_name_taken(name):
        bot.send_message(msg.chat.id, "❌ این نام قبلاً انتخاب شده. لطفاً نام متفاوتی وارد کن:")
        bot.register_next_step_handler(msg, name_step)
        return

    save_user(msg.from_user.id, msg.from_user.username, name)
    bot.send_message(msg.chat.id, f"✅ ثبت شد! از این به بعد پیامهات با نام `{name}` در چت ظاهر می‌شه.")

from collections import defaultdict
import time

spam_tracker = defaultdict(list)
mute_list = {}

@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'audio', 'document', 'sticker', 'video'])
def handle_messages(msg):
    user_id = msg.from_user.id

    # چک سکوت
    if user_id in mute_list and time.time() < mute_list[user_id]:
        return

    # ضد اسپم
    spam_tracker[user_id].append(time.time())
    spam_tracker[user_id] = [t for t in spam_tracker[user_id] if time.time() - t < 1]

    if len(spam_tracker[user_id]) > 3:
        mute_list[user_id] = time.time() + 120
        bot.send_message(msg.chat.id, "⛔️ به دلیل اسپم، شما به مدت ۲ دقیقه در سکوت هستید.")
        return

    # جلوگیری از گیف
    if msg.content_type == 'animation':
        bot.delete_message(msg.chat.id, msg.message_id)
        bot.send_message(msg.chat.id, "❌ ارسال گیف مجاز نیست.")
        return

    # نمایش نام بالای پیام
    user = db.users.find_one({"user_id": user_id})
    name = user['display_name'] if user else "ناشناس"
    try:
        bot.send_message(msg.chat.id, f"🗣 {name}:\n{msg.text}" if msg.text else "پیام دریافت شد.")
    except:
        pass

@bot.message_handler(func=lambda m: m.reply_to_message and m.text.lower() == "گزارش")
def report_message(msg):
    if msg.reply_to_message:
        try:
            bot.forward_message(OWNER_ID, msg.chat.id, msg.reply_to_message.message_id)
            bot.send_message(OWNER_ID, f"📢 گزارش جدید از @{msg.from_user.username or 'کاربر'}")
            bot.send_message(msg.chat.id, "✅ پیام با موفقیت گزارش شد.")
        except:
            bot.send_message(msg.chat.id, "❌ خطا در ارسال گزارش.")

bot_enabled = True
banned_ids = set()

@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and m.reply_to_message)
def admin_controls(msg):
    target_id = msg.reply_to_message.from_user.id
    text = msg.text.lower()

    if text == "بن":
        banned_ids.add(target_id)
        db.banned_users.insert_one({"user_id": target_id})
        bot.send_message(msg.chat.id, "🚫 کاربر بن شد.")
    elif text == "آنبن":
        banned_ids.discard(target_id)
        db.banned_users.delete_one({"user_id": target_id})
        bot.send_message(msg.chat.id, "✅ کاربر آزاد شد.")

@bot.message_handler(commands=['off', 'on'])
def toggle_bot(msg):
    global bot_enabled
    if msg.from_user.id != OWNER_ID:
        return
    bot_enabled = msg.text == "/on"
    bot.send_message(msg.chat.id, f"✅ وضعیت ربات: {'فعال' if bot_enabled else 'غیرفعال'}")

# هندلر محدودیت استفاده از ربات
@bot.message_handler(func=lambda m: True)
def gate_check(msg):
    if not bot_enabled:
        return
    if msg.from_user.id in banned_ids:
        return
    # ادامه پردازش...
# ====== webhook ======

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok", 200

@app.route("/")
def index():
    return "ربات فعال است ✅"

# ====== اجرا ======

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
