from flask import Flask, request
import telebot
from telebot import types
from pymongo import MongoClient
import re

# تنظیمات
BOT_TOKEN = "7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE"
FORCE_JOIN_CHANNEL = "@netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:p%40s sw0 rd%279%27%21@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"
OWNER_ID = 5637609683
PORT = 100

# راه‌اندازی
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client["chatroom_bot"]

# توابع کمکی
def has_joined(user_id):
    try:
        status = bot.get_chat_member(chat_id=FORCE_JOIN_CHANNEL, user_id=user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def is_english(text):
    return bool(re.fullmatch(r'[A-Za-z0-9\s]+', text.strip()))

def is_name_valid(name):
    if not is_english(name):
        return False
    if "admin" in name.lower():
        return False
    return True

def is_name_taken(name):
    return db.users.find_one({"display_name": name.lower()}) is not None

def save_user(user_id, username, name):
    db.users.insert_one({
        "user_id": user_id,
        "username": username,
        "display_name": name
    })

# استارت و چک عضویت
@bot.message_handler(commands=['start'])
def start_handler(message):
    uid = message.from_user.id

    if db.users.find_one({"user_id": uid}):
        bot.send_message(message.chat.id, "✅ شما قبلاً ثبت‌نام کردید.")
        return

    if not has_joined(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{FORCE_JOIN_CHANNEL[1:]}"),
            types.InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join")
        )
        bot.send_message(message.chat.id, f"👋 برای ادامه، عضو کانال {FORCE_JOIN_CHANNEL} شوید:", reply_markup=markup)
    else:
        show_rules_button(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def recheck_join(call):
    if has_joined(call.from_user.id):
        bot.edit_message_text("✅ عضویت تایید شد. لطفاً قوانین را مطالعه کنید:", call.message.chat.id, call.message.message_id)
        show_rules_button(call.message.chat.id)
    else:
        bot.answer_callback_query(call.id, "❌ هنوز عضو کانال نیستی!")

def show_rules_button(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📜 قوانین", callback_data="show_rules"))
    bot.send_message(chat_id, "لطفاً قوانین زیر را مطالعه کن:", reply_markup=markup)

# قوانین
@bot.callback_query_handler(func=lambda call: call.data == "show_rules")
def show_rules(call):
    rules = f"""
سلام کاربر @{call.from_user.username or 'دوست عزیز'}  
به ربات Chat Room خوش اومدی 🌟

اینجا آزادی که ناشناس چت کنی، اما این قوانین رو رعایت کن:

1» استفاده فقط برای سرگرمی و آشنایی. تبلیغات ممنوع.  
2» گیف ممنوع. عکس و موسیقی سالم مجازه.  
3» اسپم = سکوت ۲ دقیقه  
4» محترمانه باش. تخلف = گزارش با (گزارش)

⛑ ربات در نسخه اولیه‌ست. دوستاتو دعوت کن!
"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ تایید قوانین", callback_data="accept_rules"))
    bot.edit_message_text(rules, call.message.chat.id, call.message.message_id, reply_markup=markup)

# تایید قوانین و دریافت اسم
@bot.callback_query_handler(func=lambda call: call.data == "accept_rules")
def ask_name(call):
    bot.send_message(call.message.chat.id, "📝 لطفاً یک نام فقط انگلیسی وارد کن (نباید شامل admin باشه):")
    bot.register_next_step_handler(call.message, save_name_step)

def save_name_step(msg):
    name = msg.text.strip()

    if not is_name_valid(name):
        bot.send_message(msg.chat.id, "❌ فقط حروف انگلیسی مجازه و کلمه 'admin' نباید در نام باشه. دوباره امتحان کن:")
        bot.register_next_step_handler(msg, save_name_step)
        return

    if is_name_taken(name):
        bot.send_message(msg.chat.id, "❌ این نام قبلاً ثبت شده. لطفاً نام دیگری وارد کن:")
        bot.register_next_step_handler(msg, save_name_step)
        return

    save_user(msg.from_user.id, msg.from_user.username, name)
    bot.send_message(msg.chat.id, f"✅ نام {name} با موفقیت ثبت شد. خوش اومدی!")


import time
from collections import defaultdict

# وضعیت کلی ربات
bot_enabled = True
banned_ids = set()
spam_tracker = defaultdict(list)
mute_until = {}

# نمایش پیام و نام کاربر
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'audio', 'document', 'video', 'animation'])
def handle_all(msg):
    uid = msg.from_user.id

    # بررسی فعال بودن ربات
    if not bot_enabled or uid in banned_ids:
        return

    # ضداسپم بر اساس پیام در یک ثانیه
    now = time.time()
    spam_tracker[uid].append(now)
    spam_tracker[uid] = [t for t in spam_tracker[uid] if now - t < 1]

    if len(spam_tracker[uid]) > 3:
        mute_until[uid] = now + 120
        bot.send_message(msg.chat.id, "⛔️ به دلیل ارسال بیش‌ازحد، ۲ دقیقه در سکوت هستی.")
        return

    # سکوت موقت
    if uid in mute_until and time.time() < mute_until[uid]:
        return

    # حذف گیف
    if msg.content_type == 'animation':
        bot.delete_message(msg.chat.id, msg.message_id)
        bot.send_message(msg.chat.id, "❌ ارسال گیف مجاز نیست.")
        return

    # دریافت نام ثبت‌شده
    user = db.users.find_one({"user_id": uid})
    name = user["display_name"] if user else "ناشناس"

    # ارسال پیام با نام کاربر
    if msg.text:
        reply_markup = None
        bot.send_message(msg.chat.id, f"🗣 {name}:\n{msg.text}", reply_to_message_id=msg.message_id if msg.reply_to_message else None, reply_markup=reply_markup)

@bot.message_handler(func=lambda m: m.reply_to_message and m.text.lower() == "گزارش")
def handle_report(msg):
    try:
        origin_msg = msg.reply_to_message
        bot.forward_message(OWNER_ID, origin_msg.chat.id, origin_msg.message_id)
        bot.send_message(OWNER_ID, f"📣 گزارش جدید از @{msg.from_user.username or 'کاربر ناشناس'}")
        bot.send_message(msg.chat.id, "✅ پیام گزارش شد.")
    except:
        bot.send_message(msg.chat.id, "❌ خطا در ارسال گزارش.")

# بن و آن‌بن با ریپلای
@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and m.reply_to_message)
def admin_reply_commands(msg):
    target_id = msg.reply_to_message.from_user.id
    cmd = msg.text.lower()

    if cmd == "بن":
        banned_ids.add(target_id)
        db.banned_users.insert_one({"user_id": target_id})
        bot.send_message(msg.chat.id, f"🚫 کاربر {target_id} بن شد.")
    elif cmd == "آنبن":
        banned_ids.discard(target_id)
        db.banned_users.delete_one({"user_id": target_id})
        bot.send_message(msg.chat.id, f"✅ کاربر {target_id} آزاد شد.")

# روشن و خاموش کردن ربات
@bot.message_handler(commands=['on', 'off'])
def toggle_bot(msg):
    global bot_enabled
    if msg.from_user.id != OWNER_ID:
        return

    if msg.text == '/on':
        bot_enabled = True
        bot.send_message(msg.chat.id, "✅ ربات فعال شد.")
    elif msg.text == '/off':
        bot_enabled = False
        bot.send_message(msg.chat.id, "🛑 ربات غیرفعال شد.")

# حافظه موقتی پیام‌ها
stored_messages = {}

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_messages_with_quotes(msg):
    user = db.users.find_one({"user_id": msg.from_user.id})
    name = user["display_name"] if user else "ناشناس"

    # ذخیره پیام‌ها برای ریپلای بعدی
    stored_messages[msg.message_id] = {
        "text": msg.text,
        "name": name
    }

    # اگه روی پیام دیگه‌ای ریپلای شده باشه
    if msg.reply_to_message and msg.reply_to_message.message_id in stored_messages:
        original = stored_messages[msg.reply_to_message.message_id]
        quote = f"📨 پاسخ به {original['name']}:\n\"{original['text']}\"\n\n🗣 {name}:\n{msg.text}"
        bot.send_message(msg.chat.id, quote)
    else:
        # پیام معمولی
        bot.send_message(msg.chat.id, f"🗣 {name}:\n{msg.text}")
        
# وبهوک و اجرا
@app.route(f'/{BOT_TOKEN}', methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok"

@app.route("/")
def index():
    return "ربات فعاله ✅"

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
