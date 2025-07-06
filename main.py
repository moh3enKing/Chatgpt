import logging
import time
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# تنظیمات
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"

# اتصال به دیتابیس
client = MongoClient(MONGO_URI)
db = client["botdb"]
users = db["users"]

# ثبت زمان ارسال پیام کاربران
user_spam = {}

logging.basicConfig(level=logging.INFO)

# متن راهنما
HELP_TEXT = """
🎉 به ربات هوش مصنوعی ما خوش آمدید 🎉

🤖 این ربات در نسخه اولیه است و به‌مرور زمان امکانات بیشتری اضافه می‌شود. ممنون از صبر و همراهی شما.

📌 امکانات ربات:
▪️ چت با هوش مصنوعی (فقط کافیست پیام بفرستید)
▪️ ساخت تصویر (دستور: `عکس متن‌انگلیسی`)
▪️ دانلود:
   - اینستاگرام (لینک بده)
   - اسپاتیفای (لینک بده)
   - پینترست (لینک بده)

📛 قوانین:
▪️ ارسال پیام اسپم = سکوت ۲ دقیقه
▪️ رعایت احترام به دیگران
▪️ لینک‌های ناشناس یا غیرمجاز بررسی نمی‌شوند

🛟 پشتیبانی مستقیم در دسترس است (دکمه پایین)

⚠️ برای ساخت عکس لطفاً متن انگلیسی ارسال کنید
"""

# دکمه‌ها
def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📄 راهنما"), KeyboardButton("🛠 پشتیبانی")]
    ], resize_keyboard=True)

# چک عضویت
async def check_join(update: Update):
    member = await update.get_bot().get_chat_member(f"@{CHANNEL_USERNAME}", update.effective_user.id)
    return member.status in ["member", "creator", "administrator"]

# شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_join(update):
        await update.message.reply_text("برای استفاده از ربات ابتدا عضو کانال شوید:\n@" + CHANNEL_USERNAME)
        return
    if not users.find_one({"user_id": update.effective_user.id}):
        users.insert_one({"user_id": update.effective_user.id, "time": time.time()})
        await context.bot.send_message(OWNER_ID, f"کاربر جدید استارت زد: {update.effective_user.full_name} ({update.effective_user.id})")
    await update.message.reply_text("✅ خوش آمدید!\nبرای آشنایی با امکانات ربات دکمه راهنما را بزنید.", reply_markup=main_keyboard())

# راهنما
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, reply_markup=main_keyboard())

# پشتیبانی
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("پیام خود را ارسال کنید، پشتیبانی فعال شد. برای لغو `لغو` را ارسال کنید.")
    context.user_data["support"] = True

# پیام‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    # ضد اسپم
    t = time.time()
    if uid not in user_spam:
        user_spam[uid] = []
    user_spam[uid] = [msg for msg in user_spam[uid] if t - msg < 120]
    user_spam[uid].append(t)
    if len(user_spam[uid]) > 4:
        await update.message.reply_text("⏳ به دلیل ارسال زیاد، لطفاً ۲ دقیقه صبر کنید.")
        return

    # چک عضویت
    if not await check_join(update):
        await update.message.reply_text("برای استفاده از ربات ابتدا عضو کانال شوید:\n@" + CHANNEL_USERNAME)
        return

    # پشتیبانی فعال
    if context.user_data.get("support"):
        if text.lower() == "لغو":
            context.user_data["support"] = False
            await update.message.reply_text("پشتیبانی غیرفعال شد.", reply_markup=main_keyboard())
        else:
            await context.bot.send_message(OWNER_ID, f"پیام از {uid}:\n{text}")
            await update.message.reply_text("پیام شما به پشتیبانی ارسال شد.")
        return

    # دستورات
    if text == "📄 راهنما":
        await update.message.reply_text(HELP_TEXT, reply_markup=main_keyboard())
    elif text == "🛠 پشتیبانی":
        await support(update, context)
    elif text.startswith("عکس "):
        query = text[5:]
        if not query.isascii():
            await update.message.reply_text("لطفاً متن انگلیسی برای ساخت عکس وارد کنید.")
            return
        res = requests.get(f"https://v3.api-free.ir/image/?text={query}").json()
        if res.get("ok"):
            await update.message.reply_photo(res["result"])
        else:
            await update.message.reply_text("خطا در ساخت تصویر.")
    else:
        await chat_with_ai(update, context, text)

# چت با هوش مصنوعی
async def chat_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    urls = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=10)
            if res.ok:
                await update.message.reply_text(res.text)
                return
        except:
            continue
    await update.message.reply_text("خطا در دریافت پاسخ از سرور.")

# لینک دانلود
async def downloader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "instagram.com" in text:
        try:
            res = requests.get(f"https://pouriam.top/eyephp/instagram?url={text}").json()
            if res["links"]:
                for link in res["links"]:
                    if ".mp4" in link:
                        await update.message.reply_video(link)
                    else:
                        await update.message.reply_photo(link)
            else:
                await update.message.reply_text("خطا در دریافت محتوا.")
        except:
            await update.message.reply_text("خطا در پردازش لینک اینستاگرام.")
    elif "spotify.com" in text:
        try:
            res = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={text}").json()
            if res["ok"]:
                await update.message.reply_audio(res["data"]["download_url"], title=res["data"]["name"])
            else:
                await update.message.reply_text("خطا در دریافت فایل اسپاتیفای.")
        except:
            await update.message.reply_text("خطا در پردازش لینک اسپاتیفای.")
    elif "pin" in text:
        try:
            res = requests.get(f"https://haji.s2025h.space/pin/?url={text}&client_key=keyvip").json()
            if res["status"]:
                await update.message.reply_photo(res["download_url"])
            else:
                await update.message.reply_text("خطا در دریافت تصویر.")
        except:
            await update.message.reply_text("خطا در پردازش لینک پینترست.")
    else:
        await update.message.reply_text("لینک نامعتبر است یا پشتیبانی نمی‌شود.")

# اجرای ربات
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, downloader))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_webhook(listen="0.0.0.0", port=10000, webhook_url=WEBHOOK_URL)
