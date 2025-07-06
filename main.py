import telebot
from flask import Flask, request
import requests
from pymongo import MongoClient

TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
CHANNEL_ID = "@netgoris"
OWNER_ID = 5637609683
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)
client = MongoClient(MONGO_URI)
db = client["bot"]
users = db["users"]

# وب‌سرویس‌های چت
AI_SERVICES = [
    "https://starsshoptl.ir/Ai/index.php?text={}",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text={}",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text={}"
]

# لینک‌های دانلود
INSTAGRAM_API = "https://pouriam.top/eyephp/instagram?url="
SPOTIFY_API = "http://api.cactus-dev.ir/spotify.php?url="
PINTEREST_API = "https://haji.s2025h.space/pin/?url={}&client_key=keyvip"
IMAGE_API = "https://v3.api-free.ir/image/?text={}"

# دکمه‌های شیشه‌ای
def join_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("💠 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.replace('@','')}"))
    markup.add(telebot.types.InlineKeyboardButton("✅ تایید عضویت", callback_data="check_join"))
    return markup

def menu_markup():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 راهنما", "💬 پشتیبانی")
    return markup

# چک عضویت
def is_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# هندل استارت
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    if not is_joined(user_id):
        bot.send_message(user_id, "👋 برای استفاده از ربات لطفاً ابتدا عضو کانال شوید:", reply_markup=join_markup())
    else:
        users.update_one({"_id": user_id}, {"$set": {"active": True}}, upsert=True)
        bot.send_message(user_id, "🎉 خوش آمدید! از ربات استفاده کنید.", reply_markup=menu_markup())
        if not users.find_one({"_id": user_id, "notified": True}):
            bot.send_message(OWNER_ID, f"🙋‍♂️ کاربر جدید استارت زد: <code>{user_id}</code>")
            users.update_one({"_id": user_id}, {"$set": {"notified": True}})

# دکمه‌های شیشه‌ای
@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(call):
    if is_joined(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.from_user.id, "✅ عضویت تایید شد.", reply_markup=menu_markup())
    else:
        bot.answer_callback_query(call.id, "لطفاً ابتدا عضو کانال شوید.")

# راهنما
@bot.message_handler(func=lambda m: m.text == "📋 راهنما")
def guide(message):
    text = """
📖 <b>راهنمای ربات:</b>

✅ عضویت در کانال الزامیست.
✅ ارسال لینک اینستاگرام، اسپاتیفای، پینترست یا متن برای پاسخ هوش مصنوعی مجاز است.
✅ رعایت ادب در چت الزامیست.
🚫 اسپم بیش از حد باعث بلاک می‌شود.

💡 ربات همیشه در خدمت شماست!
"""
    bot.send_message(message.chat.id, text, reply_markup=menu_markup())

# پشتیبانی
@bot.message_handler(func=lambda m: m.text == "💬 پشتیبانی")
def support(message):
    bot.send_message(message.chat.id, "📩 لطفاً پیام خود را ارسال کنید، منتظر پاسخ باشید.", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, forward_support)

def forward_support(message):
    bot.forward_message(OWNER_ID, message.chat.id, message.message_id)
    bot.send_message(message.chat.id, "✅ پیام ارسال شد، منتظر پاسخ بمانید.")

@bot.message_handler(func=lambda m: True, content_types=["text"])
def chat_handler(message):
    if not is_joined(message.from_user.id):
        bot.send_message(message.chat.id, "🔒 لطفاً ابتدا عضو کانال شوید.", reply_markup=join_markup())
        return

    text = message.text

    if "instagram.com" in text:
        res = requests.get(INSTAGRAM_API + text).json()
        for link in res.get("links", []):
            bot.send_message(message.chat.id, link)
    elif "spotify.com" in text:
        res = requests.get(SPOTIFY_API + text).json()
        bot.send_message(message.chat.id, res.get("data", {}).get("download_url", "⛔ خطا در دریافت فایل"))
    elif "pin.it" in text or "pinterest.com" in text:
        res = requests.get(PINTEREST_API.format(text)).json()
        bot.send_message(message.chat.id, res.get("download_url", "⛔ خطا در دریافت تصویر"))
    elif text.startswith("ساخت عکس "):
        word = text.replace("ساخت عکس ", "")
        res = requests.get(IMAGE_API.format(word)).json()
        bot.send_message(message.chat.id, res.get("result", "⛔ خطا در ساخت عکس"))
    else:
        for url in AI_SERVICES:
            res = requests.get(url.format(text)).text
            if "Hey there" in res or res.strip():
                bot.send_message(message.chat.id, res)
                break
        else:
            bot.send_message(message.chat.id, "⛔ پاسخ از سرورها دریافت نشد.")

# دریافت پیام پشتیبانی مدیر
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID, content_types=["reply"])
def reply_support(message):
    if message.reply_to_message.forward_from:
        bot.send_message(message.reply_to_message.forward_from.id, message.text)

# وب‌هوک
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK"

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://chatgpt-qg71.onrender.com/{TOKEN}")
    app.run(host="0.0.0.0", port=5000)
