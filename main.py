import telebot
from telebot import types
from flask import Flask, request
import os
import requests
import time
from pymongo import MongoClient

# ------ تنظیمات ------
TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com/" + TOKEN
PORT = int(os.environ.get('PORT', 1000))

# ------ اتصال ها ------
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
client = MongoClient(MONGO_URI)
db = client.bot_db
users = db.users
spams = {}

# ------ ضداسپم ------
SPAM_LIMIT = 4
SPAM_TIMEOUT = 120  # ثانیه

# ------ چک عضویت ------
def is_member(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "creator", "administrator"]
    except:
        return False

# ------ مدیریت ضداسپم ------
def check_spam(user_id):
    now = time.time()
    if user_id not in spams:
        spams[user_id] = []
    spams[user_id] = [t for t in spams[user_id] if now - t < SPAM_TIMEOUT]
    spams[user_id].append(now)
    return len(spams[user_id]) > SPAM_LIMIT

# ------ هندل استارت ------
@bot.message_handler(commands=["start"])
def start_message(message):
    user_id = message.from_user.id
    if not is_member(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"))
        markup.add(types.InlineKeyboardButton("✅ عضویت انجام شد", callback_data="check"))
        bot.send_message(user_id, "🚫 برای استفاده از ربات، ابتدا عضو کانال ما شوید:", reply_markup=markup)
        return
    
    if not users.find_one({"user_id": user_id}):
        users.insert_one({"user_id": user_id})
        bot.send_message(OWNER_ID, f"🙋‍♂️ کاربر جدید استارت زد:\n[{message.from_user.first_name}](tg://user?id={user_id})", parse_mode="Markdown")

    main_panel(message)

# ------ چک عضویت دکمه ------
@bot.callback_query_handler(func=lambda call: call.data == "check")
def check_join(call):
    if is_member(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ عضویت تایید شد، خوش آمدید!", reply_markup=help_markup())
    else:
        bot.answer_callback_query(call.id, "🚫 هنوز عضو کانال نیستید.")

# ------ صفحه اصلی ------
def main_panel(message):
    markup = help_markup()
    bot.send_message(message.chat.id, "🎉 به ربات خوش آمدید!\nاز امکانات ما لذت ببرید.", reply_markup=markup)

# ------ کیبورد راهنما ------
def help_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📖 راهنما", "🎧 پشتیبانی")
    return markup

# ------ راهنما ------
@bot.message_handler(func=lambda m: m.text == "📖 راهنما")
def help_message(message):
    text = """
📚 راهنمای استفاده از ربات:

🔗 ربات لینک‌های زیر را پشتیبانی می‌کند:
✅ اینستاگرام
✅ اسپاتیفای
✅ پینترست
✅ تولید عکس با متن
✅ چت با هوش مصنوعی

⚠️ قوانین:
- ارسال اسپم = سکوت ۲ دقیقه‌ای
- عضویت در کانال الزامی است
- سواستفاده = مسدودی دائم

برای برگشت، دکمه 🔙 را بزنید.
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 برگشت")
    bot.send_message(message.chat.id, text, reply_markup=markup)

# ------ برگشت از راهنما ------
@bot.message_handler(func=lambda m: m.text == "🔙 برگشت")
def back_message(message):
    main_panel(message)

# ------ پشتیبانی ------
support_mode = []

@bot.message_handler(func=lambda m: m.text == "🎧 پشتیبانی")
def support_start(message):
    support_mode.append(message.from_user.id)
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "📝 لطفاً سوال خود را ارسال کنید. برای خروج 'لغو' را ارسال کنید.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.from_user.id in support_mode)
def handle_support(message):
    if message.text.lower() == "لغو":
        support_mode.remove(message.from_user.id)
        bot.send_message(message.chat.id, "✅ از بخش پشتیبانی خارج شدید.", reply_markup=help_markup())
    else:
        bot.send_message(OWNER_ID, f"💬 پیام جدید از [{message.from_user.first_name}](tg://user?id={message.from_user.id}):\n{message.text}", parse_mode="Markdown", reply_markup=support_reply_markup(message.from_user.id))
        support_mode.remove(message.from_user.id)
        bot.send_message(message.chat.id, "✅ پیام شما ارسال شد.", reply_markup=help_markup())

def support_reply_markup(user_id):
    markup = types.ForceReply(selective=True)
    markup.input_field_placeholder = str(user_id)
    return markup

# ------ جواب به کاربر توسط ادمین ------
@bot.message_handler(func=lambda m: m.reply_to_message and m.reply_to_message.from_user.id == OWNER_ID)
def admin_reply(message):
    try:
        user_id = int(message.reply_to_message.text.split()[-1])
        bot.send_message(user_id, f"💬 پاسخ پشتیبانی:\n{message.text}")
        bot.send_message(OWNER_ID, "✅ پاسخ ارسال شد.")
    except:
        pass

# ------ تشخیص لینک و اجرا ------
@bot.message_handler(func=lambda m: True, content_types=["text"])
def link_handler(message):
    user_id = message.from_user.id

    if check_spam(user_id):
        bot.send_message(user_id, "⛔️ لطفاً تا ۲ دقیقه دیگر پیام ارسال نکنید.")
        return

    text = message.text

    if "instagram.com" in text:
        insta_downloader(message, text)
    elif "spotify.com" in text:
        spotify_downloader(message, text)
    elif "pin.it" in text or "pinterest" in text:
        pinterest_downloader(message, text)
    elif text.startswith("/image "):
        generate_image(message, text.replace("/image ", ""))
    elif text.startswith("/ai "):
        ai_chat(message, text.replace("/ai ", ""))
    else:
        bot.send_message(message.chat.id, "❌ لینک یا دستور ناشناس.")

# ------ اینستاگرام ------
def insta_downloader(message, url):
    try:
        res = requests.get(f"https://pouriam.top/eyephp/instagram?url={url}").json()
        for link in res["links"]:
            bot.send_chat_action(message.chat.id, "upload_video")
            bot.send_video(message.chat.id, link) if ".mp4" in link else bot.send_photo(message.chat.id, link)
    except:
        bot.send_message(message.chat.id, "⛔️ خطا در دریافت از اینستاگرام.")

# ------ اسپاتیفای ------
def spotify_downloader(message, url):
    try:
        res = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={url}").json()
        bot.send_audio(message.chat.id, res["data"]["download_url"], title=res["data"]["track"]["name"], performer=res["data"]["track"]["artists"])
    except:
        bot.send_message(message.chat.id, "⛔️ خطا در دریافت اسپاتیفای.")

# ------ پینترست ------
def pinterest_downloader(message, url):
    try:
        res = requests.get(f"https://haji.s2025h.space/pin/?url={url}&client_key=keyvip").json()
        bot.send_photo(message.chat.id, res["download_url"])
    except:
        bot.send_message(message.chat.id, "⛔️ خطا در دریافت پینترست.")

# ------ تولید عکس ------
def generate_image(message, text):
    try:
        res = requests.get(f"https://v3.api-free.ir/image/?text={text}").json()
        bot.send_photo(message.chat.id, res["result"])
    except:
        bot.send_message(message.chat.id, "⛔️ خطا در تولید تصویر.")

# ------ چت AI ------
def ai_chat(message, text):
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
    bot.send_message(message.chat.id, "⛔️ خطا در دریافت پاسخ AI.")

# ------ صفحه اصلی دامنه ------
@app.route("/", methods=["GET"])
def home():
    return "ربات آنلاین است ✅", 200

# ------ وبهوک ------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok", 200

# ------ اجرا ------
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=PORT)
