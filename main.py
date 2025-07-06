# main.py
import logging
import asyncio
import threading
import re
import json
import aiohttp
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------- تنظیمات اولیه ----------
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
CHANNEL_USERNAME = "@netgoris"
OWNER_ID = 5637609683
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

PORT = 10000

# --------- راه‌اندازی لاگ ----------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- اپلیکیشن Flask ----------
app = Flask(__name__)
bot_app = None  # اینجا اپلیکیشن تلگرام ذخیره میشه


# ---------- کمک‌کننده‌ها ----------

def is_instagram_link(text):
    return "instagram.com" in text

def is_spotify_link(text):
    return "spotify.com" in text

def is_pinterest_link(text):
    return "pin.it" in text or "pinterest.com" in text

def is_image_command(text):
    return text.startswith("عکس ")

# --------- متغیرهای ضد اسپم ----------
# کلید: user_id ، مقدار: [timestamp پیام‌ها]
spam_tracker = {}

# ---------- پیام خوش آمد ----------
WELCOME_MESSAGE = """سلام دوست عزیز 👋

به ربات هوش مصنوعی خوش آمدید!

شما می‌توانید از امکانات زیر استفاده کنید:
- چت با هوش مصنوعی
- دریافت محتوا از اینستاگرام، اسپاتیفای و پینترست
- ساخت تصویر با دستور 'عکس متن مورد نظر'

لطفاً قوانین را رعایت کنید تا ربات برای شما همیشه فعال بماند.

برای مشاهده راهنما دکمه راهنما را بزنید.
"""

# ---------- متن راهنما ----------
HELP_TEXT = """
راهنمای استفاده از ربات:

۱. برای چت با ربات کافی است پیام خود را ارسال کنید.
۲. برای ساخت عکس، پیام خود را با کلمه 'عکس' شروع کنید، مثلاً:
   عکس گل زیبا
   (توجه: متن برای ساخت عکس باید به انگلیسی باشد)
۳. ارسال لینک‌های اینستاگرام، اسپاتیفای یا پینترست را به ربات بدهید تا محتوا را دریافت کنید.
۴. اگر لینک ارسالی مربوط به موارد بالا نبود، ربات اطلاع خواهد داد.
۵. برای درخواست پشتیبانی، دکمه «پشتیبانی» را در صفحه شخصی خود استفاده کنید.

⚠️ قوانین ربات:
- ارسال پیام‌های بی‌مورد و اسپم ممنوع است.
- در صورت ارسال بیش از ۴ پیام در ۲ دقیقه، ربات به مدت ۲ دقیقه پاسخ نخواهد داد.
- رعایت ادب و احترام الزامی است.

ربات در نسخه اولیه است و در حال به‌روزرسانی می‌باشد.

موفق باشید!
"""

# ---------- متن تشکر پس از راهنما ----------
THANKS_TEXT = "ممنون که ربات ما را انتخاب کردید. امیدواریم از امکانات آن لذت ببرید.\nمشکلی داشتید از طریق پشتیبانی اطلاع دهید."

