import os
import time
import threading
import requests
from flask import Flask, request
import telebot
from telebot import types
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

# ====== تنظیمات اولیه =======
TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
CHANNEL_USERNAME = "@netgoris"
ADMIN_ID = 5637609683
MONGO_PASS = "RIHPhDJPhd9aNJvC"
MONGO_URL = f"mongodb+srv://mohsenfeizi1386:{MONGO_PASS}@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority"

WEBHOOK_URL = "https://chatgpt-qg71.onrender.com/" + TOKEN

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ====== اتصال به دیتابیس =======
try:
    mongo_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db = mongo_client['telegram_bot']
    users_col = db['users']
    banned_col = db['banned']
except ServerSelectionTimeoutError:
    print("⚠️ اتصال به دیتابیس برقرار نشد!")

# ====== مدیریت اسپم =======
user_message_times = {}

def can_send(user_id):
    now = time.time()
    times = user_message_times.get(user_id, [])
    # پاک کردن پیام های قدیمی تر از ۲ دقیقه
    times = [t for t in times if now - t < 120]
    if len(times) >= 4:
        return False
    times.append(now)
    user_message_times[user_id] = times
    return True

# ====== بررسی جوین اجباری =======
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status != 'left' and member.status != 'kicked'
    except Exception as e:
        print(f"Error checking membership: {e}")
        return False

# ====== متن ها =======
WELCOME_TEXT = """سلام دوست عزیز!
برای استفاده از ربات، ابتدا باید در کانال زیر عضو شوید."""
WELCOME_BTN_TEXT = "کانال ما"
CONFIRM_BTN_TEXT = "تایید عضویت"

HELP_TEXT = """
📌 راهنمای استفاده از ربات:

- ابتدا باید عضو کانال شوید.
- سپس دکمه تایید عضویت را بزنید.
- برای دریافت پاسخ هوش مصنوعی کافیست پیام خود را ارسال کنید.
- قوانین:
  1. رعایت ادب و احترام الزامی است.
  2. ارسال پیام‌های تبلیغاتی ممنوع است.
  3. از ارسال لینک‌های نامربوط خودداری کنید.
  
برای سوالات بیشتر با پشتیبانی در ارتباط باشید.
"""

# ====== صفحه راهنما =======
def help_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("بازگشت به صفحه اصلی", callback_data="help_back"))
    return kb

# ====== صفحه اصلی =======
def main_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("راهنما", callback_data="help"))
    return kb

# ====== دکمه‌های جوین اجباری =======
def join_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(WELCOME_BTN_TEXT, url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"))
    kb.add(types.InlineKeyboardButton(CONFIRM_BTN_TEXT, callback_data="check_join"))
    return kb

# ====== کنترل بن =======
def is_banned(user_id):
    return banned_col.find_one({"user_id": user_id}) is not None

def ban_user(user_id):
    banned_col.update_one({"user_id": user_id}, {"$set": {"banned": True}}, upsert=True)

def unban_user(user_id):
    banned_col.delete_one({"user_id": user_id})

# ====== وب هوک =======
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

# ====== دستور استارت =======
@bot.message_handler(commands=["start"])
def start_handler(message):
    user_id = message.from_user.id

    # چک بن
    if is_banned(user_id):
        bot.send_message(user_id, "شما توسط مدیر بن شده‌اید و دسترسی ندارید.")
        return

    # ذخیره کاربر
    if users_col.find_one({"user_id": user_id}) is None:
        users_col.insert_one({"user_id": user_id, "username": message.from_user.username or "", "first_name": message.from_user.first_name or "", "joined": False})

        # اطلاع به ادمین از کاربر جدید
        bot.send_message(ADMIN_ID, f"کاربر جدید:\n{user_id}\n@{message.from_user.username}")

    # ارسال پیام جوین اجباری
    bot.send_message(user_id, WELCOME_TEXT, reply_markup=join_keyboard())

# ====== هندل دکمه های inline =======
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id

    if call.data == "check_join":
        if is_user_joined(user_id):
            # به روزرسانی وضعیت عضو شدن در دیتابیس
            users_col.update_one({"user_id": user_id}, {"$set": {"joined": True}})

            # حذف پیام جوین اجباری
            bot.delete_message(user_id, call.message.message_id)

            # پیام خوش آمد و دکمه راهنما
            bot.send_message(user_id, "🎉 تبریک! شما عضو کانال شدید و می‌توانید از ربات استفاده کنید.", reply_markup=main_keyboard())
        else:
            bot.answer_callback_query(call.id, "❌ شما هنوز عضو کانال نشده‌اید!", show_alert=True)

    elif call.data == "help":
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=HELP_TEXT, reply_markup=help_keyboard())

    elif call.data == "help_back":
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text="🎉 به صفحه اصلی خوش آمدید.", reply_markup=main_keyboard())

