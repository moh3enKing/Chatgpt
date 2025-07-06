import telebot
from telebot import types
from flask import Flask, request
import requests
import os
import time
from pymongo import MongoClient

# ------------ تنظیمات ------------
TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = f"https://chatgpt-qg71.onrender.com/{TOKEN}"
PORT = int(os.environ.get("PORT", 1000))

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

client = MongoClient(MONGO_URI)
db = client.bot_db
users = db.users
spam_data = {}

SPAM_LIMIT = 4
SPAM_TIMEOUT = 120  # ثانیه

support_mode = []

# ------------ چک عضویت ------------
def is_member(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ["member", "administrator", "creator"]
    except:
        return False

# ------------ ضد اسپم ------------
def check_spam(user_id):
    now = time.time()
    if user_id not in spam_data:
        spam_data[user_id] = []
    spam_data[user_id] = [t for t in spam_data[user_id] if now - t < SPAM_TIMEOUT]
    spam_data[user_id].append(now)
    return len(spam_data[user_id]) > SPAM_LIMIT

# ------------ استارت ------------
@bot.message_handler(commands=["start"])
def start(message):
    if not is_member(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"))
        markup.add(types.InlineKeyboardButton("✅ عضو شدم", callback_data="check"))
        bot.send_message(message.chat.id, "🚫 لطفاً ابتدا در کانال عضو شوید:", reply_markup=markup)
        return

    if not users.find_one({"user_id": message.from_user.id}):
        users.insert_one({"user_id": message.from_user.id})
        bot.send_message(OWNER_ID, f"🎉 کاربر جدید:\n[{message.from_user.first_name}](tg://user?id={message.from_user.id})", parse_mode="Markdown")

    show_panel(message.chat.id)

# ------------ چک عضویت دکمه ------------
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check_join(call):
    if is_member(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ عضویت تایید شد، خوش آمدید!", reply_markup=main_markup())
    else:
        bot.answer_callback_query(call.id, "🚫 هنوز عضو نیستید.")

# ------------ منو اصلی ------------
def show_panel(chat_id):
    bot.send_message(chat_id, "به ربات خوش آمدید 🎉", reply_markup=main_markup())

def main_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📖 راهنما", "🎧 پشتیبانی")
    return markup

# ------------ راهنما ------------
@bot.message_handler(func=lambda m: m.text == "📖 راهنما")
def show_help(message):
    txt = """
📚 راهنمای ربات:

✅ اینستاگرام: دانلود عکس و ویدیو
✅ اسپاتیفای: دانلود موزیک
✅ پینترست: دانلود عکس
✅ چت هوش مصنوعی
✅ تولید عکس با متن

⚠️ قوانین:
- ارسال ۴ پیام پشت سر هم = سکوت ۲ دقیقه‌ای
- عضو کانال باشید
- سواستفاده = بن دائمی
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 برگشت")
    bot.send_message(message.chat.id, txt, reply_markup=markup)

# ------------ برگشت ------------
@bot.message_handler(func=lambda m: m.text == "🔙 برگشت")
def back(message):
    show_panel(message.chat.id)

# ------------ پشتیبانی ------------
@bot.message_handler(func=lambda m: m.text == "🎧 پشتیبانی")
def support(message):
    support_mode.append(message.from_user.id)
    bot.send_message(message.chat.id, "✍️ پیام خود را ارسال کنید. برای خروج 'لغو' بزنید.", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: m.from_user.id in support_mode)
def handle_support(message):
    if message.text.lower() == "لغو":
        support_mode.remove(message.from_user.id)
        bot.send_message(message.chat.id, "❌ پشتیبانی لغو شد.", reply_markup=main_markup())
    else:
        bot.send_message(OWNER_ID, f"📩 پیام جدید از [{message.from_user.first_name}](tg://user?id={message.from_user.id}):\n{message.text}", parse_mode="Markdown", reply_markup=types.ForceReply(selective=True))
        support_mode.remove(message.from_user.id)
        bot.send_message(message.chat.id, "✅ پیام شما ارسال شد.", reply_markup=main_markup())

# ------------ پاسخ مدیر به کاربر ------------
@bot.message_handler(func=lambda m: m.reply_to_message and m.reply_to_message.from_user.id == OWNER_ID)
def admin_reply(message):
    try:
        target_id = int(message.reply_to_message.text.split()[-1])
        bot.send_message(target_id, f"💬 پاسخ پشتیبانی:\n{message.text}")
        bot.send_message(OWNER_ID, "✅ پاسخ ارسال شد.")
    except:
        pass

# ------------ پردازش پیام‌ها ------------
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    if check_spam(message.from_user.id):
        bot.send_message(message.chat.id, "⛔️ لطفاً تا ۲ دقیقه دیگر صبر کنید.")
        return

    text = message.text
    if "instagram.com" in text:
        download_instagram(message, text)
    elif "spotify.com" in text:
        download_spotify(message, text)
    elif "pinterest" in text or "pin.it" in text:
        download_pinterest(message, text)
    elif text.startswith("/image "):
        generate_image(message, text.replace("/image ", ""))
    elif text.startswith("/ai "):
        chat_ai(message, text.replace("/ai ", ""))
    else:
        bot.send_message(message.chat.id, "❌ لینک یا دستور نامعتبر.")

# ------------ اینستاگرام ------------
def download_instagram(message, url):
    try:
        res = requests.get(f"https://pouriam.top/eyephp/instagram?url={url}").json()
        for link in res["links"]:
            if link.endswith(".mp4"):
                bot.send_video(message.chat.id, link)
            else:
                bot.send_photo(message.chat.id, link)
    except:
        bot.send_message(message.chat.id, "⛔️ خطا در دانلود اینستاگرام.")

# ------------ اسپاتیفای ------------
def download_spotify(message, url):
    try:
        res = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={url}").json()
        bot.send_audio(message.chat.id, res["data"]["download_url"], title=res["data"]["track"]["name"], performer=res["data"]["track"]["artists"])
    except:
        bot.send_message(message.chat.id, "⛔️ خطا در دریافت موزیک.")

# ------------ پینترست ------------
def download_pinterest(message, url):
    try:
        res = requests.get(f"https://haji.s2025h.space/pin/?url={url}&client_key=keyvip").json()
        bot.send_photo(message.chat.id, res["download_url"])
    except:
        bot.send_message(message.chat.id, "⛔️ خطا در دریافت عکس.")

# ------------ تولید عکس ------------
def generate_image(message, text):
    try:
        res = requests.get(f"https://v3.api-free.ir/image/?text={text}").json()
        bot.send_photo(message.chat.id, res["result"])
    except:
        bot.send_message(message.chat.id, "⛔️ خطا در تولید عکس.")

# ------------ هوش مصنوعی ------------
def chat_ai(message, text):
    urls = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]
    for url in urls:
        try:
            res = requests.get(url).text
            if res:
                bot.send_message(message.chat.id, res)
                return
        except:
            continue
    bot.send_message(message.chat.id, "⛔️ خطا در دریافت پاسخ.")

# ------------ روت اصلی سایت ------------
@app.route("/", methods=["GET"])
def home():
    return "✅ ربات آنلاین است.", 200

# ------------ وبهوک ------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok", 200

# ------------ اجرا ------------
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=PORT)
