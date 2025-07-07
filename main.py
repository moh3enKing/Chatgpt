import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import aiohttp
from pymongo import MongoClient

BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

client = MongoClient(MONGO_URI)
db = client['bot']
users_col = db['users']
support_col = db['support']

# --- HELPER FUNCTIONS ---

async def send_owner_message(text):
    try:
        await application.bot.send_message(OWNER_ID, text)
    except Exception as e:
        logging.error(f"Error sending owner message: {e}")

async def send_help_message(update: Update):
    keyboard = [
        [InlineKeyboardButton("⬅️ بازگشت", callback_data="back")]
    ]
    help_text = (
        "راهنمای ربات هوش مصنوعی:\n\n"
        "1. برای چت با ربات کافی است پیام متنی خود را ارسال کنید.\n"
        "2. برای ساخت تصویر با دستور `عکس متن_انگلیسی` پیام دهید.\n"
        "3. برای دانلود از اینستاگرام، اسپاتیفای و پینترست، فقط لینک مستقیم بفرستید.\n"
        "   - اینستاگرام: لینک پست یا ویدیو\n"
        "   - اسپاتیفای: لینک ترک موسیقی\n"
        "   - پینترست: لینک تصویر\n"
        "4. دکمه 'پشتیبانی' را برای ارسال پیام به مدیر استفاده کنید.\n\n"
        "⚠️ لطفاً قوانین ربات را رعایت کنید:\n"
        "- ارسال پیام‌های اسپم ممنوع است.\n"
        "- توهین یا پیام‌های نامناسب باعث بلاک شدن خواهد شد.\n\n"
        "این ربات در نسخه اولیه خود است و به زودی آپدیت می‌شود."
    )
    await update.callback_query.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def send_welcome_message(update: Update):
    keyboard = [
        [InlineKeyboardButton("📖 راهنما", callback_data="help")],
        [InlineKeyboardButton("🛠️ پشتیبانی", callback_data="support")]
    ]
    welcome_text = (
        f"سلام {update.effective_user.first_name}!\n"
        "به ربات هوش مصنوعی خوش آمدید.\n"
        "برای مشاهده راهنما روی دکمه زیر کلیک کنید."
    )
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))

# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not users_col.find_one({"user_id": user.id}):
        users_col.insert_one({"user_id": user.id})
        await send_owner_message(f"کاربر جدید: {user.full_name} - {user.id}")
    await send_welcome_message(update)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "help":
        await send_help_message(update)
    elif data == "back":
        keyboard = [
            [InlineKeyboardButton("📖 راهنما", callback_data="help")],
            [InlineKeyboardButton("🛠️ پشتیبانی", callback_data="support")]
        ]
        text = "ممنون که ربات ما را انتخاب کردید."
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "support":
        support_col.update_one(
            {"user_id": query.from_user.id},
            {"$set": {"support": True}},
            upsert=True
        )
        await query.message.edit_text(
            "حالا پیام خود را ارسال کنید، پیام شما به مدیر فرستاده می‌شود.\n"
            "برای خروج از پشتیبانی دستور /cancel را ارسال کنید."
        )
    else:
        await query.message.edit_text("دستور ناشناخته.")

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    support_data = support_col.find_one({"user_id": user.id})
    if support_data and support_data.get("support", False):
        # ارسال پیام به ادمین
        text = f"پیام پشتیبانی از {user.full_name} ({user.id}):\n{update.message.text}"
        sent = await application.bot.send_message(OWNER_ID, text)
        # ذخیره شناسه پیام برای ریپلای بعدی ادمین به کاربر (می‌توان دیتابیس افزود)
        support_col.update_one({"user_id": user.id}, {"$set": {"last_msg_id": sent.message_id}})
        await update.message.reply_text("پیام شما برای مدیر ارسال شد.")
    else:
        # اگر در حالت پشتیبانی نبود پیام را نادیده بگیر یا پردازش عادی کن
        pass

async def cancel_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    support_col.update_one({"user_id": user.id}, {"$set": {"support": False}})
    await update.message.reply_text("از حالت پشتیبانی خارج شدید.")

# --- پیام های متنی (چت و دانلود) ---

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    # ضد اسپم: اگر کاربر 4 پیام پشت سر هم در 2 دقیقه داده، سکوت کن
    recent_msgs = list(db['messages'].find({"user_id": user.id}).sort("date",-1).limit(4))
    if len(recent_msgs) == 4:
        import datetime
        now = datetime.datetime.utcnow()
        times = [m['date'] for m in recent_msgs]
        diff = (now - times[-1]).total_seconds()
        if diff <= 120:
            await update.message.reply_text("شما پیام‌های زیادی ارسال کردید، لطفا دو دقیقه صبر کنید.")
            return
    db['messages'].insert_one({"user_id": user.id, "text": text, "date": datetime.datetime.utcnow()})

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

# --- وب سرویس ها ---

async def generate_image(update: Update, prompt: str):
    # توجه: متن باید انگلیسی باشد
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
    api = "https://pouriam.top/eyephp/instagram?url="
    await download_media(update, api + url)

async def download_spotify(update: Update, url: str):
    api = "http://api.cactus-dev.ir/spotify.php?url="
    async with aiohttp.ClientSession() as session:
        async with session.get(api + url) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("ok"):
                    track = data.get("data", {}).get("track", {})
                    if track.get("download_url"):
                        await update.message.reply_audio(audio=track["download_url"], caption=track.get("name", ""))
                        return
    await update.message.reply_text("مشکلی در دانلود اسپاتیفای رخ داد.")

async def download_pinterest(update: Update, url: str):
    api = "https://haji.s2025h.space/pin/?url="
    async with aiohttp.ClientSession() as session:
        async with session.get(api + url) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("status"):
                    await update.message.reply_photo(photo=data["download_url"])
                    return
    await update.message.reply_text("مشکلی در دانلود پینترست رخ داد.")

async def download_media(update: Update, url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                links = data.get("links")
                if links:
                    for link in links:
                        # ارسال اولین لینک موجود
                        await update.message.reply_video(video=link)
                        break
                    return
    await update.message.reply_text("مشکلی در دانلود اینستاگرام رخ داد.")

async def chat_ai(update: Update, text: str):
    apis = [
        "https://starsshoptl.ir/Ai/index.php?text=",
        "https://starsshoptl.ir/Ai/index.php?model=gpt&text=",
        "https://starsshoptl.ir/Ai/index.php?model=deepseek&text="
    ]
    async with aiohttp.ClientSession() as session:
        for api in apis:
            try:
                async with session.get(api + text) as resp:
                    if resp.status == 200:
                        res_text = await resp.text()
                        if res_text.strip():
                            await update.message.reply_text(res_text.strip())
                            return
            except:
                continue
    await update.message.reply_text("خطایی در پاسخگویی هوش مصنوعی رخ داد.")

# --- اجرای ربات ---

@app.route("/", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "ok"

if __name__ == "__main__":
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(CommandHandler("cancel", cancel_support))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, support_message))

    application.run_webhook(
        listen="0.0.0.0",
        port=10000,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )
    app.run(host="0.0.0.0", port=10000)
