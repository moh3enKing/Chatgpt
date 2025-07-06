import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import pymongo
import requests
import asyncio

# تنظیمات اصلی
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
OWNER_ID = 5637609683
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"
PORT = int(os.environ.get("PORT", "443"))  # پورت 443 یا از متغیر محیطی بگیر

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# اتصال به دیتابیس
client = pymongo.MongoClient(MONGO_URI)
db = client["botdb"]
users_collection = db["users"]
spam_collection = db["spam"]
support_collection = db["support"]

# وب سرویس های هوش مصنوعی
AI_SERVICES = [
    "https://starsshoptl.ir/Ai/index.php?text={text}",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}",
]

# وب سرویس های دانلودر
DOWNLOADERS = {
    "instagram": "https://pouriam.top/eyephp/instagram?url={url}",
    "spotify": "http://api.cactus-dev.ir/spotify.php?url={url}",
    "pinterest": "https://haji.s2025h.space/pin/?url={url}&client_key=keyvip"
}

# وب سرویس عکس سازی
IMAGE_API = "https://v3.api-free.ir/image/?text={text}"

# پیام راهنما
HELP_TEXT = """
🌟 راهنمای استفاده از ربات هوش مصنوعی 🌟

• برای چت با ربات فقط متن خود را ارسال کنید، بدون نیاز به دستور خاص.
• برای ساخت عکس دستور زیر را به همراه متن انگلیسی ارسال کنید:
   عکس <متن به انگلیسی>
مثال: عکس flower

• برای دریافت فایل از شبکه‌های اجتماعی، فقط لینک مربوطه را ارسال کنید:
   - اینستاگرام (Instagram)
   - اسپاتیفای (Spotify)
   - پینترست (Pinterest)
ربات لینک دانلود مستقیم را برای شما ارسال می‌کند.

⚠️ قوانین و اخطارها:
- احترام به دیگران و استفاده مناسب از ربات الزامی است.
- ارسال پیام‌های تبلیغاتی یا اسپم باعث مسدود شدن شما می‌شود.
- ربات در نسخه اولیه است و ممکن است آپدیت شود.

پشتیبانی: با زدن دکمه "پشتیبانی" می‌توانید مستقیماً با مدیریت در ارتباط باشید.

با تشکر از استفاده شما از ربات ما 🌹
"""

# کیبورد اصلی با دکمه راهنما و پشتیبانی
def main_keyboard():
    buttons = [
        [InlineKeyboardButton("📖 راهنما", callback_data="help")],
        [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")]
    ]
    return InlineKeyboardMarkup(buttons)

# هندلر استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # ثبت کاربر در دیتابیس
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id})
        # اطلاع به ادمین
        await context.bot.send_message(
            OWNER_ID,
            f"کاربر جدید: [{update.effective_user.first_name}](tg://user?id={user_id}) با آیدی `{user_id}` وارد ربات شد.",
            parse_mode="Markdown"
        )

    await update.message.reply_text(
        "سلام! خوش آمدید به ربات هوش مصنوعی.\n\n"
        "متن یا لینک خود را ارسال کنید یا از دکمه‌های زیر استفاده کنید.",
        reply_markup=main_keyboard()
    )

# هندلر پیام‌ها برای چت، دانلود، عکس و ...
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # ضد اسپم: چک پیام‌های اخیر
    user_spam = spam_collection.find_one({"user_id": user_id})
    import datetime
    now = datetime.datetime.utcnow()

    if user_spam:
        messages = user_spam.get("messages", [])
        # حذف پیام‌های قدیمی‌تر از ۲ دقیقه
        messages = [msg for msg in messages if (now - msg).total_seconds() < 120]
        messages.append(now)

        if len(messages) > 4:
            await update.message.reply_text("⏳ لطفا بعد از ۲ دقیقه دوباره پیام ارسال کنید.")
            return
        else:
            spam_collection.update_one({"user_id": user_id}, {"$set": {"messages": messages}})
    else:
        spam_collection.insert_one({"user_id": user_id, "messages": [now]})

    # تشخیص لینک‌های دانلودر
    if any(link in text for link in ["instagram.com", "spotify.com", "pinimg.com", "pinterest.com"]):
        # اینستا
        if "instagram.com" in text:
            await instagram_downloader(update, context, text)
            return
        # اسپاتیفای
        if "spotify.com" in text:
            await spotify_downloader(update, context, text)
            return
        # پینترست
        if "pinimg.com" in text or "pinterest.com" in text:
            await pinterest_downloader(update, context, text)
            return

    # تشخیص دستور ساخت عکس
    if text.startswith("عکس "):
        prompt = text[5:].strip()
        if not prompt:
            await update.message.reply_text("لطفا متن انگلیسی برای ساخت عکس ارسال کنید. مثال: عکس flower")
            return
        await create_image(update, context, prompt)
        return

    # ارسال به وب سرویس چت هوش مصنوعی
    await chat_ai(update, context, text)

