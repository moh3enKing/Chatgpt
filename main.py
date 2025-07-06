import logging
import os
import time
import requests
from flask import Flask, request
from telegram import (
    Bot, Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
)
from pymongo import MongoClient
from datetime import datetime, timedelta

# تنظیمات ربات
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com/webhook"
CHANNEL_ID = "@netgoris"
ADMIN_ID = 5637609683
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# اتصال به دیتابیس
client = MongoClient(MONGO_URI)
db = client["TellGPT"]
users = db["users"]
support = db["support"]
spam = {}

# آماده‌سازی
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
bot = Bot(BOT_TOKEN)
application = Application.builder().token(BOT_TOKEN).build()


# ضداسپم
def is_spamming(user_id):
    now = time.time()
    history = spam.get(user_id, [])
    history = [t for t in history if now - t < 120]
    history.append(now)
    spam[user_id] = history
    return len(history) > 4


# چک عضویت
async def is_member(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


# پیام راهنما
HELP_TEXT = """
🤖 به ربات TellGPT خوش آمدید

📌 امکانات ربات:
- چت هوش مصنوعی حرفه‌ای (بدون نیاز به دستور)
- دانلود ویدیو و عکس از اینستاگرام
- دریافت موزیک از اسپاتیفای
- دانلود عکس از پینترست
- ساخت عکس با متن انگلیسی (دستور: عکس متن)

⚠️ قوانین:
- اسپم = سکوت ۲ دقیقه
- برای ساخت عکس فقط متن انگلیسی مجاز است
- لینک دانلود فقط از اینستاگرام، اسپاتیفای، پینترست پذیرفته می‌شود

🛠 ربات در نسخه اولیه است و آپدیت می‌شود

هرگونه مشکل یا سوال: دکمه پشتیبانی 👇
"""

# هندل استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update.effective_user.id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 ورود به کانال", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
            [InlineKeyboardButton("✅ عضویت را بررسی کن", callback_data="check_join")]
        ])
        await update.message.reply_text("⚠️ برای استفاده، ابتدا عضو کانال شوید", reply_markup=btn)
    else:
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📖 راهنما", callback_data="help")],
                                    [InlineKeyboardButton("🎧 پشتیبانی", callback_data="support")]])
        await update.message.reply_text("✅ خوش آمدید! از امکانات ربات لذت ببرید.", reply_markup=btn)
        if not users.find_one({"user_id": update.effective_user.id}):
            users.insert_one({"user_id": update.effective_user.id, "joined": datetime.utcnow()})
            await bot.send_message(ADMIN_ID, f"🔔 کاربر جدید: {update.effective_user.full_name} ({update.effective_user.id})")


# دکمه‌ها
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check_join":
        if await is_member(query.from_user.id):
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("📖 راهنما", callback_data="help")],
                                        [InlineKeyboardButton("🎧 پشتیبانی", callback_data="support")]])
            await query.message.delete()
            await query.message.reply_text("✅ خوش آمدید! از امکانات ربات لذت ببرید.", reply_markup=btn)
            if not users.find_one({"user_id": query.from_user.id}):
                users.insert_one({"user_id": query.from_user.id, "joined": datetime.utcnow()})
                await bot.send_message(ADMIN_ID, f"🔔 کاربر جدید: {query.from_user.full_name} ({query.from_user.id})")
        else:
            await query.answer("❌ هنوز عضو نشدید", show_alert=True)

    elif query.data == "help":
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")],
                                    [InlineKeyboardButton("🎧 پشتیبانی", callback_data="support")]])
        await query.message.edit_text(HELP_TEXT, reply_markup=btn)

    elif query.data == "back":
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📖 راهنما", callback_data="help")],
                                    [InlineKeyboardButton("🎧 پشتیبانی", callback_data="support")]])
        await query.message.edit_text("✅ خوش آمدید! از امکانات ربات لذت ببرید.", reply_markup=btn)

    elif query.data == "support":
        support.update_one({"user_id": query.from_user.id}, {"$set": {"active": True}}, upsert=True)
        await query.message.reply_text("✍️ پیام خود را ارسال کنید", reply_markup=ReplyKeyboardRemove())


# پیام‌های ورودی
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    uid = update.effective_user.id

    if is_spamming(uid):
        await update.message.reply_text("⚠️ لطفاً اسپم نکنید، ۲ دقیقه سکوت")
        return

    if support.find_one({"user_id": uid, "active": True}):
        await bot.send_message(ADMIN_ID, f"📩 پیام پشتیبانی از {uid}:\n{msg}")
        support.update_one({"user_id": uid}, {"$set": {"active": False}})
        await update.message.reply_text("✅ پیام شما ارسال شد")
        return

    if msg.lower().startswith("عکس "):
        text = msg[4:]
        url = f"https://v3.api-free.ir/image/?text={text}"
        r = requests.get(url).json()
        if r.get("ok"):
            await update.message.reply_photo(r["result"])
        else:
            await update.message.reply_text("⚠️ خطا در ساخت عکس")
        return

    if "instagram.com" in msg:
        r = requests.get(f"https://pouriam.top/eyephp/instagram?url={msg}").json()
        if r.get("links"):
            for link in r["links"]:
                await update.message.reply_document(link)
        else:
            await update.message.reply_text("⚠️ خطا در دریافت اینستاگرام")
        return

    if "spotify.com" in msg:
        r = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={msg}").json()
        if r.get("ok"):
            await update.message.reply_document(r["data"]["download_url"])
        else:
            await update.message.reply_text("⚠️ خطا در دریافت موزیک")
        return

    if "pin.it" in msg or "pinterest.com" in msg:
        r = requests.get(f"https://haji.s2025h.space/pin/?url={msg}&client_key=keyvip").json()
        if r.get("status"):
            await update.message.reply_photo(r["download_url"])
        else:
            await update.message.reply_text("⚠️ خطا در دریافت عکس پینترست")
        return

    for api in [
        "https://starsshoptl.ir/Ai/index.php?text=",
        "https://starsshoptl.ir/Ai/index.php?model=gpt&text=",
        "https://starsshoptl.ir/Ai/index.php?model=deepseek&text="
    ]:
        try:
            r = requests.get(api + msg, timeout=5).text
            if r:
                await update.message.reply_text(r)
                return
        except:
            continue
    await update.message.reply_text("⚠️ خطا در پاسخ‌دهی ربات")


# پنل مدیر
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    cmd = update.message.text
    if cmd.startswith("بن "):
        try:
            uid = int(cmd.split()[1])
            msg = "⚠️ کاربر بن شد\nمتن اطلاع را بفرست:"
            users.update_one({"user_id": uid}, {"$set": {"banned": True}})
            await update.message.reply_text(msg)
        except:
            await update.message.reply_text("❌ دستور نامعتبر")

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))
application.add_handler(MessageHandler(filters.TEXT, handle_message))
application.add_handler(MessageHandler(filters.TEXT, admin_panel))


# سرور Flask و وب هوک
@app.route('/webhook', methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put_nowait(update)
    return "OK"

if __name__ == "__main__":
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
