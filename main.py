import telebot
from flask import Flask, request
import requests
import os
from pymongo import MongoClient

TOKEN = '8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0'
WEBHOOK_URL = f"https://chatgpt-qg71.onrender.com/{TOKEN}"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# اتصال به دیتابیس
client = MongoClient("mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['bot_data']
users = db['users']

OWNER_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"


# جین اجباری
def is_member(user_id):
    try:
        res = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return res.status in ["member", "administrator", "creator"]
    except:
        return False


# وب سرویس‌های هوش مصنوعی
AI_APIS = [
    "https://starsshoptl.ir/Ai/index.php?text={text}",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
]


# هندل استارت
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id

    if not is_member(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        btn1 = telebot.types.InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")
        btn2 = telebot.types.InlineKeyboardButton("✅ بررسی عضویت", callback_data="check")
        markup.add(btn1)
        markup.add(btn2)
        bot.send_message(user_id, "🔒 برای استفاده از ربات لطفاً در کانال ما عضو شوید:", reply_markup=markup)
        return

    if users.find_one({"user_id": user_id}) is None:
        users.insert_one({"user_id": user_id})
        bot.send_message(OWNER_ID, f"👤 کاربر جدید: {message.from_user.first_name} ({user_id})")

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("ℹ️ راهنما", "💬 پشتیبانی")
    bot.send_message(user_id, "🎉 خوش آمدید! از امکانات ربات استفاده کنید.", reply_markup=markup)


# دکمه های شیشه ای
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "check":
        if is_member(call.from_user.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("ℹ️ راهنما", "💬 پشتیبانی")
            bot.send_message(call.from_user.id, "✅ عضویت تایید شد. خوش آمدید!", reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "❌ هنوز عضو نشدید!", show_alert=True)


# پیام‌های متنی
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(message):
    text = message.text
    user_id = message.from_user.id

    if text == "ℹ️ راهنما":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("⬅️ بازگشت", "💬 پشتیبانی")
        bot.send_message(user_id, "📖 راهنمای ربات:\n- لطفاً عضو کانال شوید.\n- ارسال لینک‌های معتبر:\nاینستاگرام، اسپاتیفای، پینترست.\n- رعایت قوانین و احترام الزامی است.\n\n⚠️ لینک غیرمجاز ممنوع است.", reply_markup=markup)

    elif text == "⬅️ بازگشت":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("ℹ️ راهنما", "💬 پشتیبانی")
        bot.send_message(user_id, "🔙 بازگشت به منو اصلی.", reply_markup=markup)

    elif text == "💬 پشتیبانی":
        bot.send_message(user_id, "✉️ پیام خود را ارسال کنید.\nبرای لغو دستور: /cancel")
        bot.register_next_step_handler(message, support_handler)

    elif "instagram.com" in text:
        handle_instagram(message)

    elif "spotify.com" in text:
        handle_spotify(message)

    elif "pin.it" in text or "pinterest.com" in text:
        handle_pinterest(message)

    else:
        handle_ai(message)


# هندل پشتیبانی
def support_handler(message):
    if message.text == "/cancel":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("ℹ️ راهنما", "💬 پشتیبانی")
        bot.send_message(message.chat.id, "❌ پشتیبانی لغو شد.", reply_markup=markup)
        return

    msg = f"📩 پیام جدید:\n\n{message.text}\n\n👤 از: {message.from_user.id}"
    bot.send_message(OWNER_ID, msg)
    bot.send_message(message.chat.id, "✅ پیام شما ارسال شد.")


# هندل هوش مصنوعی
def handle_ai(message):
    text = message.text
    for api in AI_APIS:
        try:
            res = requests.get(api.format(text=text)).json()
            if "Hey there" in res.get("text", "") or "Hey there" in res.get("result", ""):
                bot.send_message(message.chat.id, res.get("result", res.get("text")))
                return
        except:
            continue
    bot.send_message(message.chat.id, "❌ مشکلی در پاسخ‌دهی رخ داد.")


# هندل اینستاگرام
def handle_instagram(message):
    try:
        url = f"https://pouriam.top/eyephp/instagram?url={message.text}"
        res = requests.get(url).json()
        for link in res["links"]:
            bot.send_message(message.chat.id, link)
    except:
        bot.send_message(message.chat.id, "❌ لینک اینستاگرام نامعتبر است.")


# هندل اسپاتیفای
def handle_spotify(message):
    try:
        url = f"http://api.cactus-dev.ir/spotify.php?url={message.text}"
        res = requests.get(url).json()
        bot.send_audio(message.chat.id, res['data']['download_url'])
    except:
        bot.send_message(message.chat.id, "❌ لینک اسپاتیفای نامعتبر است.")


# هندل پینترست
def handle_pinterest(message):
    try:
        url = f"https://haji.s2025h.space/pin/?url={message.text}&client_key=keyvip"
        res = requests.get(url).json()
        bot.send_photo(message.chat.id, res["download_url"])
    except:
        bot.send_message(message.chat.id, "❌ لینک پینترست نامعتبر است.")


# وب هوک و اجرا روی هاست
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return '', 200
    return '', 403


@app.route('/')
def index():
    return "✅ Bot Running."


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=port)