# وب سرویس چت هوش مصنوعی با fallback
async def chat_ai(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    for url_template in AI_SERVICES:
        url = url_template.format(text=requests.utils.quote(text))
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.text.strip()
                if data:
                    await update.message.reply_text(data)
                    return
        except Exception:
            continue
    await update.message.reply_text("⚠️ متاسفانه پاسخ دریافت نشد، لطفا بعدا تلاش کنید.")

# اینستاگرام دانلودر
async def instagram_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    api_url = DOWNLOADERS["instagram"].format(url=requests.utils.quote(url))
    try:
        r = requests.get(api_url, timeout=15).json()
        if r.get("links"):
            media_links = r["links"]
            for media_link in media_links:
                # ارسال مستقیم فایل (فیلم یا عکس)
                await update.message.reply_video(media_link) if media_link.endswith(".mp4") else await update.message.reply_photo(media_link)
        else:
            await update.message.reply_text("⚠️ لینک معتبر اینستاگرام پیدا نشد.")
    except Exception:
        await update.message.reply_text("⚠️ خطا در دریافت اطلاعات اینستاگرام.")

# اسپاتیفای دانلودر
async def spotify_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    api_url = DOWNLOADERS["spotify"].format(url=requests.utils.quote(url))
    try:
        r = requests.get(api_url, timeout=15).json()
        if r.get("ok"):
            track = r.get("data", {}).get("track", {})
            mp3_link = track.get("download_url")
            if mp3_link:
                await update.message.reply_audio(mp3_link)
                return
        await update.message.reply_text("⚠️ لینک معتبر اسپاتیفای پیدا نشد یا امکان دانلود نیست.")
    except Exception:
        await update.message.reply_text("⚠️ خطا در دریافت اطلاعات اسپاتیفای.")

# پینترست دانلودر
async def pinterest_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    api_url = DOWNLOADERS["pinterest"].format(url=requests.utils.quote(url))
    try:
        r = requests.get(api_url, timeout=15).json()
        if r.get("status"):
            dl_link = r.get("download_url")
            if dl_link:
                await update.message.reply_photo(dl_link)
                return
        await update.message.reply_text("⚠️ لینک معتبر پینترست پیدا نشد.")
    except Exception:
        await update.message.reply_text("⚠️ خطا در دریافت اطلاعات پینترست.")

# ساخت عکس
async def create_image(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    api_url = IMAGE_API.format(text=requests.utils.quote(prompt))
    try:
        r = requests.get(api_url, timeout=15).json()
        if r.get("ok"):
            img_url = r.get("result")
            await update.message.reply_photo(img_url, caption=f"🎨 تصویر ساخته شده برای: {prompt}")
        else:
            await update.message.reply_text("⚠️ خطا در ساخت تصویر.")
    except Exception:
        await update.message.reply_text("⚠️ خطا در ارتباط با سرویس ساخت تصویر.")

# هندلر دکمه‌های کیبورد
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        await query.edit_message_text(HELP_TEXT, reply_markup=main_keyboard())
    elif query.data == "support":
        user_id = query.from_user.id
        # علامت گذاری کاربر در حالت پشتیبانی
        support_collection.update_one({"user_id": user_id}, {"$set": {"support": True}}, upsert=True)
        await query.edit_message_text(
            "💬 شما در حالت پشتیبانی هستید. پیام خود را ارسال کنید یا /cancel را بزنید برای خروج.",
            reply_markup=None
        )
    else:
        await query.answer("دستور نامشخص.")

# هندلر پیام پشتیبانی (ارسال پیام از کاربر به ادمین و بالعکس)
async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sup = support_collection.find_one({"user_id": user_id})

    if sup and sup.get("support"):
        # پیام از کاربر به ادمین
        await context.bot.send_message(
            OWNER_ID,
            f"💬 پیام پشتیبانی از [{update.effective_user.first_name}](tg://user?id={user_id}):\n{update.message.text}",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ پیام شما به مدیریت ارسال شد.")
    elif user_id == OWNER_ID and update.message.reply_to_message:
        # پیام از ادمین به کاربر (ریپلای)
        original_text = update.message.reply_to_message.text_markdown_v2 or ""
        await context.bot.send_message(
            int(update.message.reply_to_message.from_user.id),
            f"📩 پاسخ مدیریت:\n{update.message.text}"
        )

# لغو پشتیبانی
async def cancel_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    support_collection.update_one({"user_id": user_id}, {"$set": {"support": False}}, upsert=True)
    await update.message.reply_text("✅ شما از حالت پشتیبانی خارج شدید.", reply_markup=main_keyboard())

# تابع اصلی اجرای ربات و وبهوک
async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("cancel", cancel_support))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), support_message))

    await application.start()
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )
    await application.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())
