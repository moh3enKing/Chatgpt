import telebot
from flask import Flask, request
import requests
import re
import time

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv("TOKEN", "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0")
ADMIN_ID = 5637609683
CHANNEL_ID = "@netgoris"
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", f"https://chatgpt-qg71.onrender.com/{TOKEN}")

# Web services
AI_SERVICES = [
    "https://starsshoptl.ir/Ai/index.php?text={}",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text={}",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text={}"
]
INSTAGRAM_API = "https://pouriam.top/eyephp/instagram?url={}"
SPOTIFY_API = "http://api.cactus-dev.ir/spotify.php?url={}"
PINTEREST_API = "https://haji.s2025h.space/pin/?url={}&client_key=keyvip"
IMAGE_API = "https://v3.api-free.ir/image/?text={}"

# MongoDB setup
client = pymongo.MongoClient(MONGODB_URI)
db = client["telegram_bot"]
users_collection = db["users"]

# Spam protection
SPAM_LIMIT = 4
SPAM_WINDOW = 120  # seconds (2 minutes)

# Initialize Flask and Bot
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)

# Keyboards
MAIN_KEYBOARD = types.ReplyKeyboardMarkup(resize_keyboard=True)
MAIN_KEYBOARD.add(types.KeyboardButton("راهنما 📖"), types.KeyboardButton("پشتیبانی 🛠"))

SUPPORT_CANCEL_KEYBOARD = types.ReplyKeyboardMarkup(resize_keyboard=True)
SUPPORT_CANCEL_KEYBOARD.add(types.KeyboardButton("لغو 🚫"))

ADMIN_KEYBOARD = types.ReplyKeyboardMarkup(resize_keyboard=True)
ADMIN_KEYBOARD.add(
    types.KeyboardButton("بن کاربر 🚫"),
    types.KeyboardButton("آنبن کاربر ✅"),
    types.KeyboardButton("ارسال پیام 📩")
)

def check_channel_membership(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return False

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user = users_collection.find_one({"user_id": user_id})

    # Notify admin for first-time users
    if not user:
        users_collection.insert_one({"user_id": user_id, "joined": False, "messages": [], "support_mode": False, "banned": False})
        bot.send_message(
            ADMIN_ID,
            f"کاربر جدید استارت کرد:\nID: {user_id}\nUsername: @{message.from_user.username or 'None'}"
        )

    # Check if user is banned
    if user and user.get("banned", False):
        bot.reply_to(message, "⛔ شما از ربات بن شدی! برای اطلاعات بیشتر با پشتیبانی تماس بگیر.")
        return

    # Check if user has joined the channel
    if not check_channel_membership(user_id):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📢 جوین کانال", url="https://t.me/netgoris"))
        keyboard.add(types.InlineKeyboardButton("✅ تأیید", callback_data="check_join"))
        bot.reply_to(message, "لطفاً برای استفاده از ربات، ابتدا در کانال ما جوین کنید!", reply_markup=keyboard)
        return

    # Welcome message
    welcome_text = (
        "🎉 به ربات ما خوش اومدی!\n"
        "ممنون که جوین کردی! 😊 حالا می‌تونی از امکانات ربات استفاده کنی.\n"
        "برای اطلاعات بیشتر، دکمه راهنما رو بزن."
    )
    bot.reply_to(message, welcome_text, reply_markup=MAIN_KEYBOARD)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    if check_channel_membership(user_id):
        users_collection.update_one({"user_id": user_id}, {"$set": {"joined": True}})
        welcome_text = (
            "🎉 به ربات ما خوش اومدی!\n"
            "ممنون که جوین کردی! 😊 حالا می‌تونی از امکانات ربات استفاده کنی.\n"
            "برای اطلاعات بیشتر، دکمه راهنما رو بزن."
        )
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, welcome_text, reply_markup=MAIN_KEYBOARD)
    else:
        bot.edit_message_text(
            "❌ هنوز در کانال جوین نکردی!\nلطفاً در کانال جوین کن و دوباره تأیید بزن.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=call.message.reply_markup
        )

