import telebot
from flask import Flask, request
import requests
from pymongo import MongoClient
import time

# ---------------------- تنظیمات ----------------------
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"
CHANNEL_USERNAME = "@netgoris"
ADMIN_ID = 5637609683
MONGO_URL = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# ---------------------- اتصال ----------------------
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
client = MongoClient(MONGO_URL)
db = client["TellGPT"]
users = db["users"]
bans = db["bans"]
spams = {}

# ---------------------- کیبوردها ----------------------
def main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💬 پشتیبانی", "📖 راهنما", "⚙️ پنل مدیریت")
    return markup

def join_keyboard():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"))
    markup.add(telebot.types.InlineKeyboardButton("✅ عضویت انجام شد", callback_data="check_join"))
    return markup

# ---------------------- بررسی عضویت ----------------------
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ---------------------- پیام راهنما ----------------------
HELP_TEXT = """
📌 راهنمای استفاده از ربات:

✅ برای دریافت پاسخ از هوش مصنوعی، کافیست پیام خود را ارسال کنید.

⚠️ قوانین:
1. ارسال محتوای غیرمجاز یا تبلیغاتی ممنوع است.
2. ابتدا باید در کانال عضو شوید.
3. رعایت احترام الزامی است.
4. ربات در صورت اسپم، تا 2 دقیقه پاسخ نمی‌دهد.

🛠 پشتیبانی 24 ساعته: فقط از طریق دکمه "💬 پشتیبانی"

🤖 با آرزوی تجربه‌ای جذاب با TellGPT
"""

# ---------------------- هندل استارت ----------------------
@bot.message_handler(commands=["start"])
def start(message):
    if message.from_user.id in bans.distinct("user_id"):
        return

    if not is_user_joined(message.from_user.id):
        bot.send_message(message.chat.id, f"برای استفاده از ربات ابتدا در کانال {CHANNEL_USERNAME} عضو شوید👇", reply_markup=join_keyboard())
        return

    if not users.find_one({"user_id": message.from_user.id}):
        users.insert_one({"user_id": message.from_user.id})
        bot.send_message(ADMIN_ID, f"🟢 کاربر جدید استارت زد:\n👤 {message.from_user.first_name} ({message.from_user.id})")

    bot.send_message(message.chat.id, "به ربات TellGPT خوش آمدید! 👋", reply_markup=main_keyboard())

# ---------------------- چک عضویت ----------------------
@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(call):
    if is_user_joined(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ عضویت شما تایید شد. از ربات لذت ببرید.", reply_markup=main_keyboard())
    else:
        bot.answer_callback_query(call.id, "⚠️ هنوز عضو کانال نشدید!", show_alert=True)

# ---------------------- ضداسپم ----------------------
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    if message.from_user.id in bans.distinct("user_id"):
        return

    if message.text == "📖 راهنما":
        bot.send_message(message.chat.id, HELP_TEXT, reply_markup=main_keyboard())
        return

    if message.text == "💬 پشتیبانی":
        bot.send_message(message.chat.id, "لطفا پیام خود را ارسال کنید:", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, support_handler)
        return

    if message.text == "⚙️ پنل مدیریت" and message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "به پنل خوش آمدید:\n- /ban [ID] برای بن کردن\n- /unban [ID] برای آنبن", reply_markup=main_keyboard())
        return

    # ضد اسپم
    now = time.time()
    times = spams.get(message.from_user.id, [])
    times = [t for t in times if now - t < 60]  # 1 دقیقه قبل
    times.append(now)
    spams[message.from_user.id] = times

    if len(times) >= 4:
        bans.insert_one({"user_id": message.from_user.id})
        bot.send_message(message.chat.id, "🚫 به دلیل ارسال بیش از حد پیام، شما بن شدید.")
        return

    handle_services(message)

# ---------------------- پشتیبانی ----------------------
def support_handler(message):
    bot.send_message(ADMIN_ID, f"📨 پیام جدید پشتیبانی:\nاز {message.from_user.id}:\n{message.text}")
    bot.send_message(message.chat.id, "✅ پیام شما ارسال شد.", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.reply_to_message and m.chat.id == ADMIN_ID)
def reply_support(message):
    try:
        target_id = int(message.reply_to_message.text.split("از ")[1].split(":")[0])
        bot.send_message(target_id, f"💬 پاسخ پشتیبانی:\n{message.text}")
        bot.send_message(message.chat.id, "✅ پاسخ ارسال شد.")
    except:
        bot.send_message(message.chat.id, "❌ خطا در ارسال پاسخ.")

# ---------------------- وب‌سرویس‌ها ----------------------
def handle_services(message):
    text = message.text

    # تشخیص لینک و پاسخ‌دهی
    if "instagram.com" in text:
        res = requests.get(f"https://pouriam.top/eyephp/instagram?url={text}").json()
        if res.get("links"):
            for link in res["links"]:
                bot.send_message(message.chat.id, link)
        return

    if "spotify.com" in text:
        res = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={text}").json()
        if res.get("data", {}).get("download_url"):
            bot.send_audio(message.chat.id, res["data"]["download_url"])
        return

    if "pin.it" in text or "pinterest.com" in text:
        res = requests.get(f"https://haji.s2025h.space/pin/?url={text}&client_key=keyvip").json()
        if res.get("download_url"):
            bot.send_photo(message.chat.id, res["download_url"])
        return

    if text.startswith("/image "):
        query = text.replace("/image ", "")
        res = requests.get(f"https://v3.api-free.ir/image/?text={query}").json()
        if res.get("result"):
            bot.send_photo(message.chat.id, res["result"])
        return

    # وب‌سرویس هوش مصنوعی
    for url in [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]:
        try:
            res = requests.get(url, timeout=5).text
            if res:
                bot.send_message(message.chat.id, res)
                return
        except:
            continue

    bot.send_message(message.chat.id, "❗️ لینک یا دستور نامعتبر است.")

# ---------------------- بن و آنبن ----------------------
@bot.message_handler(commands=["ban"])
def ban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        bans.insert_one({"user_id": target_id})
        bot.send_message(message.chat.id, "✅ کاربر بن شد.")
    except:
        bot.send_message(message.chat.id, "❌ دستور اشتباه.")

@bot.message_handler(commands=["unban"])
def unban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        bans.delete_one({"user_id": target_id})
        bot.send_message(message.chat.id, "✅ کاربر آنبن شد.")
    except:
        bot.send_message(message.chat.id, "❌ دستور اشتباه.")

# ---------------------- وب‌هوک ----------------------
@app.route('/', methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    return "OK"

def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

# ---------------------- اجرا ----------------------
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=5000)
