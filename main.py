import telebot
from telebot import types
from flask import Flask, request
import requests
import threading
import time
from pymongo import MongoClient
from datetime import datetime, timedelta

# ====== تنظیمات =======
API_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

WEBHOOK_HOST = "https://chatgpt-qg71.onrender.com"
WEBHOOK_PATH = "/"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH

WEBHOOK_PORT = 1000  # پورت رندر

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# اتصال به دیتابیس
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["telegram_bot"]
users_col = db["users"]
banned_col = db["banned"]
spam_col = db["spam"]
support_col = db["support"]  # ذخیره وضعیت پشتیبانی کاربران

# ----------------
# متن‌ها و استیکرها
JOIN_MSG_ID = None  # برای ذخیره پیام جوین اجباری جهت پاک کردن
HELP_TEXT = """
📚 *راهنمای استفاده از ربات:*

1️⃣ برای شروع، ابتدا باید عضو کانال ما شوید.
2️⃣ پس از عضویت، دکمه "تایید عضویت" را بزنید.
3️⃣ در صورت تایید، می‌توانید از امکانات ربات استفاده کنید.

⚠️ *اخطارها و قوانین:*
- ارسال بیش از ۴ پیام در ۲ دقیقه ممنوع است (سیستم ضد اسپم فعال می‌شود).
- ارسال لینک‌های غیرمجاز به ربات ممنوع است.
- ربات تنها از لینک‌های اینستاگرام، اسپاتیفای و پینترست پشتیبانی می‌کند.
- هرگونه سو استفاده باعث بن شدن خواهد شد.

برای دیدن توضیحات بیشتر، دکمه پایین را بزنید.
"""

HELP_EXTRA_TEXT = """
ما همیشه خدمتگذار شما هستیم و در تلاشیم بهترین خدمات را ارائه دهیم.
هرگونه سوال یا مشکل داشتید با دکمه پشتیبانی تماس بگیرید.
"""

WELCOME_STICKER = "CAACAgIAAxkBAAEGoF9jLXxVp98tSr0M2PEly7izDu3HtAACSwEAAjFlwUpJPp0kuUi9DyME"  # استیکر تبریک

# دکمه‌های جوین اجباری
def get_join_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("کانال ما 📢", url=f"https://t.me/{CHANNEL_USERNAME}"))
    keyboard.add(types.InlineKeyboardButton("✅ تایید عضویت", callback_data="check_join"))
    return keyboard

# دکمه‌های راهنما
def get_help_keyboard(stage="main"):
    keyboard = types.InlineKeyboardMarkup()
    if stage == "main":
        keyboard.add(types.InlineKeyboardButton("📖 راهنما", callback_data="show_help"))
    elif stage == "help_extra":
        keyboard.add(types.InlineKeyboardButton("بازگشت نداریم! 🚫", callback_data="help_extra"))
    return keyboard

# کیبورد اصلی پیوی (با دکمه پشتیبانی)
def get_private_keyboard(support_active=False):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if not support_active:
        keyboard.add("📞 پشتیبانی")
    else:
        keyboard.add("لغو پشتیبانی")
    return keyboard

# -------------------
# توابع کمکی

def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status not in ['left', 'kicked']
    except Exception:
        return False

def send_owner_message(text):
    try:
        bot.send_message(OWNER_ID, text, parse_mode="Markdown")
    except Exception:
        pass

# چک اسپم (۴ پیام در ۲ دقیقه)
def check_spam(user_id):
    now = datetime.utcnow()
    spam_data = spam_col.find_one({"user_id": user_id})
    if spam_data:
        msgs = spam_data.get("timestamps", [])
        msgs = [t for t in msgs if now - t < timedelta(minutes=2)]
        if len(msgs) >= 4:
            return True
        msgs.append(now)
        spam_col.update_one({"user_id": user_id}, {"$set": {"timestamps": msgs}})
    else:
        spam_col.insert_one({"user_id": user_id, "timestamps": [now]})
    return False

