import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters
import aiohttp
from pymongo import MongoClient
import os

# اطلاعات اصلی
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"

client = MongoClient(MONGO_URI)
db = client['bot']
users_col = db['users']

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

# بررسی عضویت کانال
async def is_user_member(user_id):
    try:
        member = await application.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_member(user.id):
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton("✅ تایید عضویت", callback_data="verify_join")]
        ]
        await update.message.reply_text("🔒 لطفا ابتدا عضو کانال شوید و سپس تایید بزنید.", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        if not users_col.find_one({"user_id": user.id}):
            users_col.insert_one({"user_id": user.id})
            await application.bot.send_message(OWNER_ID, f"✅ کاربر جدید:\n{user.full_name} - {user.id}")
        await send_welcome(update)

# پیام خوش آمد و راهنما
async def send_welcome(update):
    keyboard = [
        [InlineKeyboardButton("📖 راهنما", callback_data="show_help")]
    ]
    await update.message.reply_text(
        "🎉 به ربات هوش مصنوعی خوش آمدید!\nبرای مشاهده امکانات روی دکمه زیر بزنید.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# دکمه‌ها
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "verify_join":
        if await is_user_member(user.id):
            await query.message.delete()
            await send_welcome(update)
        else:
            await query.answer("⛔ هنوز عضو کانال نیستید!", show_alert=True)

    elif query.data == "show_help":
        keyboard = [[InlineKeyboardButton("⬅️ بازگشت", callback_data="back_home")]]
        await query.message.edit_text(
            "📖 راهنمای ربات:\n\n"
            "✅ چت معمولی = پاسخ هوش مصنوعی\n"
            "✅ ارسال لینک اینستاگرام، اسپاتیفای، پینترست = دریافت محتوا\n"
            "✅ دستور ساخت عکس: `عکس متن انگلیسی`\n\n"
            "⚠️ قوانین:\n"
            "⛔ اسپم = سکوت موقت\n"
            "🔧 نسخه اولیه، آپدیت خواهد شد.\n\n"
            "👨‍💻 پشتیبانی همیشه در دسترس است.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif query.data == "back_home":
        keyboard = [[InlineKeyboardButton("📖 راهنما", callback_data="show_help")]]
        await query.message.edit_text(
            "🙏 ممنون که ربات ما را انتخاب کردید. امیدواریم راضی باشید.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# پیام‌ها
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if not await is_user_member(user.id):
        return

    if text.lower().startswith("عکس "):
        txt = text[4:]
        await generate_image(update, txt)
    elif "instagram.com" in text:
        await download_instagram(update, text)
    elif "spotify.com" in text:
        await download_spotify(update, text)
    elif "pin.it" in text or "pinterest.com" in text:
        await download_pinterest(update, text)
    else:
        await ai_chat(update, text)

# هوش مصنوعی
async def ai_chat(update, text):
    urls = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]
    for url in urls:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.text()
                    if "Hey" in data:
                        await update.message.reply_text(data)
                        return
        except:
            continue
    await update.message.reply_text("⛔ خطا در پردازش!")

# اینستاگرام
async def download_instagram(update, url):
    try:
        api = f"https://pouriam.top/eyephp/instagram?url={url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as resp:
                data = await resp.json()
                for link in data.get("links", []):
                    await update.message.reply_text(link)
    except:
        await update.message.reply_text("⛔ خطا در دریافت اینستاگرام!")

# اسپاتیفای
async def download_spotify(update, url):
    try:
        api = f"http://api.cactus-dev.ir/spotify.php?url={url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as resp:
                data = await resp.json()
                mp3 = data["data"]["track"]["download_url"]
                await update.message.reply_audio(mp3)
    except:
        await update.message.reply_text("⛔ خطا در اسپاتیفای!")

# پینترست
async def download_pinterest(update, url):
    try:
        api = f"https://haji.s2025h.space/pin/?url={url}&client_key=keyvip"
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as resp:
                data = await resp.json()
                await update.message.reply_photo(data["download_url"])
    except:
        await update.message.reply_text("⛔ خطا در پینترست!")

# ساخت عکس
async def generate_image(update, text):
    try:
        api = f"https://v3.api-free.ir/image/?text={text}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as resp:
                data = await resp.json()
                await update.message.reply_photo(data["result"])
    except:
        await update.message.reply_text("⛔ خطا در ساخت عکس!")

# وب‌هوک
@app.route("/", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "ok"

# شروع
if __name__ == "__main__":
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    application.run_webhook(listen="0.0.0.0", port=10000, webhook_url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)
