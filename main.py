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

BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
OWNER_ID = 5637609683
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"
PORT = int(os.environ.get("PORT", "443"))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

client = pymongo.MongoClient(MONGO_URI)
db = client["botdb"]
users_collection = db["users"]
spam_collection = db["spam"]
support_collection = db["support"]

AI_SERVICES = [
    "https://starsshoptl.ir/Ai/index.php?text={text}",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}",
]

DOWNLOADERS = {
    "instagram": "https://pouriam.top/eyephp/instagram?url={url}",
    "spotify": "http://api.cactus-dev.ir/spotify.php?url={url}",
    "pinterest": "https://haji.s2025h.space/pin/?url={url}&client_key=keyvip"
}

IMAGE_API = "https://v3.api-free.ir/image/?text={text}"

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

def main_keyboard():
    buttons = [
        [InlineKeyboardButton("📖 راهنما", callback_data="help")],
        [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")]
    ]
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id})
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (همون کد قبلی handle_message بدون تغییر)
    pass

async def chat_ai(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    # ... (مثل قبل)
    pass

async def instagram_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    # ... (مثل قبل)
    pass

async def spotify_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    # ... (مثل قبل)
    pass

async def pinterest_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    # ... (مثل قبل)
    pass

async def create_image(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    # ... (مثل قبل)
    pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (مثل قبل)
    pass

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (مثل قبل)
    pass

async def cancel_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    support_collection.update_one({"user_id": user_id}, {"$set": {"support": False}}, upsert=True)
    await update.message.reply_text("✅ شما از حالت پشتیبانی خارج شدید.", reply_markup=main_keyboard())

async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("cancel", cancel_support))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), support_message))

    await application.initialize()  # <== اضافه شده این خط
    await application.start()
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )
    await application.updater.idle()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
