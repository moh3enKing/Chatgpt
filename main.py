import logging
import datetime
from flask import Flask, request
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import aiohttp
from pymongo import MongoClient

# ====== تنظیمات ======
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"
PORT = 10000

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

# اتصال به دیتابیس MongoDB
client = MongoClient(MONGO_URI)
db = client["botdb"]
users_col = db["users"]
support_col = db["support"]
messages_col = db["messages"]

# کیبورد پشتیبانی (برای پیوی)
def support_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🛠️ پشتیبانی"), KeyboardButton("❌ لغو پشتیبانی")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

# کیبورد خوش آمد و راهنما (دکمه‌های شیشه‌ای)
def welcome_inline_keyboard():
    buttons = [
        [InlineKeyboardButton("📖 راهنما", callback_data="help")],
        [InlineKeyboardButton("🛠️ پشتیبانی", callback_data="support")],
    ]
    return InlineKeyboardMarkup(buttons)

# متن خوش آمد
WELCOME_TEXT = (
    "سلام {}!\n"
    "به ربات هوش مصنوعی خوش آمدید.\n"
    "برای استفاده از ربات دکمه‌های زیر را ببینید."
)

# متن راهنما رسمی و جامع
HELP_TEXT = (
    "📚 راهنمای استفاده از ربات هوش مصنوعی:\n\n"
    "۱. چت: کافیست پیام متنی خود را ارسال کنید تا ربات پاسخ دهد.\n"
    "۲. ساخت تصویر: با ارسال پیام به شکل:\n"
    "   عکس متن_انگلیسی\n"
    "   یک تصویر ساخته و ارسال خواهد شد. (متن باید انگلیسی باشد)\n"
    "۳. دانلود محتوا:\n"
    "   - اینستاگرام: لینک پست یا ویدئو ارسال کنید.\n"
    "   - اسپاتیفای: لینک ترک موسیقی ارسال کنید.\n"
    "   - پینترست: لینک تصویر ارسال کنید.\n"
    "۴. پشتیبانی: با کلیک روی دکمه پشتیبانی پیام خود را به مدیر ارسال کنید.\n\n"
    "⚠️ قوانین ربات:\n"
    "- لطفا از ارسال پیام‌های اسپم خودداری کنید.\n"
    "- پیام‌های نامناسب باعث بلاک شدن خواهند شد.\n\n"
    "ربات در نسخه اولیه است و در حال به‌روزرسانی می‌باشد."
)

THANKS_TEXT = (
    "ممنون که ربات ما را انتخاب کردید.\n"
    "اگر سوال یا مشکلی داشتید، با دکمه پشتیبانی در ارتباط باشید."
)

# --- هندلر استارت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not users_col.find_one({"user_id": user.id}):
        users_col.insert_one({"user_id": user.id})
        await application.bot.send_message(
            OWNER_ID, f"کاربر جدید:\n{user.full_name} ({user.id})"
        )

    # ارسال پیام خوش آمد با دکمه‌های شیشه‌ای
    await update.message.reply_text(
        WELCOME_TEXT.format(user.first_name),
        reply_markup=welcome_inline_keyboard(),
    )

# --- هندلر دکمه‌ها ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "help":
        await query.message.edit_text(
            HELP_TEXT,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت", callback_data="back")]])
        )
    elif data == "back":
        # وقتی برگشت داده شد متن تشکر نمایش داده شود و دکمه راهنما زیرش باشد
        await query.message.edit_text(
            THANKS_TEXT,
            reply_markup=welcome_inline_keyboard()
        )
    elif data == "support":
        # فعال کردن حالت پشتیبانی برای کاربر
        support_col.update_one(
            {"user_id": query.from_user.id}, {"$set": {"supporting": True}}, upsert=True
        )
        await query.message.edit_text(
            "حالا پیام خود را ارسال کنید تا برای مدیر فرستاده شود.\n"
            "برای لغو پشتیبانی دستور ❌ لغو پشتیبانی را ارسال کنید."
        )
    else:
        await query.message.edit_text("دستور نامعتبر است.")

# --- هندلر پیام متنی ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    # ضد اسپم: بررسی 4 پیام اخیر در 2 دقیقه
    now = datetime.datetime.utcnow()
    recent_msgs = list(messages_col.find({"user_id": user.id}).sort("date", -1).limit(4))
    if len(recent_msgs) == 4:
        diff = (now - recent_msgs[-1]["date"]).total_seconds()
        if diff <= 120:
            await update.message.reply_text("شما پیام‌های زیادی ارسال کردید، لطفاً ۲ دقیقه صبر کنید.")
            return
    messages_col.insert_one({"user_id": user.id, "text": text, "date": now})

    # بررسی وضعیت پشتیبانی
    support_data = support_col.find_one({"user_id": user.id})
    if support_data and support_data.get("supporting"):
        # ارسال پیام به مدیر
        try:
            sent_msg = await application.bot.send_message(
                OWNER_ID,
                f"پیام پشتیبانی از {user.full_name} ({user.id}):\n{text}"
            )
            # ذخیره شناسه پیام برای ریپلای بعدی
            support_col.update_one(
                {"user_id": user.id},
                {"$set": {"last_msg_id": sent_msg.message_id}}
            )
            await update.message.reply_text("پیام شما برای مدیر ارسال شد.")
        except Exception as e:
            await update.message.reply_text("خطایی رخ داد، لطفا بعداً تلاش کنید.")
        return

    # اگر پیام پشتیبانی نبود پردازش معمولی
    if text.startswith("عکس "):
        prompt = text[5:].strip()
        await generate_image(update, prompt)
    elif "instagram.com" in text:
        await download_instagram(update, text)
    elif "spotify.com" in text:
        await download_spotify(update, text)
    elif "pin.it" in text or "pinterest.com" in text:
        await download_pinterest(update, text)
    else:
        await chat_ai(update, text)

# --- لغو پشتیبانی ---
async def cancel_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    support_col.update_one({"user_id": user.id}, {"$set": {"supporting": False}})
    await update.message.reply_text("از حالت پشتیبانی خارج شدید.", reply_markup=support_keyboard())

# --- وب سرویس‌ها ---

async def generate_image(update: Update, prompt: str):
    url = f"https://v3.api-free.ir/image/?text={prompt}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("ok"):
                    await update.message.reply_photo(photo=data["result"])
                    return
    await update.message.reply_text("مشکلی در ساخت تصویر رخ داد.")

async def download_instagram(update: Update, url: str):
    api_url = f"https://pouriam.top/eyephp/instagram?url={url}"
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            if resp.status == 200:
                data = await resp.json()
                links = data.get("links")
                if links and len(links) > 0:
                    await update.message.reply_video(video=links[0])
                    return
    await update.message.reply_text("مشکلی در دانلود اینستاگرام رخ داد.")

async def download_spotify(update: Update, url: str):
    api_url = f"http://api.cactus-dev.ir/spotify.php?url={url}"
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("ok"):
                    track = data.get("data", {}).get("track", {})
                    if track.get("download_url"):
                        await update.message.reply_audio(audio=track["download_url"], caption=track.get("name", ""))
                        return
    await update.message.reply_text("مشکلی در دانلود اسپاتیفای رخ داد.")

async def download_pinterest(update: Update, url: str):
    api_url = f"https://haji.s2025h.space/pin/?url={url}"
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("