# ---------- کلیدهای شیشه‌ای ----------
def get_start_keyboard():
    keyboard = [
        [InlineKeyboardButton("راهنما", callback_data="help")],
        [InlineKeyboardButton("پشتیبانی", callback_data="support_start")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_support_close_keyboard():
    keyboard = [
        [InlineKeyboardButton("لغو پشتیبانی", callback_data="support_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------- دیتابیس موقتی در رم (برای نمونه) ----------
users_state = {}  # user_id : dict { 'joined': bool, 'in_support': bool, 'support_chat_id': int, 'show_welcome': bool, 'in_help': bool, 'help_seen': bool }

# ---------- وب‌سرویس‌ها ----------
CHAT_SERVICES = [
    "https://starsshoptl.ir/Ai/index.php?text=",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text=",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text=",
]

INSTAGRAM_API = "https://pouriam.top/eyephp/instagram?url="
SPOTIFY_API = "http://api.cactus-dev.ir/spotify.php?url="
PINTEREST_API = "https://haji.s2025h.space/pin/?url={}&client_key=keyvip"
IMAGE_API = "https://v3.api-free.ir/image/?text="

# ---------- چک اسپم ----------
import time

def is_spamming(user_id):
    now = time.time()
    timestamps = spam_tracker.get(user_id, [])
    timestamps = [t for t in timestamps if now - t < 120]  # ۲ دقیقه اخیر
    spam_tracker[user_id] = timestamps

    if len(timestamps) >= 4:
        return True
    else:
        spam_tracker[user_id].append(now)
        return False

# ---------- فراخوانی وب‌سرویس چت با fallback ----------
async def call_chat_services(text):
    async with aiohttp.ClientSession() as session:
        for url_base in CHAT_SERVICES:
            try:
                url = url_base + aiohttp.helpers.quote(text)
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.text()
                        if data:
                            return data
            except:
                continue
    return "متأسفانه پاسخگو نبودم، لطفا دوباره تلاش کنید."

# ---------- فراخوانی وب‌سرویس‌های دانلود ----------
async def fetch_instagram_links(url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(INSTAGRAM_API + url, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("links", [])
        except:
            return []

async def fetch_spotify_mp3(url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(SPOTIFY_API + url, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        return data["data"]["track"]["download_url"]
        except:
            return None

async def fetch_pinterest_image(url):
    async with aiohttp.ClientSession() as session:
        try:
            api_url = PINTEREST_API.format(url)
            async with session.get(api_url, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status"):
                        return data.get("download_url")
        except:
            return None

async def fetch_generated_image(text):
    async with aiohttp.ClientSession() as session:
        try:
            url = IMAGE_API + aiohttp.helpers.quote(text)
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        return data.get("result")
        except:
            return None

# ---------- هندلرها ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users_state.setdefault(user_id, {
        "joined": True,  # چون کانال حذف شد، فرض می‌کنیم عضو هستند
        "in_support": False,
        "support_chat_id": None,
        "show_welcome": True,
        "in_help": False,
        "help_seen": False
    })

    # پیام به ادمین اگر اولین بار استارت زد
    if users_state[user_id]["show_welcome"]:
        await context.bot.send_message(OWNER_ID, f"👤 کاربر جدید: @{update.effective_user.username or 'ناشناس'} ({user_id}) استارت زد.")
        await update.message.reply_text(WELCOME_MESSAGE, reply_markup=get_start_keyboard())
        users_state[user_id]["show_welcome"] = False
    else:
        # اگر قبلاً خوش آمد گفتیم فقط پیام اصلی را بفرست
        await update.message.reply_text(THANKS_TEXT, reply_markup=get_start_keyboard())

async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if users_state.get(user_id, {}).get("in_help"):
        # در صفحه تشکر هستیم، بازگشت نداریم
        await query.edit_message_text(text=THANKS_TEXT, reply_markup=get_start_keyboard())
        users_state[user_id]["in_help"] = False
        users_state[user_id]["help_seen"] = True
        return

    # نمایش متن راهنما
    await query.edit_message_text(text=HELP_TEXT, reply_markup=get_start_keyboard())
    users_state[user_id]["in_help"] = True

async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users_state.setdefault(user_id, {
        "joined": True,
        "in_support": False,
        "support_chat_id": None,
        "show_welcome": False,
        "in_help": False,
        "help_seen": False
    })

    if users_state[user_id]["in_support"]:
        await update.message.reply_text("شما در حال حاضر در بخش پشتیبانی هستید.")
        return

    users_state[user_id]["in_support"] = True
    await update.message.reply_text("لطفا پیام خود را برای پشتیبانی ارسال کنید. برای لغو، دکمه زیر را بزنید.",
                                    reply_markup=get_support_close_keyboard())

async def support_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if users_state.get(user_id):
        users_state[user_id]["in_support"] = False
    await query.answer("پشتیبانی لغو شد.")
    await query.edit_message_text("پشتیبانی لغو شد.", reply_markup=get_start_keyboard())

async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not users_state.get(user_id, {}).get("in_support", False):
        return

    # پیام را به ادمین فوروارد کن
    text = update.message.text
    await context.bot.send_message(OWNER_ID, f"پیام از @{update.effective_user.username or 'ناشناس'} ({user_id}):\n{text}")

    await update.message.reply_text("پیام شما به پشتیبانی ارسال شد. منتظر پاسخ باشید.")
    users_state[user_id]["in_support"] = False

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # اسپم چک
    if is_spamming(user_id):
        await update.message.reply_text("⏳ لطفا کمی صبر کنید، ارسال پیام‌های زیاد ممنوع است.")
        return

    # پشتیبانی
    if users_state.get(user_id, {}).get("in_support", False):
        # ارسال پیام به ادمین
        await handle_support_message(update, context)
        return

    # لینک‌ها
    if is_instagram_link(text):
        links = await fetch_instagram_links(text)
        if links:
            # ارسال لینک مستقیم (اولین لینک)
            await update.message.reply_video(links[0])
        else:
            await update.message.reply_text("خطا در دریافت اطلاعات اینستاگرام.")
        return

    elif is_spotify_link(text):
        mp3_url = await fetch_spotify_mp3(text)
        if mp3_url:
            await update.message.reply_audio(mp3_url)
        else:
            await update.message.reply_text("خطا در دریافت اطلاعات اسپاتیفای.")
        return

    elif is_pinterest_link(text):
        img_url = await fetch_pinterest_image(text)
        if img_url:
            await update.message.reply_photo(img_url)
        else:
            await update.message.reply_text("خطا در دریافت اطلاعات پینترست.")
        return

    elif is_image_command(text):
        # گرفتن متن پس از "عکس "
        prompt = text[5:].strip()
        if not prompt:
            await update.message.reply_text("لطفا متن انگلیسی برای ساخت عکس وارد کنید. مثال: عکس flower")
            return
        img_url = await fetch_generated
