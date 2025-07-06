import telebot
from flask import Flask, request
import requests
import re
import time

# تنظیمات
TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"
WEBHOOK_URL = f"https://chatgpt-qg71.onrender.com/{TOKEN}"

# لینک‌های هوش مصنوعی
AI_LINKS = [
    "https://starsshoptl.ir/Ai/index.php?text={}",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text={}",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text={}"
]

# اپ و بات
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)

# روت چک سایت
@app.route("/", methods=["GET"])
def index():
    return "✅ ربات فعال است.", 200

# دریافت آپدیت تلگرام
@app.route(f"/{TOKEN}", methods=["POST"])
def get_update():
    if request.headers.get("content-type") == "application/json":
        json_str = request.stream.read().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "ok", 200
    return "bad request", 403

# استارت
@bot.message_handler(commands=["start"])
def start(msg):
    if msg.chat.type != "private":
        return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📢 ورود به کانال", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"),
        telebot.types.InlineKeyboardButton("✅ عضو شدم", callback_data="check")
    )
    bot.send_message(msg.chat.id, f"سلام {msg.from_user.first_name} عزیز!\nلطفاً ابتدا عضو {CHANNEL_USERNAME} شو.", reply_markup=markup)
    bot.send_message(OWNER_ID, f"🟢 کاربر جدید:\nنام: {msg.from_user.first_name}\nآیدی عددی: `{msg.chat.id}`", parse_mode="Markdown")

# بررسی عضویت
@bot.callback_query_handler(func=lambda call: call.data == "check")
def check(call):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, call.from_user.id).status
        if status in ["member", "administrator", "creator"]:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            show_menu(call.message.chat.id)
        else:
            bot.answer_callback_query(call.id, "⚠️ هنوز عضو کانال نشدی!", show_alert=True)
    except:
        bot.answer_callback_query(call.id, "خطا در بررسی عضویت.", show_alert=True)

# منو اصلی
def show_menu(chat_id):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💡 راهنما", "🖼 ساخت عکس")
    bot.send_message(chat_id, "🎉 خوش اومدی، از ربات استفاده کن!", reply_markup=markup)

# راهنما
@bot.message_handler(func=lambda m: m.text == "💡 راهنما")
def help_msg(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 برگشت")
    text = (
        "📖 راهنمای ربات:\n"
        "✅ ارسال پیام برای گفت‌وگو با هوش مصنوعی.\n"
        "✅ ارسال لینک‌های اینستاگرام، اسپاتیفای، پینترست برای دریافت محتوا.\n"
        "✅ ساخت عکس دلخواه با دستور '🖼 ساخت عکس'.\n"
        "⚠️ رعایت قوانین ضروریست.\n"
        "🛠 پشتیبانی در صورت نیاز فعال است.\n"
    )
    bot.send_message(msg.chat.id, text, reply_markup=markup)

# برگشت
@bot.message_handler(func=lambda m: m.text == "🔙 برگشت")
def back(msg):
    show_menu(msg.chat.id)

# ساخت عکس
@bot.message_handler(func=lambda m: m.text == "🖼 ساخت عکس")
def make_image(msg):
    sent = bot.send_message(msg.chat.id, "🖼 متن دلخواه برای تصویر رو بفرست:")
    bot.register_next_step_handler(sent, send_image)

def send_image(msg):
    r = requests.get(f"https://v3.api-free.ir/image/?text={msg.text}").json()
    if r.get("ok"):
        bot.send_photo(msg.chat.id, r["result"])
    else:
        bot.send_message(msg.chat.id, "❌ خطا در ساخت تصویر.")

# تشخیص پیام‌ها
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_all(msg):
    if "instagram.com" in msg.text:
        insta(msg)
    elif "spotify.com" in msg.text:
        spotify(msg)
    elif "pin.it" in msg.text or "pinterest.com" in msg.text:
        pinterest(msg)
    else:
        ai_chat(msg)

# اینستاگرام دانلود
def insta(msg):
    url = f"https://pouriam.top/eyephp/instagram?url={msg.text}"
    try:
        res = requests.get(url).json()
        if "links" in res:
            for l in res["links"]:
                bot.send_message(msg.chat.id, l)
        else:
            bot.send_message(msg.chat.id, "❌ لینک نامعتبر یا محدود.")
    except:
        bot.send_message(msg.chat.id, "❌ خطا در پردازش لینک.")

# اسپاتیفای دانلود
def spotify(msg):
    url = f"http://api.cactus-dev.ir/spotify.php?url={msg.text}"
    try:
        res = requests.get(url).json()
        if res.get("ok"):
            bot.send_audio(msg.chat.id, res["data"]["download_url"], title=res["data"]["name"])
        else:
            bot.send_message(msg.chat.id, "❌ خطا یا لینک نامعتبر.")
    except:
        bot.send_message(msg.chat.id, "❌ خطا در دریافت موسیقی.")

# پینترست دانلود
def pinterest(msg):
    url = f"https://haji.s2025h.space/pin/?url={msg.text}&client_key=keyvip"
    try:
        res = requests.get(url).json()
        if res.get("status"):
            bot.send_photo(msg.chat.id, res["download_url"])
        else:
            bot.send_message(msg.chat.id, "❌ لینک نامعتبر.")
    except:
        bot.send_message(msg.chat.id, "❌ خطا در پردازش لینک.")

# چت هوش مصنوعی
def ai_chat(msg):
    text = msg.text
    for link in AI_LINKS:
        try:
            res = requests.get(link.format(text), timeout=5).text
            if res:
                bot.send_message(msg.chat.id, res)
                return
        except:
            continue
    bot.send_message(msg.chat.id, "❌ خطا در دریافت پاسخ، دوباره تلاش کن.")

# ست وب‌هوک و ران اپ
if __name__ == "__main__":
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}")
    app.run(host="0.0.0.0", port=10000)
