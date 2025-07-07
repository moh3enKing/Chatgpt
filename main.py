import logging
import aiohttp
import re
import os
from flask import Flask, request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from pymongo import MongoClient
from datetime import datetime, timedelta

TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"

client = MongoClient(MONGO_URI)
db = client["BotDatabase"]
users = db["Users"]
spam = {}

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

bot_app = Application.builder().token(TOKEN).build()


# ------------------ جین اجباری ------------------
async def check_join(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "creator", "administrator"]
    except:
        return False


# ------------------ استارت ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await check_join(user.id, context):
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("✅ تایید عضویت", callback_data="verify")]
        ]
        await update.message.reply_text("🔒 لطفاً ابتدا در کانال عضو شوید و سپس دکمه تایید را بزنید.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if not users.find_one({"user_id": user.id}):
        users.insert_one({"user_id": user.id, "joined": datetime.utcnow()})
        await context.bot.send_message(OWNER_ID, f"👤 کاربر جدید استارت کرد: {user.full_name} ({user.id})")

    keyboard = [[InlineKeyboardButton("📖 راهنما", callback_data="help")]]
    await update.message.reply_text(f"سلام {user.first_name} عزیز! 👋\nبه ربات ما خوش آمدید.\nمی‌توانید از دکمه زیر برای مشاهده راهنما استفاده کنید:", reply_markup=InlineKeyboardMarkup(keyboard))


# ------------------ دکمه ها ------------------
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "verify":
        if await check_join(query.from_user.id, context):
            await query.message.delete()
            keyboard = [[InlineKeyboardButton("📖 راهنما", callback_data="help")]]
            await context.bot.send_message(query.from_user.id, f"✅ عضویت شما تایید شد!\nبه ربات ما خوش آمدید.", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.answer("⛔ هنوز عضو کانال نیستید.", show_alert=True)

    elif query.data == "help":
        keyboard = [[InlineKeyboardButton("⬅️ بازگشت", callback_data="back")]]
        await query.message.edit_text(
            "📖 راهنمای استفاده از ربات:\n\n"
            "🔹 ارسال لینک اینستاگرام، اسپاتیفای یا پینترست ➡️ دریافت مستقیم محتوا.\n"
            "🔹 ارسال دستور `ساخت عکس متن` ➡️ ساخت تصویر (فقط متن انگلیسی).\n"
            "🔹 ارسال هر متن ➡️ پاسخ هوش مصنوعی.\n\n"
            "⚠️ قوانین:\n"
            "⛔ ارسال لینک خارج از اینستاگرام، اسپاتیفای و پینترست ممنوع است.\n"
            "⛔ رعایت ادب الزامی است.\n\n"
            "⚡ این ربات نسخه آزمایشی است و به‌مرور بروزرسانی خواهد شد.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "back":
        keyboard = [[InlineKeyboardButton("📖 راهنما", callback_data="help")]]
        await query.message.edit_text("✅ ممنون که از ربات ما استفاده می‌کنید!\nهر زمان سوال داشتید، می‌توانید مجدد از دکمه راهنما استفاده کنید.", reply_markup=InlineKeyboardMarkup(keyboard))


# ------------------ پیام ها ------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # ضد اسپم
    now = datetime.utcnow()
    if user_id not in spam:
        spam[user_id] = []
    spam[user_id] = [t for t in spam[user_id] if now - t < timedelta(minutes=2)]
    spam[user_id].append(now)
    if len(spam[user_id]) > 4:
        await update.message.reply_text("⏳ لطفاً کمی صبر کنید و بعد پیام دهید.")
        return

    # تشخیص لینک‌ها
    if "instagram.com" in text:
        await insta(update, context, text)
    elif "spotify.com" in text:
        await spotify(update, context, text)
    elif "pin.it" in text or "pinterest.com" in text:
        await pinterest(update, context, text)
    elif text.startswith("ساخت عکس "):
        await generate_image(update, context, text.replace("ساخت عکس ", ""))
    else:
        await ai_chat(update, context, text)


# ------------------ اینستاگرام ------------------
async def insta(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://pouriam.top/eyephp/instagram?url={url}") as resp:
                data = await resp.json()
        for link in data.get("links", []):
            await update.message.reply_document(link)
    except:
        await update.message.reply_text("⚠️ خطا در دریافت از اینستاگرام.")


# ------------------ اسپاتیفای ------------------
async def spotify(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://api.cactus-dev.ir/spotify.php?url={url}") as resp:
                data = await resp.json()
        if data.get("ok"):
            await update.message.reply_document(data["data"]["download_url"])
        else:
            raise Exception()
    except:
        await update.message.reply_text("⚠️ خطا در دریافت از اسپاتیفای.")


# ------------------ پینترست ------------------
async def pinterest(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://haji.s2025h.space/pin/?url={url}&client_key=keyvip") as resp:
                data = await resp.json()
        if data.get("status"):
            await update.message.reply_photo(data["download_url"])
        else:
            raise Exception()
    except:
        await update.message.reply_text("⚠️ خطا در دریافت از پینترست.")


# ------------------ ساخت عکس ------------------
async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://v3.api-free.ir/image/?text={text}") as resp:
                data = await resp.json()
        await update.message.reply_photo(data["result"])
    except:
        await update.message.reply_text("⚠️ خطا در ساخت تصویر.")


# ------------------ هوش مصنوعی ------------------
async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    urls = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}",
    ]
    for url in urls:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    reply = await resp.text()
            if reply:
                await update.message.reply_text(reply)
                return
        except:
            continue
    await update.message.reply_text("⚠️ خطا در پاسخ‌دهی هوش مصنوعی.")


# ------------------ اجرا ------------------
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(buttons))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


@app.route("/", methods=["GET", "POST"])
def index():
    return "Bot Running"


@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        bot_app.update_queue.put_nowait(request.get_json(force=True))
    return "OK"


if __name__ == "__main__":
    bot_app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=f"{WEBHOOK_URL}/webhook"
    )
