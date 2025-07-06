import telebot
from flask import Flask, request
import requests
import time
from pymongo import MongoClient

# اطلاعات ربات
BOT_TOKEN = "7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE"
CHANNEL_USERNAME = "@netgoris"
ADMIN_ID = 5637609683
MONGO_URL = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# دیتابیس
client = MongoClient(MONGO_URL)
db = client["TellGPT"]
users = db["users"]
ban = db["ban"]
spam_db = {}

# ضده اسپم
SPAM_LIMIT = 4
SPAM_TIME = 120  # ثانیه

# پیام خوش‌آمد و راهنما
def welcome_message():
    return ("سلام خوش اومدی 😍🌟\n"
            "برای استفاده از ربات، لطفاً عضو کانال ما شو:\n"
            f"{CHANNEL_USERNAME}\n"
            "بعد دکمه تایید رو بزن")

def help_text():
    return ("📌 راهنمای ربات TellGPT:\n"
            "- ارسال متن برای چت‌بات هوش مصنوعی\n"
            "- ارسال لینک اینستا، اسپاتیفای، پینترست برای دانلود\n"
            "- دکمه پشتیبانی برای ارتباط با ادمین\n"
            "⚠️ قوانین:\n"
            "- ارسال اسپم = محدودیت موقت\n"
            "- رعایت ادب در پیام‌ها الزامیست")

# چک عضویت
def is_member(user_id):
    try:
        res = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return res.status in ["member", "administrator", "creator"]
    except:
        return False

# ضد اسپم
def check_spam(user_id):
    now = time.time()
    if user_id not in spam_db:
        spam_db[user_id] = []
    spam_db[user_id] = [t for t in spam_db[user_id] if now - t < SPAM_TIME]
    spam_db[user_id].append(now)
    return len(spam_db[user_id]) > SPAM_LIMIT

# هندل استارت
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    if ban.find_one({"user_id": user_id}):
        return

    if not is_member(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"))
        markup.add(telebot.types.InlineKeyboardButton("✅ عضویت انجام شد", callback_data="check_join"))
        bot.send_message(user_id, welcome_message(), reply_markup=markup)
    else:
        if not users.find_one({"user_id": user_id}):
            users.insert_one({"user_id": user_id})
            bot.send_message(ADMIN_ID, f"کاربر جدید استارت زد: [{user_id}](tg://user?id={user_id})", parse_mode="Markdown")
        send_main_menu(user_id)

# دکمه تایید عضویت
@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(c):
    if is_member(c.from_user.id):
        bot.delete_message(c.message.chat.id, c.message.message_id)
        send_main_menu(c.from_user.id)
    else:
        bot.answer_callback_query(c.id, "اول عضو شو!", show_alert=True)

# ارسال منو
def send_main_menu(chat_id):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📚 راهنما", "💬 پشتیبانی")
    bot.send_message(chat_id, "✅ خوش اومدی، می‌تونی پیام بدی یا از منو استفاده کنی.", reply_markup=markup)

# هندل پیام‌ها
@bot.message_handler(func=lambda m: True)
def all_msgs(message):
    user_id = message.from_user.id
    text = message.text

    if ban.find_one({"user_id": user_id}):
        return
    if not is_member(user_id):
        return start(message)

    if check_spam(user_id):
        bot.send_message(user_id, "🚫 لطفاً اسپم نده، کمی صبر کن.")
        return

    if text == "📚 راهنما":
        bot.send_message(user_id, help_text())
    elif text == "💬 پشتیبانی":
        msg = bot.send_message(user_id, "پیامت رو بنویس، ادمین جواب میده.")
        bot.register_next_step_handler(msg, support_handler)
    elif "instagram.com" in text:
        send_insta(text, user_id)
    elif "spotify.com" in text:
        send_spotify(text, user_id)
    elif "pin.it" in text or "pinterest.com" in text:
        send_pinterest(text, user_id)
    else:
        ai_chat(text, user_id)

# پشتیبانی
def support_handler(message):
    bot.send_message(ADMIN_ID, f"پیام جدید از [{message.from_user.id}](tg://user?id={message.from_user.id}):\n{message.text}", parse_mode="Markdown")

# وب‌سرویس‌های مختلف
def ai_chat(text, user_id):
    urls = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=10).text
            if res.strip():
                bot.send_message(user_id, res)
                return
        except:
            continue
    bot.send_message(user_id, "❌ مشکلی در پاسخ‌دهی بود.")

def send_insta(link, user_id):
    try:
        res = requests.get(f"https://pouriam.top/eyephp/instagram?url={link}").json()
        for media in res.get("links", []):
            if ".mp4" in media:
                bot.send_video(user_id, media)
            elif ".jpg" in media or ".png" in media:
                bot.send_photo(user_id, media)
    except:
        bot.send_message(user_id, "⛔ خطا در دانلود اینستاگرام")

def send_spotify(link, user_id):
    try:
        res = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={link}").json()
        if res.get("ok"):
            bot.send_audio(user_id, res["data"]["track"]["download_url"])
    except:
        bot.send_message(user_id, "⛔ خطا در دانلود اسپاتیفای")

def send_pinterest(link, user_id):
    try:
        res = requests.get(f"https://haji.s2025h.space/pin/?url={link}&client_key=keyvip").json()
        if res.get("status"):
            bot.send_photo(user_id, res["download_url"])
    except:
        bot.send_message(user_id, "⛔ خطا در دانلود پینترست")

# وب‌هوک
@app.route("/", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "OK"

# ست وب‌هوک
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=5000)
