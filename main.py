import telebot
from flask import Flask, request
import requests
from pymongo import MongoClient

# === تنظیمات ربات ===
BOT_TOKEN = "7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE"
CHANNEL_USERNAME = "@netgoris"  # آیدی کانال با @
ADMIN_ID = 5637609683
MONGO_URL = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
client = MongoClient(MONGO_URL)
db = client["TellGPT"]
users = db["users"]

# === ضد اسپم ===
spam_count = {}

# بررسی عضویت در کانال
def is_member(user_id):
    try:
        res = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return res.status in ["member", "administrator", "creator"]
    except:
        return False

# دکمه های کیبورد پایین
def main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💡 راهنما", "🛠 پشتیبانی")
    return markup

# ضد اسپم شمارش
def check_spam(user_id):
    count = spam_count.get(user_id, 0) + 1
    spam_count[user_id] = count
    if count >= 4:
        return True
    return False

# وب‌سرویس چت GPT
def ask_ai(text):
    urls = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=10)
            if r.ok and len(r.text.strip()) > 2:
                return r.text.strip()
        except:
            continue
    return "❌ خطا در پاسخ هوش مصنوعی!"

# استارت
@bot.message_handler(commands=["start"])
def start_handler(message):
    user = users.find_one({"user_id": message.chat.id})
    if not user:
        users.insert_one({"user_id": message.chat.id})
        bot.send_message(ADMIN_ID, f"💡 کاربر جدید استارت کرد:\n\n👤 {message.from_user.first_name}\n🆔 {message.chat.id}")

    if not is_member(message.chat.id):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("عضویت در کانال 📢", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"))
        bot.send_message(message.chat.id, "👋 برای استفاده از ربات ابتدا عضو کانال شوید:", reply_markup=markup)
        return

    bot.send_message(message.chat.id, "✅ خوش آمدید! از دکمه‌های پایین استفاده کنید یا پیام ارسال کنید.", reply_markup=main_keyboard())

# راهنما
@bot.message_handler(func=lambda m: m.text == "💡 راهنما")
def help_handler(message):
    help_text = """
📌 راهنمای ربات:

✅ ارسال پیام → دریافت پاسخ هوش مصنوعی
✅ ارسال لینک‌های اینستاگرام، پینترست، اسپاتیفای → دریافت دانلود مستقیم

💡 لینک‌های پشتیبانی:
🟢 اینستاگرام: https://pouriam.top/eyephp/instagram?url=
🟢 اسپاتیفای: http://api.cactus-dev.ir/spotify.php?url=
🟢 پینترست: https://haji.s2025h.space/pin/?url=...&client_key=keyvip
    """
    bot.send_message(message.chat.id, help_text)

# پشتیبانی
support_sessions = {}

@bot.message_handler(func=lambda m: m.text == "🛠 پشتیبانی")
def support_start(message):
    support_sessions[message.chat.id] = True
    markup = telebot.types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "🔧 لطفاً پیام خود را ارسال کنید. برای خروج 'لغو' را ارسال کنید.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.chat.id in support_sessions and m.text.lower() != "لغو")
def support_msg(message):
    bot.send_message(ADMIN_ID, f"📩 پیام پشتیبانی از {message.chat.id}:\n{message.text}")
    bot.send_message(message.chat.id, "✅ پیام شما ارسال شد.")
    support_sessions.pop(message.chat.id, None)
    bot.send_message(message.chat.id, "✅ بازگشت به منو", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.chat.id in support_sessions and m.text.lower() == "لغو")
def cancel_support(message):
    support_sessions.pop(message.chat.id, None)
    bot.send_message(message.chat.id, "❌ پشتیبانی لغو شد.", reply_markup=main_keyboard())

# پیام‌ها
@bot.message_handler(func=lambda m: True)
def ai_handler(message):
    if not is_member(message.chat.id):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("عضویت در کانال 📢", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"))
        bot.send_message(message.chat.id, "❗️ابتدا عضو کانال شوید.", reply_markup=markup)
        return

    if check_spam(message.chat.id):
        bot.send_message(message.chat.id, "🚫 لطفاً کمی صبر کنید، ضداسپم فعال شد.")
        return

    text = message.text

    if "instagram.com" in text:
        res = requests.get(f"https://pouriam.top/eyephp/instagram?url={text}").json()
        for link in res.get("links", []):
            bot.send_message(message.chat.id, link)
    elif "spotify.com" in text:
        res = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={text}").json()
        if res.get("ok"):
            bot.send_audio(message.chat.id, res["data"]["download_url"])
    elif "pin.it" in text or "pinterest" in text:
        res = requests.get(f"https://haji.s2025h.space/pin/?url={text}&client_key=keyvip").json()
        if res.get("status"):
            bot.send_photo(message.chat.id, res["download_url"])
    else:
        answer = ask_ai(text)
        bot.send_message(message.chat.id, answer)

# وب‌هوک فلask
@app.route('/', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok"

# ست وب هوک
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

# اجرا
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=5000)