# ====== تابع پاسخ با fallback 3 وب‌سرویس هوش مصنوعی =======
AI_SERVICES = [
    "https://starsshoptl.ir/Ai/index.php?text=",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text=",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text=",
]

def ask_ai(text):
    for url in AI_SERVICES:
        try:
            r = requests.get(url + requests.utils.quote(text), timeout=8)
            if r.status_code == 200:
                res = r.json()
                # اگر خروجی مناسب نبود از بعدی امتحان کن
                if "result" in res:
                    return res["result"]
        except Exception as e:
            print(f"AI service error: {e}")
    return None

# ====== شناسایی لینک ها و دانلودر =======
import re

def detect_and_process_links(text):
    # نمونه regex ساده برای اینستا، اسپاتیفای و پینترست
    instagram_pattern = r"(https?://(www\.)?instagram\.com[^\s]+)"
    spotify_pattern = r"(https?://open\.spotify\.com[^\s]+)"
    pinterest_pattern = r"(https?://(www\.)?pinterest\.[^\s]+)"

    if re.search(instagram_pattern, text):
        return process_instagram(text)
    elif re.search(spotify_pattern, text):
        return process_spotify(text)
    elif re.search(pinterest_pattern, text):
        return process_pinterest(text)
    else:
        return None

def process_instagram(text):
    try:
        # فقط لینک را استخراج کن
        link = re.search(r"https?://[^\s]+", text).group(0)
        api_url = f"https://pouriam.top/eyephp/instagram?url={link}"
        r = requests.get(api_url, timeout=10)
        data = r.json()
        if "links" in data and len(data["links"]) > 0:
            # فقط اولین لینک رو بفرست
            return data["links"][0]
        return "خطا در دریافت ویدیو اینستاگرام."
    except Exception as e:
        return "خطا در پردازش لینک اینستاگرام."

def process_spotify(text):
    try:
        link = re.search(r"https?://[^\s]+", text).group(0)
        api_url = f"http://api.cactus-dev.ir/spotify.php?url={link}"
        r = requests.get(api_url, timeout=10)
        data = r.json()
        if data.get("ok") and "data" in data:
            return data["data"]["track"]["download_url"]
        return "خطا در دریافت فایل اسپاتیفای."
    except Exception as e:
        return "خطا در پردازش لینک اسپاتیفای."

def process_pinterest(text):
    try:
        link = re.search(r"https?://[^\s]+", text).group(0)
        api_url = f"https://haji.s2025h.space/pin/?url={link}&client_key=keyvip"
        r = requests.get(api_url, timeout=10)
        data = r.json()
        if data.get("status"):
            return data["download_url"]
        return "خطا در دریافت عکس پینترست."
    except Exception as e:
        return "خطا در پردازش لینک پینترست."

# ====== پاسخ به پیام کاربر =======
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.from_user.id

    if is_banned(user_id):
        bot.send_message(user_id, "شما توسط مدیر بن شده‌اید و دسترسی ندارید.")
        return

    if not can_send(user_id):
        bot.send_message(user_id, "⚠️ شما زیاد پیام می‌فرستید لطفا کمی صبر کنید.")
        return

    # چک جوین اجباری
    user_data = users_col.find_one({"user_id": user_id})
    if not user_data or not user_data.get("joined", False):
        bot.send_message(user_id, "❌ لطفا ابتدا عضو کانال شوید و تایید کنید.", reply_markup=join_keyboard())
        return

    text = message.text or ""

    # اگر لینک دانلود بود
    link_result = detect_and_process_links(text)
    if link_result:
        bot.send_message(user_id, link_result)
        return

    # اگر متن عادی بود، از هوش مصنوعی بپرس
    ai_answer = ask_ai(text)
    if ai_answer:
        bot.send_message(user_id, ai_answer)
    else:
        bot.send_message(user_id, "❌ مشکلی در پاسخ‌دهی رخ داد. لطفا بعدا تلاش کنید.")

# ====== اجرای ربات و وب هوک =======
def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    res = requests.get(url)
    if res.status_code == 200:
        print("Webhook set successfully.")
    else:
        print(f"Failed to set webhook: {res.text}")

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