# حذف رکورد اسپم بعد از دو دقیقه سکوت
def clear_spam(user_id):
    time.sleep(120)
    spam_col.delete_one({"user_id": user_id})

# ارسال پیام خطا وب‌سرویس
def send_error_message(chat_id, text="خطایی در پردازش درخواست رخ داده است. لطفا دوباره تلاش کنید."):
    bot.send_message(chat_id, text)

# تشخیص لینک‌ها
def detect_link(text):
    text = text.lower()
    if "instagram.com" in text:
        return "instagram"
    elif "spotify.com" in text:
        return "spotify"
    elif "pin.it" in text or "pinterest.com" in text:
        return "pinterest"
    else:
        return None

# وب‌سرویس چت هوش مصنوعی با fallback
AI_APIS = [
    "https://starsshoptl.ir/Ai/index.php?text=",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text=",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text="
]

def ai_chat_response(text):
    for api in AI_APIS:
        try:
            r = requests.get(api + requests.utils.quote(text), timeout=7)
            if r.status_code == 200:
                j = r.json()
                # فرض میکنیم پاسخ توی کلید 'result' یا 'answer' یا همان متن بدست میاد، اگر نداشت متن ساده برگردان
                # چون جواب نمونه تو توضیحات "Hey there! What's on your mind today?" بود
                # چون خروجی هردو یکسانه، خود متن رو می فرستیم
                # اگر ساختار فرق داشت میشه اصلاح کرد
                if "result" in j:
                    return j["result"]
                elif "answer" in j:
                    return j["answer"]
                else:
                    # fallback به متن اولیه
                    return r.text
            else:
                continue
        except Exception:
            continue
    return None

# دانلودرها
def insta_downloader(url):
    try:
        r = requests.get("https://pouriam.top/eyephp/instagram?url=" + requests.utils.quote(url), timeout=10)
        if r.status_code == 200:
            j = r.json()
            links = j.get("links")
            if links and isinstance(links, list) and len(links) > 0:
                return links[0]  # لینک مستقیم اولی
        return None
    except:
        return None

def spotify_downloader(url):
    try:
        r = requests.get("http://api.cactus-dev.ir/spotify.php?url=" + requests.utils.quote(url), timeout=10)
        if r.status_code == 200:
            j = r.json()
            if j.get("ok") and "data" in j:
                return j["data"]["track"].get("download_url")
        return None
    except:
        return None

def pinterest_downloader(url):
    try:
        r = requests.get(f"https://haji.s2025h.space/pin/?url={requests.utils.quote(url)}&client_key=keyvip", timeout=10)
        if r.status_code == 200:
            j = r.json()
            if j.get("status"):
                return j.get("download_url")
        return None
    except:
        return None

# ساخت عکس
def generate_image(text):
    try:
        r = requests.get(f"https://v3.api-free.ir/image/?text={requests.utils.quote(text)}", timeout=10)
        if r.status_code == 200:
            j = r.json()
            if j.get("ok") and j.get("result"):
                return j.get("result")
        return None
    except:
        return None

# -------------------------
# هندلرهای ربات

# صفحه استارت و جوین اجباری
@bot.message_handler(commands=["start"])
def start_handler(message):
    user_id = message.from_user.id

    # ثبت یوزر در دیتابیس اگر اولین بار
    if users_col.find_one({"user_id": user_id}) is None:
        users_col.insert_one({"user_id": user_id, "start_time": datetime.utcnow()})
        # اطلاع به ادمین
        send_owner_message(f"کاربر جدید استارت زد:\n👤 {message.from_user.first_name}\n🆔 `{user_id}`")

    # اگر بن شده کاربر
    if banned_col.find_one({"user_id": user_id}):
        bot.send_message(user_id, "شما در ربات بن شده‌اید. برای اطلاعات بیشتر با پشتیبانی تماس بگیرید.")
        return

    # ارسال پیام جوین اجباری
    kb = get_join_keyboard()
    global JOIN_MSG_ID
    sent = bot.send_message(user_id, "لطفا ابتدا عضو کانال شوید و سپس عضویت خود را تایید کنید:", reply_markup=kb)
    JOIN_MSG_ID = sent.message_id

    # ثبت وضعیت جوین اجباری در دیتابیس
    users_col.update_one({"user_id": user_id}, {"$set": {"awaiting_join": True}})

    # ارسال کیبورد معمولی برای pv
    bot.send_message(user_id, "برای شروع، لطفا عضو کانال شوید.", reply_markup=get_private_keyboard())

