import logging
import re
import time
import requests
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from pymongo import MongoClient
from io import BytesIO

# ====== تنظیمات ======
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
ADMIN_ID = 5637609683
CHANNEL = "@netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"https://chatgpt-qg71.onrender.com{WEBHOOK_PATH}"
PORT = int(__import__("os").environ.get("PORT", "10000"))

# لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask برای وب‌هوک
app = Flask(__name__)

# MongoDB
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
users = db["users"]

# ربات
application = Application.builder().token(BOT_TOKEN).build()

# حالت‌های in-memory
spam_times = {}
support_mode = {}

# کیبورد‌های ثابت
def main_menu():
    return ReplyKeyboardMarkup([["پشتیبانی"]], resize_keyboard=True)

def inline_menu(buttons):
    return InlineKeyboardMarkup(buttons)

# --- دستورات ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users.update_one({"user_id": uid}, {"$setOnInsert": {"banned": False, "joined": False}}, upsert=True)
    if users.find_one({"user_id": uid}).get("banned"):
        return await update.message.reply_text("❌ شما مسدود شده‌اید.")
    # جوین اجباری
    member = await context.bot.get_chat_member(CHANNEL, uid)
    if member.status not in ["member", "administrator", "creator"]:
        buttons = [
            [InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL.lstrip('@')}")],
            [InlineKeyboardButton("✅ تأیید عضویت", callback_data="verify_join")]
        ]
        return await update.message.reply_text("لطفاً ابتدا عضو کانال شوید:", reply_markup=inline_menu(buttons))
    # خوش‌آمد
    users.update_one({"user_id": uid}, {"$set": {"joined": True}}, upsert=True)
    if not users.find_one({"user_id": uid, "notified": True}):
        await context.bot.send_message(ADMIN_ID, f"👤 کاربر جدید: @{update.effective_user.username} ({uid})")
        users.update_one({"user_id": uid}, {"$set": {"notified": True}})
    buttons = [[InlineKeyboardButton("📖 راهنما", callback_data="help")]]
    await update.message.reply_text(f"👋 سلام {update.effective_user.first_name}!", reply_markup=inline_menu(buttons))

async def verify_join_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    member = await context.bot.get_chat_member(CHANNEL, uid)
    if member.status in ["member", "administrator", "creator"]:
        await query.message.delete()
        buttons = [[InlineKeyboardButton("📖 راهنما", callback_data="help")]]
        await context.bot.send_message(uid, "✅ عضویت تأیید شد!", reply_markup=inline_menu(buttons))
        users.update_one({"user_id": uid}, {"$set": {"joined": True}}, upsert=True)
    else:
        await query.answer("هنوز عضو کانال نیستید!", show_alert=True)

async def help_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "📚 راهنما:\n"
        "۱. ارسال لینک اینستاگرام، اسپاتیفای، پینترست → دانلود محتوا\n"
        "۲. ارسال `عکس <متن انگلیسی>` → ساخت تصویر\n"
        "۳. ارسال متن عادی → پاسخ هوش مصنوعی\n"
        "⚠️ قوانین: هر ۴ پیام پشت هم → سکوت ۲ دقیقه\n"
        "درصورت سوال “پشتیبانی” را ارسال کنید."
    )
    buttons = [[InlineKeyboardButton("⬅️ بازگشت", callback_data="back")]]
    await query.message.edit_text(text, reply_markup=inline_menu(buttons))

async def back_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    buttons = [[InlineKeyboardButton("📖 راهنما", callback_data="help")]]
    await query.message.edit_text("✅ متشکریم!", reply_markup=inline_menu(buttons))

# --- پیام متنی ---
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    # اسپم
    now = time.time()
    arr = spam_times.get(uid, [])
    arr = [t for t in arr if now - t < 120]
    arr.append(now)
    spam_times[uid] = arr
    if len(arr) > 4:
        return await update.message.reply_text("⏳ برای ۲ دقیقه سکوت شدید.")
    # پشتیبانی
    if support_mode.get(uid):
        support_mode.pop(uid)
        await context.bot.send_message(ADMIN_ID, f"💬 پیام پشتیبانی از {uid}:\n{text}")
        return await update.message.reply_text("✅ ارسال شد.", reply_markup=main_menu())
    if text == "پشتیبانی":
        support_mode[uid] = True
        return await update.message.reply_text("✉️ پیام خود را ارسال کنید:", reply_markup=ReplyKeyboardRemove())
    # لینک‌ها
    if "instagram.com" in text:
        await download_instagram(update, context, text)
    elif "spotify.com" in text:
        await download_spotify(update, context, text)
    elif "pinterest.com" in text or "pin.it" in text:
        await download_pinterest(update, context, text)
    elif text.startswith("عکس "):
        await generate_image(update, context, text[5:].strip())
    else:
        await ai_chat(update, context, text)

# --- توابع کمکی ---
async def download_instagram(update, context, url):
    res = requests.get(f"https://pouriam.top/eyephp/instagram?url={url}").json()
    for link in res.get("links", []):
        await update.message.reply_document(link)

async def download_spotify(update, context, url):
    res = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={url}").json()
    dl = res.get("data", {}).get("track", {}).get("download_url")
    if dl: await update.message.reply_audio(dl)

async def download_pinterest(update, context, url):
    res = requests.get(f"https://haji.s2025h.space/pin/?url={url}&client_key=keyvip}").json()
    if res.get("download_url"): await update.message.reply_photo(res["download_url"])

async def generate_image(update, context, prompt):
    if re.search(r'[\u0600-\u06FF]', prompt):
        return await update.message.reply_text("⚠️ متن باید انگلیسی باشد.")
    resp = requests.get(f"https://v3.api-free.ir/image/?text={prompt}")
    if resp.ok:
        await update.message.reply_photo(resp.content)

async def ai_chat(update, context, text):
    for endpoint in [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]:
        try:
            res = requests.get(endpoint, timeout=5)
            if res.ok and res.text:
                return await update.message.reply_text(res.text)
        except: pass
    await update.message.reply_text("❌ خطا در دریافت پاسخ.")

# --- هندلرها ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(verify_join_callback, pattern="verify_join"))
application.add_handler(CallbackQueryHandler(help_cb, pattern="help"))
application.add_handler(CallbackQueryHandler(back_cb, pattern="back"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

# --- وب‌هوک ---
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.post_update(update)
    return Response("OK", status=200)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
