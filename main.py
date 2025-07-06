import telebot
from flask import Flask, request
import requests
import pymongo
import os

# تنظیمات
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
CHANNEL_USERNAME = "@netgoris"
ADMIN_ID = 5637609683
MONGO_URL = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "chatgpt-qg71.onrender.com"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# اتصال به دیتابیس
mongo_client = pymongo.MongoClient(MONGO_URL)
db = mongo_client["TellGPT"]
users_col = db["users"]
bans_col = db["bans"]

# تنظیم وب‌هوک
def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
    res = requests.get(url)
    print(res.text)

# بررسی عضویت
def is_member(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# دریافت استارت
@bot.message_handler(commands=["start"])
def start_handler(message):
    user_id = message.from_user.id
    if bans_col.find_one({"user_id": user_id}):
        bot.reply_to(message, "شما مسدود شده‌اید.")
        return

    if not is_member(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"))
        markup.add(telebot.types.InlineKeyboardButton("تایید عضویت", callback_data="verify"))
        bot.send_message(user_id, "⚠️ لطفاً ابتدا در کانال عضو شوید سپس تایید را بزنید.", reply_markup=markup)
    else:
        welcome_msg = "🎉 به ربات خوش آمدید!\nاز دکمه زیر می‌توانید راهنما را دریافت کنید."
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📖 راهنما", "💬 پشتیبانی")
        bot.send_message(user_id, welcome_msg, reply_markup=markup)
        
        if not users_col.find_one({"user_id": user_id}):
            users_col.insert_one({"user_id": user_id})
            bot.send_message(ADMIN_ID, f"کاربر جدید: [{user_id}](tg://user?id={user_id})", parse_mode="Markdown")

# دکمه تایید عضویت
@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify(call):
    if is_member(call.from_user.id):
        welcome_msg = "🎉 عضویت تایید شد! خوش آمدید."
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📖 راهنما", "💬 پشتیبانی")
        bot.send_message(call.from_user.id, welcome_msg, reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "هنوز عضو کانال نیستید!", show_alert=True)

# دکمه‌های کیبورد
@bot.message_handler(func=lambda msg: msg.text == "📖 راهنما")
def help_message(message):
    help_text = (
        "📖 راهنمای استفاده از ربات:\n\n"
        "✅ عضویت در کانال الزامی است.\n"
        "✅ ارسال لینک‌های معتبر:\n"
        "- اینستاگرام\n"
        "- اسپاتیفای\n"
        "- پینترست\n"
        "- ساخت عکس با متن\n"
        "🚫 هرگونه تخلف مسدودیت دارد."
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(func=lambda msg: msg.text == "💬 پشتیبانی")
def support_handler(message):
    bot.send_message(message.chat.id, "پیام خود را ارسال کنید، پشتیبانی به شما پاسخ خواهد داد.")
    users_col.update_one({"user_id": message.from_user.id}, {"$set": {"support": True}}, upsert=True)

# مدیریت پیام‌های کاربر
@bot.message_handler(func=lambda msg: True, content_types=["text"])
def text_handler(message):
    user_id = message.from_user.id
    user = users_col.find_one({"user_id": user_id})

    if user and user.get("support"):
        bot.send_message(ADMIN_ID, f"📩 پیام پشتیبانی از [{user_id}](tg://user?id={user_id}):\n{message.text}", parse_mode="Markdown")
        users_col.update_one({"user_id": user_id}, {"$set": {"support": False}})
        bot.send_message(user_id, "✅ پیام شما ارسال شد.")
        return

    if not is_member(user_id):
        bot.send_message(user_id, "لطفاً ابتدا عضو کانال شوید.")
        return

    if message.text.startswith("http"):
        if "instagram" in message.text:
            res = requests.get(f"https://pouriam.top/eyephp/instagram?url={message.text}").json()
            for link in res.get("links", []):
                bot.send_message(user_id, link)
        elif "spotify" in message.text:
            res = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={message.text}").json()
            if res.get("ok"):
                bot.send_audio(user_id, res["data"]["track"]["download_url"])
        elif "pin" in message.text:
            res = requests.get(f"https://haji.s2025h.space/pin/?url={message.text}&client_key=keyvip").json()
            if res.get("status"):
                bot.send_photo(user_id, res["download_url"])
        else:
            bot.send_message(user_id, "لینک معتبر نیست.")
    elif message.text.startswith("ساخت عکس "):
        txt = message.text.replace("ساخت عکس ", "")
        res = requests.get(f"https://v3.api-free.ir/image/?text={txt}").json()
        if res.get("ok"):
            bot.send_photo(user_id, res["result"])
    else:
        fallback_response = get_ai_response(message.text)
        bot.send_message(user_id, fallback_response)

# وب‌سرویس هوش مصنوعی
def get_ai_response(text):
    urls = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}",
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=5).text
            if res:
                return res
        except:
            continue
    return "❌ متاسفم، پاسخ دریافت نشد."

# مسیر وب‌هوک
@app.route("/", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        update = telebot.types.Update.de_json(request.data.decode("utf-8"))
        bot.process_new_updates([update])
    return "ok", 200

# شروع برنامه
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0"
