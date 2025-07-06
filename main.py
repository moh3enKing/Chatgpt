from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import requests
import time

# ======= تنظیمات اولیه =======
TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
CHANNEL_ID = "@netgoris"
ADMIN_ID = 5637609683
MONGO_PASS = "RIHPhDJPhd9aNJvC"
MONGO_LINK = f"mongodb+srv://mohsenfeizi1386:{MONGO_PASS}@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ======= حافظه موقتی ضد اسپم =======
user_message_times = {}

# ======= تابع بررسی جوین اجباری =======
def check_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status != "left"
    except Exception:
        return False

# ======= صفحه جوین اجباری =======
def send_join_forced(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_ID[1:]}"))
    keyboard.add(InlineKeyboardButton("تایید عضویت", callback_data="check_join"))
    bot.send_message(message.chat.id, "لطفا ابتدا عضو کانال شوید و سپس تایید را بزنید.", reply_markup=keyboard)

# ======= صفحه راهنما =======
def send_help(message):
    text = """
📌 *راهنمای استفاده از ربات:*

1️⃣ برای شروع از دکمه /start استفاده کنید.  
2️⃣ حتما عضو کانال باشید تا بتوانید از ربات استفاده کنید.  
3️⃣ لینک‌های اینستاگرام، اسپاتیفای، پینترست را ارسال کنید تا مستقیم دانلود شوند.  
4️⃣ مراقب قوانین ربات باشید و اسپم نکنید.  
5️⃣ اگر سوالی داشتید دکمه پشتیبانی را فشار دهید.

⚠️ *اخطارها و قوانین:*  
- ارسال پیام‌های بی‌ربط و اسپم منجر به مسدودیت می‌شود.  
- احترام به کاربران و ادمین‌ها الزامی است.

📩 هر سوال یا مشکل داشتید به ادمین پیام دهید: @King_Red1
"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="main_menu"))
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=keyboard)

# ======= صفحه منوی اصلی =======
def send_main_menu(message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("راهنما"), KeyboardButton("پشتیبانی"))
    bot.send_message(message.chat.id, "به منوی اصلی خوش آمدید.", reply_markup=keyboard)

# ======= کنترل دکمه‌های شیشه‌ای =======
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "check_join":
        joined = check_joined(call.from_user.id)
        if joined:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, "تشکر از عضویت شما 🎉")
            send_main_menu(call.message)
        else:
            bot.answer_callback_query(call.id, "شما هنوز عضو کانال نشده‌اید!")

    elif call.data == "main_menu":
        send_main_menu(call.message)

# ======= پیام استارت =======
@bot.message_handler(commands=["start"])
def start_handler(message):
    if not check_joined(message.from_user.id):
        send_join_forced(message)
    else:
        send_main_menu(message)

# ======= پیام‌های متنی =======
@bot.message_handler(func=lambda message: True)
def message_handler(message):
    # ضد اسپم: بیش از ۴ پیام در ۲ دقیقه ممنوع
    now = time.time()
    times = user_message_times.get(message.from_user.id, [])
    times = [t for t in times if now - t < 120]
    times.append(now)
    user_message_times[message.from_user.id] = times
    if len(times) > 4:
        bot.reply_to(message, "⛔ لطفا آرام‌تر پیام دهید، اسپم ممنوع است.")
        return

    text = message.text or ""
    # دکمه راهنما
    if text == "راهنما":
        send_help(message)
        return
    # دکمه پشتیبانی
    if text == "پشتیبانی":
        bot.send_message(message.chat.id, "برای ارسال پیام به پشتیبانی، لطفا پیام خود را بنویسید.")
        # اینجا باید حالت پشتیبانی را فعال کنید (کد مربوطه را بعدا اضافه کنید)
        return

    # تشخیص لینک و ارسال به وب‌سرویس‌های دانلودر یا هوش مصنوعی
    if "instagram.com" in text:
        # مثال استفاده از وب‌سرویس اینستا
        url = f"https://pouriam.top/eyephp/instagram?url={text}"
        try:
            res = requests.get(url).json()
            links = res.get("links")
            if links:
                for link in links:
                    bot.send_message(message.chat.id, link)
            else:
                bot.send_message(message.chat.id, "خطا در دریافت لینک اینستاگرام.")
        except Exception:
            bot.send_message(message.chat.id, "خطا در اتصال به سرویس اینستاگرام.")
        return
    elif "spotify.com" in text:
        url = f"http://api.cactus-dev.ir/spotify.php?url={text}"
        try:
            res = requests.get(url).json()
            mp3 = res["data"]["track"]["download_url"]
            bot.send_message(message.chat.id, mp3)
        except Exception:
            bot.send_message(message.chat.id, "خطا در اتصال به سرویس اسپاتیفای.")
        return
    elif "pin.it" in text or "pinterest.com" in text:
        url = f"https://haji.s2025h.space/pin/?url={text}&client_key=keyvip"
        try:
            res = requests.get(url).json()
            if res.get("status"):
                bot.send_message(message.chat.id, res["download_url"])
            else:
                bot.send_message(message.chat.id, "خطا در دریافت تصویر پینترست.")
        except Exception:
            bot.send_message(message.chat.id, "خطا در اتصال به سرویس پینترست.")
        return

    # fallback وب‌سرویس‌های هوش مصنوعی (اولین که جواب داد ارسال می‌شود)
    ai_urls = [
        "https://starsshoptl.ir/Ai/index.php?text=",
        "https://starsshoptl.ir/Ai/index.php?model=gpt&text=",
        "https://starsshoptl.ir/Ai/index.php?model=deepseek&text="
    ]
    response_sent = False
    for api in ai_urls:
        try:
            r = requests.get(api + text)
            if r.status_code == 200:
                resp = r.text.strip()
                if resp:
                    bot.send_message(message.chat.id, resp)
                    response_sent = True
                    break
        except Exception:
            continue
    if not response_sent:
        bot.send_message(message.chat.id, "متاسفانه پاسخ مناسبی دریافت نشد.")

# ======= وب‌هوک فلاسک =======
@app.route('/', methods=["POST"])
def webhook():
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK"

# ======= اجرای سرور =======
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