# پاسخ به دکمه‌ها
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    user_id = call.from_user.id

    if call.data == "check_join":
        joined = is_user_joined(user_id)
        if joined:
            # پاک کردن پیام جوین اجباری
            try:
                bot.delete_message(user_id, call.message.message_id)
            except Exception:
                pass

            # آپدیت وضعیت
            users_col.update_one({"user_id": user_id}, {"$set": {"awaiting_join": False, "joined": True}})

            # پیام خوش آمد و دکمه راهنما
            kb = get_help_keyboard("main")
            bot.send_message(user_id, "🎉 عضویت شما تایید شد.\nخوش آمدید!", reply_markup=kb)
        else:
            bot.answer_callback_query(call.id, "شما هنوز عضو کانال نشده‌اید!", show_alert=True)

    elif call.data == "show_help":
        # ویرایش پیام به متن راهنما
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                              text=HELP_TEXT, parse_mode="Markdown", reply_markup=get_help_keyboard("help_extra"))

    elif call.data == "help_extra":
        # ویرایش پیام به پیام دوم راهنما که برگشت نداره
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                              text=HELP_EXTRA_TEXT, parse_mode="Markdown", reply_markup=get_help_keyboard("help_extra"))

# هندلر پیام‌های متنی
@bot.message_handler(func=lambda m: True)
def message_handler(message):
    user_id = message.from_user.id
    text = message.text

    # بررسی بن بودن
    if banned_col.find_one({"user_id": user_id}):
        bot.send_message(user_id, "شما در ربات بن شده‌اید و نمی‌توانید پیام ارسال کنید.")
        return

    # بررسی اسپم
    if check_spam(user_id):
        bot.send_message(user_id, "🚫 شما بیش از حد پیام ارسال کرده‌اید. لطفا ۲ دقیقه صبر کنید.")
        return
    else:
        # چون 4 پیام در 2 دقیقه بیشتر نباید باشه، پس اگر رسیدیم به 4، بعد از 2 دقیقه پاکش می‌کنیم.
        spam_data = spam_col.find_one({"user_id": user_id})
        if spam_data and len(spam_data.get("timestamps", [])) >= 4:
            threading.Thread(target=clear_spam, args=(user_id,)).start()

    # بررسی وضعیت جوین اجباری
    user_data = users_col.find_one({"user_id": user_id})
    if user_data and user_data.get("awaiting_join", False):
        bot.send_message(user_id, "لطفا ابتدا عضویت خود را تایید کنید.")
        return

    # دکمه پشتیبانی
    support_status = support_col.find_one({"user_id": user_id})
    if support_status and support_status.get("active", False):
        # فوروارد پیام به ادمین
        try:
            fwd = bot.forward_message(OWNER_ID, user_id, message.message_id)
            # ذخیره آیدی پیام ادمین و کاربر برای ریپلای
            support_col.update_one({"user_id": user_id}, {"$set": {"last_user_msg_id": message.message_id, "last_admin_msg_id": None}})
        except Exception:
            pass
        return

    # فرمان لغو پشتیبانی
    if text == "لغو پشتیبانی":
        support_col.update_one({"user_id": user_id}, {"$set": {"active": False}})
        bot.send_message(user_id, "پشتیبانی لغو شد.", reply_markup=get_private_keyboard(support_active=False))
        return

    # فرمان پشتیبانی
    if text == "📞 پشتیبانی":
        support_col.update_one({"user_id": user_id}, {"$set": {"active": True}})
        bot.send_message(user_id, "شما وارد بخش پشتیبانی شدید. پیام خود را ارسال کنید.", reply_markup=get_private_keyboard(support_active=True))
        return

    # تشخیص لینک
    link_type = detect_link(text)
    if link_type == "instagram":
        dl_url = insta_downloader(text)
        if dl_url:
            bot.send_message(user_id, dl_url)
        else:
            send_error_message(user_id)
        return
    elif link_type == "spotify":
        dl_url = spotify_downloader(text)
        if dl_url:
            bot.send_message(user_id, dl_url)
        else:
            send_error_message(user_id)
        return
    elif link_type == "pinterest":
        dl_url = pinterest_downloader(text)
        if dl_url:
            bot.send_message(user_id, dl_url)
        else:
            send_error_message(user_id)
        return

    # اگر لینک نبود یا غیرمجاز بود اخطار بده
    if text.startswith("http") or text.startswith("https"):
        bot.send_message(user_id, "⚠️ این لینک توسط ربات پشتیبانی نمی‌شود.\nلطفا فقط لینک‌های اینستاگرام، اسپاتیفای و پینترست ارسال کنید.")
        return

    # بررسی اگر پیام ساخت عکس است (مثلا فرمان خاصی داشت)
    if text.startswith("/image ") or text.startswith("تصویر "):
        cmd_text = text.replace("/image ", "").replace("تصویر ", "").strip()
        if cmd_text:
            img_url = generate_image(cmd_text)
            if img_url:
                bot.send_photo(user_id, img_url)
            else:
                send_error_message(user_id)
        else:
            bot.send_message(user_id, "لطفا متن تصویر را بعد از دستور وارد کنید.\nمثال: /image گل")
        return

    # اگر پیام معمولی است، پاسخ چت هوش مصنوعی
    answer = ai_chat_response(text)
    if answer:
        bot.send_message(user_id, answer)
    else:
        send_error_message(user_id)

