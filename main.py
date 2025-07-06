import logging
import re
import time
import asyncio
from functools import wraps

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatAction, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
)
from telegram.error import BadRequest
from pymongo import MongoClient
import requests

# ====== تنظیمات اولیه =======
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"
MONGO_URL = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
SPAM_LIMIT = 4
SPAM_INTERVAL = 120  # seconds

# وب‌سرویس‌ها
AI_SERVICES = [
    "https://starsshoptl.ir/Ai/index.php?text=",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text=",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text=",
]

INSTAGRAM_API = "https://pouriam.top/eyephp/instagram?url="
SPOTIFY_API = "http://api.cactus-dev.ir/spotify.php?url="
PINTEREST_API = "https://haji.s2025h.space/pin/?url={}&client_key=keyvip"
IMAGE_API = "https://v3.api-free.ir/image/?text="

# ======= لاگینگ ========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== اتصال به دیتابیس =======
client = MongoClient(MONGO_URL)
db = client['telegrambot']
users_col = db['users']
support_col = db['support']

# ====== ضد اسپم =======
user_message_times = {}

def anti_spam(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        now = time.time()
        times = user_message_times.get(user_id, [])
        times = [t for t in times if now - t < SPAM_INTERVAL]
        times.append(now)
        user_message_times[user_id] = times
        if len(times) > SPAM_LIMIT:
            try:
                await update.message.reply_text(
                    "⚠️ لطفاً آرامش داشته باشید! به‌دلیل ارسال پیام‌های متعدد، ۲ دقیقه سکوت فعال شد."
                )
                return
            except:
                return
        return await func(update, context)
    return wrapper

# ====== چک عضویت =======
async def check_joined(user_id: int, bot):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except:
        return False

# ====== کیبورد جین اجباری =======
def join_keyboard():
    buttons = [
        [InlineKeyboardButton("📢 کانال رسمی", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("✅ عضو شدم", callback_data="joined")]
    ]
    return InlineKeyboardMarkup(buttons)

# ====== کیبورد اصلی =======
def main_keyboard():
    buttons = [
        [InlineKeyboardButton("📖 راهنما", callback_data="help")],
        [InlineKeyboardButton("🛠 پشتیبانی", callback_data="support")]
    ]
    return InlineKeyboardMarkup(buttons)

# ====== متن‌ها =======
WELCOME_TEXT = f"""🌟 خوش آمدید به ربات حرفه‌ای ما!

اینجا می‌توانید به امکانات هوش مصنوعی، دانلودر پیشرفته و ابزارهای جذاب به‌صورت رایگان دسترسی داشته باشید.

برای شروع، لطفاً عضو کانال ما شوید.

کانال رسمی: {CHANNEL_USERNAME}

بعد از عضویت، روی دکمه "✅ عضو شدم" کلیک کنید.
"""

HELP_TEXT = f"""
📚 راهنمای جامع استفاده از ربات:

سلام دوست عزیز، خوش اومدی به ربات حرفه‌ای ما! 😍

اینجا می‌تونی از کلی امکانات جذاب بهره ببری:

🔹 امکانات اصلی:

✅ گفت‌وگوی هوشمند  
کافیه سوال، درخواست یا متن خودتو بفرستی، هوش مصنوعی سریع جواب می‌ده.

✅ دانلود از اینستاگرام، اسپاتیفای، پینترست  
برای دانلود فقط لینک بفرست، ربات خودش تشخیص می‌ده و محتوا رو مستقیم می‌فرسته:
• اینستاگرام → دانلود عکس یا ویدیو  
• اسپاتیفای → دانلود آهنگ با کیفیت  
• پینترست → دانلود عکس با کیفیت  

✅ ساخت عکس  
دستور: ساخت عکس متن شما  
توجه: متن باید انگلیسی باشه، مثال: ساخت عکس flower

✅ ارتباط مستقیم با مدیر  
از دکمه "پشتیبانی" در چت خصوصی استفاده کن.

⚠️ قوانین ربات:
🚫 ارسال ۴ پیام پشت هم باعث سکوت ۲ دقیقه‌ای می‌شه  
🚫 فقط لینک‌های اینستاگرام، اسپاتیفای، پینترست یا دستور ساخت عکس مجازه  
🚫 تبلیغ، توهین، ارسال لینک ناشناس = مسدودیت دائم  

🛠 ربات همواره در حال به‌روزرسانی و بهبود هست و در نسخه اولیه قرار داره.

🕰 ربات همیشه فعاله و آماده پاسخ‌گویی به توئه  
ممنون که از ربات ما استفاده می‌کنی، بهترین‌ها برات آرزو می‌کنیم! 💙
"""

SUPPORT_TEXT = "برای ارتباط با مدیر، پیام خود را ارسال کنید. برای خروج از پشتیبانی /لغو را بفرستید."

ALWAYS_SERVING_TEXT = """
💡 همواره در خدمت شما هستیم!

برای بازگشت، از منوی پایین استفاده کنید.
"""

# ====== بررسی لینک‌ها =======
def detect_link_type(text: str):
    text = text.lower()
    if "instagram.com" in text:
        return "instagram"
    elif "spotify.com" in text:
        return "spotify"
    elif "pin.it" in text or "pinterest.com" in text:
        return "pinterest"
    elif re.match(r'^ساخت عکس ', text):
        return "make_image"
    else:
        return "unknown"

# ====== پاسخ هوش مصنوعی =======
async def ask_ai(text):
    for api in AI_SERVICES:
        try:
            url = api + requests.utils.quote(text)
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                result = r.text.strip()
                if result:
                    return result
        except Exception as e:
            continue
    return "متاسفانه پاسخ مناسبی دریافت نشد، لطفاً دوباره تلاش کنید."

# ====== دانلود اینستا =======
def insta_download(url):
    try:
        r = requests.get(INSTAGRAM_API + url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            links = data.get("links", [])
            if links:
                return links[0]  # لینک مستقیم اولین فایل
        return None
    except:
        return None

# ====== دانلود اسپاتیفای =======
def spotify_download(url):
    try:
        r = requests.get(SPOTIFY_API + url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("ok") and "data" in data and "track" in data["data"]:
                return data["data"]["track"].get("download_url")
        return None
    except:
        return None

# ====== دانلود پینترست =======
def pinterest_download(url):
    try:
        full_url = PINTEREST_API.format(url)
        r = requests.get(full_url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("status"):
                return data.get("download_url")
        return None
    except:
        return None

# ====== ساخت عکس =======
def make_image(text):
    try:
        url = IMAGE_API + requests.utils.quote(text)
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("ok"):
                return data.get("result")
        return None
    except:
        return None

# ====== استارت و جین اجباری =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    user = update.effective_user

    # ثبت کاربر در دیتابیس اگر وجود ندارد
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({"user_id": user_id, "first_seen": time.time(), "banned": False})

        # ارسال پیام به ادمین برای کاربر جدید
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"👤 کاربر جدید: [{user.first_name}](tg://user?id={user_id})\nآیدی: `{user_id}`",
            parse_mode="Markdown"
        )

    # چک عضویت کانال
    joined = await check_joined(user_id, context.bot)
    if not joined:
        # ارسال پیام جین اجباری با دکمه‌ها
        msg = await update.message.reply_text(
            f"⚠️ لطفاً ابتدا عضو کانال {CHANNEL_USERNAME} شوید تا بتوانید از ربات استفاده کنید.",
            reply_markup=join_keyboard()
        )
        context.user_data["join_message_id"] = msg.message_id
        return

    # ارسال پیام خوش آمد
    await update.message.reply_text(
        HELP_TEXT,
        reply_markup=main_keyboard()
    )

# ====== تایید جین شدن =======
async def joined_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    joined = await check_joined(user_id, context.bot)
    if joined:
        # حذف پیام جین اجباری
        if "join_message_id" in context.user_data:
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=context.user_data["join_message_id"])
            except BadRequest:
                pass

        # ارسال پیام خوش آمد با راهنما
        await query.message.reply_text(
            HELP_TEXT,
            reply_markup=main_keyboard()
        )
    else:
        await query.message.reply_text("❌ هنوز عضو کانال نشده‌اید. لطفاً ابتدا عضو شوید.")

# ====== نمایش راهنما =======
async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        HELP_TEXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("بازگشت", callback_data="main_menu")]
        ])
    )

