from flask import Flask, request
import telebot
from telebot.types import *
import requests
import time

# اطلاعات تنظیمات
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
ADMIN_ID = 5637609683
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"
AI_API_URL = "https://starsshoptl.ir/Ai/index.php?text="

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)
user_messages = {}
banned_users = set()

# کیبورد اصلی
def main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🤖 هوش مصنوعی", "📊 پنل مدیریت")
    kb.add("ℹ️ راهنما", "📞 پشتیبانی")
    return kb

# دکمه‌های شیشه‌ای
def inline_buttons():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💻 وبسایت", url=WEBHOOK_URL))
    markup.add(InlineKeyboardButton("🎯 پشتیبانی تلگرام", url="https://t.me/NetGoris"))
    return markup

# ضد اسپم
def is_spamming(user_id):
    now = time.time()
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id] = [t for t in user_messages[user_id] if now - t < 120]
    user_messages[user_id].append(now)
    return len(user_messages[user_id]) >= 4

# استارت
@bot.message_handler(commands=["start"])
def start(message):
    if is_spamming(message.chat.id):
        return
    if message.chat.id in banned_users:
        return
    bot.send_message(message.chat.id, f"سلام {message.from_user.first_name} عزیز 👋\nبه ربات هوش مصنوعی خوش اومدی!", reply_markup=main_keyboard())
    bot.send_message(message.chat.id, "👇 دکمه‌های دسترسی سریع:", reply_markup=inline_buttons())
    if message.chat.id != ADMIN_ID:
        bot.send_message(ADMIN_ID, f"📥 کاربر جدید:\nنام: {message.from_user.first_name}\nآیدی عددی: <code>{message.chat.id}</code>")

# راهنما
@bot.message_handler(func=lambda msg: msg.text == "ℹ️ راهنما")
def help_menu(message):
    if is_spamming(message.chat.id):
        return
    text = "📚 راهنمای ربات:\n\n" \
           "🤖 هوش مصنوعی: ارسال سوال یا متن برای دریافت پاسخ\n" \
           "📞 پشتیبانی: ارسال پیام به مدیر\n" \
           "📊 پنل مدیریت: فقط برای ادمین فعال است\n"
    bot.send_message(message.chat.id, text, reply_markup=inline_buttons())

# پشتیبانی
@bot.message_handler(func=lambda msg: msg.text == "📞 پشتیبانی")
def support(message):
    if is_spamming(message.chat.id):
        return
    bot.send_message(message.chat.id, "لطفاً سوال خود را ارسال کنید:")
    bot.register_next_step_handler(message, forward_to_admin)

def forward_to_admin(message):
    bot.send_message(ADMIN_ID, f"📨 پیام از کاربر:\n{message.text}\n🆔 <code>{message.chat.id}</code>")
    bot.send_message(message.chat.id, "✅ پیام شما به مدیر ارسال شد.")

# چت هوش مصنوعی
@bot.message_handler(func=lambda msg: msg.text == "🤖 هوش مصنوعی")
def ai_chat(message):
    if is_spamming(message.chat.id):
        return
    bot.send_message(message.chat.id, "لطفاً سوال خود را ارسال کنید:")
    bot.register_next_step_handler(message, send_to_ai)

def send_to_ai(message):
    if is_spamming(message.chat.id):
        return
    r = requests.get(AI_API_URL + message.text)
    if r.ok:
        bot.send_message(message.chat.id, f"🤖 پاسخ هوش مصنوعی:\n{r.text}")
    else:
        bot.send_message(message.chat.id, "❌ خطا در دریافت پاسخ از هوش مصنوعی")

# پنل مدیریت
@bot.message_handler(func=lambda msg: msg.text == "📊 پنل مدیریت" and msg.chat.id == ADMIN_ID)
def admin_panel(message):
    total = len(user_messages)
    text = f"👤 آمار ربات:\n\n" \
           f"👥 کاربران: {total}\n" \
           f"🚫 لیست بن: {len(banned_users)}"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("➕ بن کاربر", callback_data="ban"))
    markup.add(InlineKeyboardButton("➖ آن‌بن کاربر", callback_data="unban"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "ban")
def ban_user(call):
    bot.send_message(call.message.chat.id, "لطفاً آیدی عددی کاربر را بفرستید:")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_ban)

def process_ban(message):
    try:
        user_id = int(message.text)
        banned_users.add(user_id)
        bot.send_message(message.chat.id, f"✅ کاربر <code>{user_id}</code> بن شد.")
    except:
        bot.send_message(message.chat.id, "❌ آیدی نامعتبر است.")

@bot.callback_query_handler(func=lambda call: call.data == "unban")
def unban_user(call):
    bot.send_message(call.message.chat.id, "آیدی عددی کاربر را بفرستید:")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_unban)

def process_unban(message):
    try:
        user_id = int(message.text)
        banned_users.discard(user_id)
        bot.send_message(message.chat.id, f"✅ کاربر <code>{user_id}</code> از بن خارج شد.")
    except:
        bot.send_message(message.chat.id, "❌ آیدی نامعتبر است.")

# پاسخ ادمین
@bot.message_handler(func=lambda msg: msg.chat.id == ADMIN_ID and msg.reply_to_message)
def reply_to_user(message):
    try:
        lines = message.reply_to_message.text.split("\n")
        user_id = int(lines[-1].replace("🆔 ", "").replace("<code>", "").replace("</code>", ""))
        bot.send_message(user_id, f"📢 پاسخ مدیر:\n{message.text}")
    except:
        bot.send_message(ADMIN_ID, "❗ لطفاً روی پیام کاربر ریپلای کنید.")

# روت سلامت و وب‌هوک
@app.route("/", methods=["GET", "POST"])
def index():
    return "✅ ربات فعال است."

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.stream.read().decode("utf-8")
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    return "OK", 200

# تنظیم وب‌هوک
def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    res = requests.post(url, data={"url": f"{WEBHOOK_URL}/{BOT_TOKEN}"})
    print("وضعیت وب‌هوک:", res.text)

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=5000)