# هندلر پیام‌های ادمین (پشتیبانی و مدیریت بن)
@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID, content_types=["text"])
def owner_handler(message):
    text = message.text

    # پاسخ به پیام کاربر در پشتیبانی (ریپلای)
    if message.reply_to_message:
        replied_msg = message.reply_to_message
        # پیدا کردن کاربر متناظر با پیام ریپلای شده
        for s in support_col.find({"active": True}):
            # چک کردن اگر پیام ریپلای شده همان پیام ادمین است
            if s.get("last_admin_msg_id") == replied_msg.message_id:
                user_id = s["user_id"]
                try:
                    sent = bot.send_message(user_id, text, reply_to_message_id=s.get("last_user_msg_id"))
                    support_col.update_one({"user_id": user_id}, {"$set": {"last_admin_msg_id": sent.message_id}})
                except Exception:
                    pass
                return

    # فرمان بن کاربر: /ban <user_id>
    if text.startswith("/ban "):
        try:
            target_id = int(text.split(" ")[1])
            bot.send_message(OWNER_ID, f"لطفا پیام اطلاع‌رسانی بن به کاربر (ID: {target_id}) را ارسال کنید:")
            # منتظر پیام بعدی می‌شویم (ساده‌ترین راه ذخیره حالت یا استفاده از متغیر)
            # این بخش برای سادگی در این کد نوشته نشده کامل (باید state machine ساخت)
            # به همین دلیل توصیه می‌کنم مرحله به مرحله کامل کنیم
        except:
            bot.send_message(OWNER_ID, "فرمت فرمان اشتباه است. مثال: /ban 123456789")
        return

    # فرمان آنبن کاربر: /unban <user_id>
    if text.startswith("/unban "):
        try:
            target_id = int(text.split(" ")[1])
            banned_col.delete_one({"user_id": target_id})
            bot.send_message(OWNER_ID, f"کاربر {target_id} از بن خارج شد.")
        except:
            bot.send_message(OWNER_ID, "فرمت فرمان اشتباه است. مثال: /unban 123456789")
        return

# وب‌هوک فلاسک

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "", 200
