import telebot
from telebot import types
import requests
import datetime
from flask import Flask, request
import threading

# ==== تنظیمات ربات ====
TOKEN = '8175470749:AAGjaYSVosmfk6AmuqXvcVbSUJAqS200q3c'
CHANNEL = '@netgoris'
GEMINI_API_KEY = 'AIzaSyDvvYZuvKhwCMMGPE7NHV2JkkhPTJ2BHQ0'
WEBHOOK_URL = 'https://chatgpt-qg71.onrender.com'
PORT = 10000

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ==== تاریخچه چت موقتی (در رم) ====
user_histories = {}  # user_id: [(timestamp, message)]

# ==== بررسی عضویت در کانال ====
def is_member(user_id):
    try:
        status = bot.get_chat_member(CHANNEL, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

# ==== ذخیره پیام در حافظه ۲۴ساعته ====
def store_message(user_id, message):
    now = datetime.datetime.utcnow()
    if user_id not in user_histories:
        user_histories[user_id] = []
    user_histories[user_id].append((now, message))
    # حذف پیام‌های قدیمی‌تر از ۲۴ ساعت
    user_histories[user_id] = [(t, m) for t, m in user_histories[user_id] if (now - t).total_seconds() < 86400]

def get_history(user_id):
    if user_id in user_histories:
        return [msg for _, msg in user_histories[user_id]]
    return []

# ==== وب‌هوک ====
@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'ok', 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running."

# ==== هندل /start ====
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if not is_member(user_id):
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("📢 ورود به کانال", url=f"https://t.me/{CHANNEL[1:]}")
        btn2 = types.InlineKeyboardButton("✅ تایید عضویت", callback_data='check_join')
        markup.add(btn1)
        markup.add(btn2)
        msg = bot.send_message(user_id, "🌟 برای استفاده از ربات ابتدا در کانال عضو شوید:", reply_markup=markup)
        bot.pin_chat_message(user_id, msg.message_id)
    else:
        ask_ai_and_edit(user_id, "سلام به ربات خوش اومدی!")

# ==== تایید عضویت از دکمه ====
@bot.callback_query_handler(func=lambda c: c.data == 'check_join')
def check_join(call):
    user_id = call.from_user.id
    if is_member(user_id):
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
        ask_ai_and_edit(user_id, "سلام مجدد! آماده‌ام پاسخ بدم.")
    else:
        bot.answer_callback_query(call.id, "⛔️ هنوز عضو نشدی!", show_alert=True)

# ==== پاسخ هوش مصنوعی Gemini ====
def ask_ai_and_edit(user_id, input_text):
    # ذخیره پیام
    store_message(user_id, input_text)
    # ارسال پیام اولیه
    msg = bot.send_message(user_id, "…")
    # آماده‌سازی context برای Gemini
    history = get_history(user_id)
    parts = [{"text": line} for line in history]
    # تماس با Gemini API
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}'
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": parts}]}
    try:
        r = requests.post(url, headers=headers, json=payload)
        res = r.json()
        reply = res['candidates'][0]['content']['parts'][0]['text']
    except:
        reply = "❌ خطا در دریافت پاسخ از Gemini"

    # ذخیره پاسخ در تاریخچه
    store_message(user_id, reply)
    try:
        bot.edit_message_text(reply, chat_id=user_id, message_id=msg.message_id)
    except:
        bot.send_message(user_id, reply)

# ==== پاسخ به همه پیام‌ها ====
@bot.message_handler(func=lambda message: True)
def chat_handler(message):
    user_id = message.from_user.id
    if is_member(user_id):
        ask_ai_and_edit(user_id, message.text)
    else:
        start(message)

# ==== راه‌اندازی وب‌هوک ====
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

# ==== اجرای اپلیکیشن Flask در thread جدا ====
def run():
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    threading.Thread(target=run).start()
    set_webhook()