@bot.message_handler(func=lambda message: message.text == "راهنما 📖")
def guide(message):
    user_id = message.from_user.id
    if not check_channel_membership(user_id):
        bot.reply_to(message, "لطفاً اول در کانال جوین کن!")
        return

    guide_text = (
        "📖 **راهنمای استفاده از ربات** 📖\n\n"
        "🎯 **چطور از ربات استفاده کنم؟**\n"
        "این ربات بهت کمک می‌کنه تا محتوای اینستاگرام، اسپاتیفای، پینترست و تصاویر تولید شده با هوش مصنوعی رو دانلود کنی. کافیه لینک یا متن مورد نظرت رو بفرستی!\n\n"
        "🔗 **لینک‌های پشتیبانی‌شده**:\n"
        "- اینستاگرام: لینک پست یا ریل\n"
        "- اسپاتیفای: لینک آهنگ\n"
        "- پینترست: لینک پین\n"
        "- ساخت تصویر: متن دلخواه (مثال: `flower`)\n\n"
        "⚠️ **اخطارها و قوانین**:\n"
        "1. فقط لینک‌های معتبر از سرویس‌های بالا ارسال کن. لینک‌های نامعتبر باعث خطا می‌شن.\n"
        "2. اسپم نکن! حداکثر ۴ پیام در ۲ دقیقه می‌تونی بفرستی.\n"
        "3. در صورت تخلف، ممکنه از ربات بن بشی.\n"
        "4. برای هر مشکلی، از دکمه پشتیبانی استفاده کن.\n\n"
        "😊 **سؤالی داشتی؟** دکمه پشتیبانی رو بزن تا بتونیم باهات در ارتباط باشیم!"
    )
    bot.reply_to(message, guide_text, parse_mode="Markdown")
    bot.send_message(message.chat.id, "🌟 ما همیشه در خدمت شما هستیم!", reply_markup=MAIN_KEYBOARD)

@bot.message_handler(func=lambda message: message.text == "پشتیبانی 🛠")
def support(message):
    user_id = message.from_user.id
    if not check_channel_membership(user_id):
        bot.reply_to(message, "لطفاً اول در کانال جوین کن!")
        return

    users_collection.update_one({"user_id": user_id}, {"$set": {"support_mode": True}})
    bot.reply_to(message, "🛠 لطفاً پیامت رو برای پشتیبانی بفرست یا برای خروج 'لغو' رو بزن.", reply_markup=SUPPORT_CANCEL_KEYBOARD)

@bot.message_handler(func=lambda message: message.text == "لغو 🚫")
def cancel_support(message):
    user_id = message.from_user.id
    users_collection.update_one({"user_id": user_id}, {"$set": {"support_mode": False}})
    bot.reply_to(message, "🚫 پشتیبانی لغو شد. حالا می‌تونی از ربات استفاده کنی!", reply_markup=MAIN_KEYBOARD)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.reply_to(message, "⛔ این دستور فقط برای ادمینه!")
        return
    bot.reply_to(message, "پنل ادمین 🛠\nلطفاً یه گزینه انتخاب کن:", reply_markup=ADMIN_KEYBOARD)

@bot.message_handler(content_types=['text'])
def handle_message(message):
    user_id = message.from_user.id
    text = message.text
    user = users_collection.find_one({"user_id": user_id})

    if not user or not user.get("joined", False):
        bot.reply_to(message, "لطفاً اول در کانال جوین کن!")
        return

    if user.get("banned", False):
        bot.reply_to(message, "⛔ شما از ربات بن شدی! برای اطلاعات بیشتر با پشتیبانی تماس بگیر.")
        return

    # Handle support mode
    if user.get("support_mode", False):
        if text == "لغو":
            cancel_support(message)
        else:
            bot.send_message(
                ADMIN_ID,
                f"📩 پیام پشتیبانی از @{message.from_user.username or 'None'} (ID: {user_id}):\n{text}",
                reply_to_message_id=message.message_id
            )
            bot.reply_to(message, "✅ پیامت به پشتیبانی ارسال شد. منتظر جواب باش!")
        return

    # Spam protection
    now = datetime.now()
    messages = user.get("messages", [])
    messages = [ts for ts in messages if (now - datetime.fromisoformat(ts)).total_seconds() < SPAM_WINDOW]
    messages.append(now.isoformat())
    if len(messages) > SPAM_LIMIT:
        bot.reply_to(message, "⛔ لطفاً صبر کن! بیش از حد پیام فرستادی. ۲ دقیقه دیگه امتحان کن.")
        return
    users_collection.update_one({"user_id": user_id}, {"$set": {"messages": messages}})

    # Handle admin commands
    if user_id == ADMIN_ID:
        if text in ["بن کاربر 🚫", "آنبن کاربر ✅", "ارسال پیام 📩"]:
            bot.reply_to(message, "لطفاً آیدی عددی کاربر رو بفرست:")
            users_collection.update_one({"user_id": user_id}, {"$set": {"admin_action": text}})
            return
        elif user.get("admin_action"):
            if not text.strip().isdigit():
                bot.reply_to(message, "لطفاً یه آیدی عددی معتبر بفرست!")
                return
            target_user_id = int(text.strip())
            users_collection.update_one({"user_id": user_id}, {"$set": {"admin_action": None, "target_user_id": target_user_id}})
            bot.reply_to(message, "لطفاً پیام اطلاع‌رسانی به کاربر رو بفرست:")
            return
        elif user.get("target_user_id"):
            action = user.get("admin_action")
            target_user_id = user.get("target_user_id")
            notification = text
            users_collection.update_one({"user_id": user_id}, {"$set": {"target_user_id": None}})

            if action == "بن کاربر 🚫":
                users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": True}})
                bot.send_message(target_user_id, f"⛔ شما بن شدی!\nدلیل: {notification}")
                bot.reply_to(message, "کاربر با موفقیت بن شد!")
            elif action == "آنبن کاربر ✅":
                users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": False}})
                bot.send_message(target_user_id, f"✅ بن شما برداشته شد!\nپیام ادمین: {notification}")
                bot.reply_to(message, "کاربر با موفقیت آنبن شد!")
            elif action == "ارسال پیام 📩":
                bot.send_message(target_user_id, f"📩 پیام از ادمین:\n{notification}")
                bot.reply_to(message, "پیام با موفقیت ارسال شد!")
            return

    # Handle web services
    if "instagram.com" in text:
        handle_instagram(message, text)
    elif "spotify.com" in text:
        handle_spotify(message, text)
    elif "pinterest.com" in text:
        handle_pinterest(message, text)
    else:
        handle_ai_or_image(message, text)