# ====== بازگشت به منوی اصلی =======
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        HELP_TEXT,
        reply_markup=main_keyboard()
    )

# ====== پشتیبانی =======
async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("⚠️ این بخش فقط برای مدیر ربات فعال است.")
        return
    await update.message.reply_text(SUPPORT_TEXT)
    context.user_data["in_support"] = True

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "in_support" not in context.user_data or not context.user_data["in_support"]:
        return

    message = update.message
    if message.text and message.reply_to_message and message.reply_to_message.from_user.id != OWNER_ID:
        # پیام پاسخ به کاربر
        target_user_id = message.reply_to_message.from_user.id
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=message.text,
                reply_to_message_id=message.reply_to_message.message_id
            )
            await message.reply_text("پیام شما به کاربر ارسال شد.")
        except Exception as e:
            await message.reply_text(f"خطا در ارسال پیام به کاربر: {e}")
    elif message.text == "/لغو":
        context.user_data["in_support"] = False
        await message.reply_text("پشتیبانی لغو شد.")
    else:
        await message.reply_text("برای پاسخ دادن به کاربر، پیام خود را به صورت ریپلای ارسال کنید یا /لغو را بفرستید.")

# ====== مدیریت پیام‌ها =======
@anti_spam
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text or ""

    # چک بن بودن کاربر
    user_data = users_col.find_one({"user_id": user_id})
    if user_data and user_data.get("banned", False):
        await update.message.reply_text("⚠️ شما مسدود شده‌اید و نمی‌توانید از ربات استفاده کنید.")
        return

    # چک عضویت
    joined = await check_joined(user_id, context.bot)
    if not joined:
        # جین اجباری دوباره
        msg = await update.message.reply_text(
            f"⚠️ لطفاً ابتدا عضو کانال {CHANNEL_USERNAME} شوید تا بتوانید از ربات استفاده کنید.",
            reply_markup=join_keyboard()
        )
        context.user_data["join_message_id"] = msg.message_id
        return

    # تشخیص نوع پیام
    link_type = detect_link_type(text)

    if link_type == "instagram":
        dl = insta_download(text)
        if dl:
            await update.message.reply_chat_action(ChatAction.UPLOAD_VIDEO)
            await update.message.reply_video(dl)
        else:
            await update.message.reply_text("❌ خطا در دانلود از اینستاگرام. لینک معتبر ارسال کنید.")
        return

    elif link_type == "spotify":
        dl = spotify_download(text)
        if dl:
            await update.message.reply_chat_action(ChatAction.UPLOAD_AUDIO)
            await update.message.reply_audio(dl)
        else:
            await update.message.reply_text("❌ خطا در دانلود از اسپاتیفای. لینک معتبر ارسال کنید.")
        return

    elif link_type == "pinterest":
        dl = pinterest_download(text)
        if dl:
            await update.message.reply_chat_action(ChatAction.UPLOAD_PHOTO)
            await update.message.reply_photo(dl)
        else:
            await update.message.reply_text("❌ خطا در دانلود از پینترست. لینک معتبر ارسال کنید.")
        return

    elif link_type == "make_image":
        # دستور ساخت عکس
        # متن بعد از "ساخت عکس "
        img_text = text[8:].strip()
        if not img_text:
            await update.message.reply_text("❌ لطفاً متن انگلیسی برای ساخت عکس وارد کنید. مثال: ساخت عکس flower")
            return
        url = make_image(img_text)
        if url:
            await update.message.reply_chat_action(ChatAction.UPLOAD_PHOTO)
            await update.message.reply_photo(url)
        else:
            await update.message.reply_text("
