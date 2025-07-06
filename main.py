import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import pymongo
import requests

# تنظیمات
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"

PORT = int(os.environ.get("PORT", "1000"))

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

# سرویس های چت هوش مصنوعی
AI_SERVICES = [
    "https://starsshoptl.ir/Ai/index.php?text={text}",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}",
]

# سرویس های دانلودر
DOWNLOADERS = {
    "instagram": "https://pouriam.top/eyephp/instagram?url={url}",
    "spotify": "http://api.cactus-dev.ir/spotify.php?url={url}",
    "pinterest": "https://haji.s2025h.space/pin/?url={url}&client_key=keyvip"
}

# API ساخت عکس
IMAGE_API = "https://v3.api-free.ir/image/?text={text}"

# متن راهنما
HELP_TEXT = """
🌟 راهنمای استفاده از ربات هوش مصنوعی 🌟

• برای چت با ربات فقط متن خود را ارسال کنید.
• برای ساخت عکس دستور زیر را ارسال کنید:
   عکس <متن به انگلیسی>
مثال: عکس flower

• برای دریافت فایل از شبکه‌های اجتماعی فقط لینک مربوطه را ارسال کنید:
   - اینستاگرام (Instagram)
   - اسپاتیفای (Spotify)
   - پینترست (Pinterest)
ربات لینک دانلود مستقیم را ارسال خواهد کرد.

⚠️ قوانین و اخطارها:
- احترام به دیگر کاربران الزامی است.
- ارسال پیام‌های تبلیغاتی یا اسپم باعث مسدودیت خواهد شد.
- ربات در نسخه اولیه است و در حال آپدیت می‌باشد.

📞 برای ارتباط با مدیریت دکمه "پشتیبانی" را بزنید.

با تشکر از شما 🌹
"""

# ساختار کیبورد اصلی
def main_keyboard():
    buttons = [
        [InlineKeyboardButton("📖 راهنما", callback_data="help")],
        [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")]
    ]
    return InlineKeyboardMarkup(buttons)

# تابع استارت
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

# بررسی اسپم: ۴ پیام پشت سر هم در ۲ دقیقه
async def check_spam(user_id):
    import time
    now = time.time()
    records = list(spam_collection.find({"user_id": user_id}))
    records = [r for r in records if now - r["time"] < 120]
    if len(records) >= 4:
        return True
    spam_collection.insert_one({"user_id": user_id, "time": now})
    return False

# ارسال درخواست به سرویس AI به ترتیب (fallback)
def get_ai_response(text):
    for url_template in AI_SERVICES:
        try:
            url = url_template.format(text=text)
            res = requests.get(url, timeout=8)
            if res.status_code == 200:
                data = res.text
                if data and len(data) > 0:
                    return data
        except:
            continue
    return None

# دانلودرها

def get_instagram_links(url):
    try:
        r = requests.get(DOWNLOADERS["instagram"].format(url=url), timeout=10)
        if r.status_code == 200:
            data = r.json()
            if "links" in data and data["links"]:
                return data["links"]
    except:
        pass
    return None

def get_spotify_link(url):
    try:
        r = requests.get(DOWNLOADERS["spotify"].format(url=url), timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("ok") and data.get("data") and data["data"].get("track"):
                return data["data"]["track"].get("download_url")
    except:
        pass
    return None

def get_pinterest_link(url):
    try:
        r = requests.get(DOWNLOADERS["pinterest"].format(url=url), timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") and data.get("download_url"):
                return data["download_url"]
    except:
        pass
    return None

# ساخت عکس
def get_image_link(text):
    try:
        r = requests.get(IMAGE_API.format(text=text), timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("ok") and data.get("result"):
                return data["result"]
    except:
        pass
    return None

# هندلر پیامها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # اسپم چک
    if await check_spam(user_id):
        await update.message.reply_text("⚠️ شما پیام‌های زیادی ارسال کرده‌اید. لطفاً ۲ دقیقه صبر کنید.")
        return

    # پشتیبانی فعال؟
    support = support_collection.find_one({"user_id": user_id, "support": True})
    if support:
        # ارسال پیام به مدیریت و نمایش ریپلای
        await context.bot.send_message(
            OWNER_ID,
            f"پیام پشتیبانی از [{update.effective_user.first_name}](tg://user?id={user_id}):\n\n{text}",
            parse_mode="Markdown"
        )
        await update.message.reply_text("پیام شما به مدیریت ارسال شد. لطفاً صبر کنید.", reply_markup=None)
        return

    # دستور ساخت عکس
    if text.startswith("عکس "):
        prompt = text[5:].strip()
        if not prompt:
            await update.message.reply_text("لطفاً متن انگلیسی برای ساخت عکس ارسال کنید.\nمثال: عکس flower")
            return
        img_link = get_image_link(prompt)
        if img_link:
            await update.message.reply_photo(img_link)
        else:
            await update.message.reply_text("متاسفانه ساخت عکس انجام نشد. دوباره تلاش کنید.")
        return

    # تشخیص لینکها
    if "instagram.com" in text:
        links = get_instagram_links(text)
        if links:
            for link in links:
                await update.message.reply_video(link)
        else:
            await update.message.reply_text("خطا در دریافت اطلاعات اینستاگرام. لطفا لینک را بررسی کنید.")
        return

    if "spotify.com" in text:
        link = get_spotify_link(text)
        if link:
            await update.message.reply_audio(link)
        else:
            await update.message.reply_text("خطا در دریافت اطلاعات اسپاتیفای. لطفا لینک را بررسی کنید.")
        return

    if "pin.it" in text or "pinterest.com" in text:
        link = get_pinterest_link(text)
        if link:
            await update.message.reply_photo(link)
        else:
            await update.message.reply_text("خطا در دریافت اطلاعات پینترست. لطفا لینک را بررسی کنید.")
        return

    # بقیه پیام‌ها => ارسال به هوش مصنوعی
    ai_response = get_ai_response(text)
    if ai_response:
        await update.message.reply_text(ai_response)
    else:
        await update.message.reply_text("متاسفانه ربات در پاسخ به سوال شما دچار مشکل شد. دوباره تلاش کنید.")

# هندلر دکمه‌ها
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        await query.edit_message_text(HELP_TEXT, reply_markup=main_keyboard())
    elif query.data == "support":
        user_id = query.from_user.id
        support_collection.update_one({"user_id": user_id}, {"$set": {"support": True}}, upsert=True)
        await query.edit_message_text("حالت پشتیبانی فعال شد.\nپیام خود را ارسال کنید یا /cancel برای خروج از پشتیبانی را بزنید.")
    else:
        await query.edit_message_text("دستور ناشناخته.")

# لغو پشتیبانی
async def cancel_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    support_collection.update_one({"user_id": user_id}, {"$set": {"support": False}}, upsert=True)
    await update.message.reply_text("✅ شما از حالت پشتیبانی خارج شدید.", reply_markup=main_keyboard())

# فانکشن اصلی
async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("cancel", cancel_support))

    await application.initialize()
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