def handle_instagram(message, url):
    try:
        response = requests.get(INSTAGRAM_API.format(url))
        if response.status_code != 200:
            bot.reply_to(message, "❌ خطا در ارتباط با سرور اینستاگرام. لطفاً بعداً امتحان کن.")
            return
        data = response.json()
        if "links" in data:
            for link in data["links"]:
                if link.endswith(".mp4"):
                    bot.send_video(message.chat.id, link)
                elif link.endswith((".jpg", ".png")):
                    bot.send_photo(message.chat.id, link)
        else:
            bot.reply_to(message, "❌ خطا: هیچ رسانه‌ای پیدا نشد!")
    except Exception as e:
        logger.error(f"Error processing Instagram link: {e}")
        bot.reply_to(message, f"❌ خطا در پردازش لینک اینستاگرام: {str(e)}")

def handle_spotify(message, url):
    try:
        response = requests.get(SPOTIFY_API.format(url))
        if response.status_code != 200:
            bot.reply_to(message, "❌ خطا در ارتباط با سرور اسپاتیفای. لطفاً بعداً امتحان کن.")
            return
        data = response.json()
        if data.get("ok") and "data" in data and "download_url" in data["data"]["track"]:
            bot.send_audio(message.chat.id, data["data"]["track"]["download_url"])
        else:
            bot.reply_to(message, "❌ خطا: هیچ آهنگی پیدا نشد!")
    except Exception as e:
        logger.error(f"Error processing Spotify link: {e}")
        bot.reply_to(message, f"❌ خطا در پردازش لینک اسپاتیفای: {str(e)}")

def handle_pinterest(message, url):
    try:
        response = requests.get(PINTEREST_API.format(url))
        if response.status_code != 200:
            bot.reply_to(message, "❌ خطا در ارتباط با سرور پینترست. لطفاً بعداً امتحان کن.")
            return
        data = response.json()
        if data.get("status") and "download_url" in data:
            bot.send_photo(message.chat.id, data["download_url"])
        else:
            bot.reply_to(message, "❌ خطا: هیچ تصویری پیدا نشد!")
    except Exception as e:
        logger.error(f"Error processing Pinterest link: {e}")
        bot.reply_to(message, f"❌ خطا در پردازش لینک پینترست: {str(e)}")

def handle_ai_or_image(message, text):
    # Try AI services
    for api in AI_SERVICES:
        try:
            response = requests.get(api.format(text))
            if response.status_code == 200:
                bot.reply_to(message, response.text)
                return
        except Exception as e:
            logger.error(f"Error processing AI service {api}: {e}")
            continue

    # If AI fails, try image generation
    try:
        response = requests.get(IMAGE_API.format(text))
        if response.status_code != 200:
            bot.reply_to(message, "❌ خطا در ارتباط با سرور ساخت تصویر. لطفاً بعداً امتحان کن.")
            return
        data = response.json()
        if data.get("ok") and "result" in data:
            bot.send_photo(message.chat.id, data["result"])
        else:
            bot.reply_to(message, "❌ خطا: هیچ تصویری تولید نشد!")
    except Exception as e:
        logger.error(f"Error processing image generation: {e}")
        bot.reply_to(message, f"❌ خطا در پردازش درخواست: {str(e)}")

# Flask webhook endpoint
@app.route(f"/{TOKEN}", methods=["GET", "POST"])
def webhook():
    try:
        if request.method == "POST":
            update = request.get_json()
            if update:
                bot.process_new_updates([telebot.types.Update.de_json(update)])
                return "", 200
        elif request.method == "GET":
            # Handle GET requests for testing or webhook verification
            return "Webhook is active", 200
        return "", 400
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return "", 500

# Set webhook
def set_webhook():
    try:
        bot.remove_webhook()
        success = bot.set_webhook(url=WEBHOOK_URL)
        if success:
            logger.info(f"Webhook set to {WEBHOOK_URL}")
        else:
            logger.error("Failed to set webhook")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")

# For Gunicorn, export the Flask app
application = app

# ست وب‌هوک و ران اپ
if __name__ == "__main__":
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}")
    app.run(host="0.0.0.0", port=10000)
