import logging
import requests
import re
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from pymongo import MongoClient
from datetime import datetime, timedelta

# ---------------- تنظیمات ----------------
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
SUPPORT_ACTIVE = {}

# ---------------- اتصال به دیتابیس ----------------
client = MongoClient(MONGO_URI)
db = client['TelegramBot']
users = db['Users']
spam = db['Spam']

# ---------------- تنظیم لاگ ----------------
logging.basicConfig(level=logging.INFO)

# ---------------- متن راهنما ----------------
HELP_TEXT = """
🤖 راهنمای استفاده از ربات:

🔹 ارسال پیام متنی: فقط کافیست پیام خود را ارسال کنید، هوش مصنوعی پاسخ می‌دهد.

🔹 دانلود اینستاگرام، اسپاتیفای، پینترست:
لینک مربوطه را ارسال کنید، فایل مستقیم برای شما ارسال می‌شود.

🔹 ساخت عکس:
دستور زیر را ارسال کنید (متن انگلیسی باشد):
ساخت عکس [متن]

🌟 امکانات:
✔️ پاسخ هوش مصنوعی
✔️ دانلود مستقیم شبکه‌های اجتماعی
✔️ ساخت عکس با متن سفارشی
✔️ ارتباط با پشتیبانی

📌 قوانین:
- ارسال 4 پیام پشت سر هم = سکوت 2 دقیقه
- فقط لینک‌های معتبر یا دستور ساخت عکس را ارسال کنید
- رعایت ادب الزامی است

📢 نسخه فعلی: اولیه (ربات درحال آپدیت می‌باشد)

کانال رسمی: @netgoris
"""

# ---------------- توابع ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not users.find_one({"user_id": user.id}):
        users.insert_one({"user_id": user.id, "first_name": user.first_name})
        await context.bot.send_message(chat_id=OWNER_ID, text=f"کاربر جدید استارت کرد:\n{user.mention_html()}", parse_mode="HTML")

    if not await is_member(context, user.id):
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")]
        ]
        await update.message.reply_text("🔒 لطفاً ابتدا عضو کانال شوید:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await send_main_menu(update, context)

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_member(context, query.from_user.id):
        await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        await send_main_menu(query, context)
    else:
        await query.reply_text("⛔ هنوز عضو کانال نیستید!")

async def send_main_menu(update_or_query, context):
    keyboard = [
        [InlineKeyboardButton("📖 راهنما", callback_data="help")],
        [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")]
    ]
    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text("🎉 خوش آمدید! از ربات لذت ببرید.", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update_or_query.message.reply_text("🎉 خوش آمدید! از ربات لذت ببرید.", reply_markup=InlineKeyboardMarkup(keyboard))

async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
    await query.edit_message_text(HELP_TEXT, reply_markup=InlineKeyboardMarkup(keyboard))

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    SUPPORT_ACTIVE[query.from_user.id] = True
    await query.message.reply_text("✍️ پیام خود را ارسال کنید، پاسخ توسط مدیریت داده می‌شود.")
    
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await send_main_menu(query, context)

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    # ضد اسپم
    recent_msgs = spam.find({"user_id": user.id, "time": {"$gt": datetime.utcnow() - timedelta(minutes=2)}})
    if recent_msgs.count() >= 4:
        await update.message.reply_text("⛔ لطفاً ۲ دقیقه صبر کنید.")
        return
    spam.insert_one({"user_id": user.id, "time": datetime.utcnow()})

    # چک پشتیبانی
    if SUPPORT_ACTIVE.get(user.id):
        await context.bot.send_message(chat_id=OWNER_ID, text=f"💬 پیام جدید از {user.first_name}:\n{text}")
        SUPPORT_ACTIVE.pop(user.id)
        await update.message.reply_text("✅ پیام شما ارسال شد.")
        return

    # لینک‌ها
    if "instagram.com" in text:
        await handle_instagram(update, context, text)
    elif "spotify.com" in text:
        await handle_spotify(update, context, text)
    elif "pin" in text:
        await handle_pinterest(update, context, text)
    elif text.lower().startswith("ساخت عکس"):
        query = text.replace("ساخت عکس", "").strip()
        await handle_image(update, context, query)
    else:
        await handle_ai_chat(update, context, text)

async def handle_instagram(update, context, url):
    try:
        res = requests.get(f"https://pouriam.top/eyephp/instagram?url={url}").json()
        for link in res.get("links", []):
            await update.message.reply_document(link)
    except:
        await update.message.reply_text("⛔ خطا در دریافت از اینستاگرام")

async def handle_spotify(update, context, url):
    try:
        res = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={url}").json()
        await update.message.reply_document(res["data"]["download_url"])
    except:
        await update.message.reply_text("⛔ خطا در دریافت آهنگ")

async def handle_pinterest(update, context, url):
    try:
        res = requests.get(f"https://haji.s2025h.space/pin/?url={url}&client_key=keyvip").json()
        await update.message.reply_photo(res["download_url"])
    except:
        await update.message.reply_text("⛔ خطا در دریافت عکس پینترست")

async def handle_image(update, context, query):
    try:
        res = requests.get(f"https://v3.api-free.ir/image/?text={query}").json()
        await update.message.reply_photo(res["result"])
    except:
        await update.message.reply_text("⛔ خطا در ساخت تصویر")

async def handle_ai_chat(update, context, text):
    urls = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=5).text
            if res:
                await update.message.reply_text(res)
                return
        except:
            continue
    await update.message.reply_text("⛔ هوش مصنوعی در دسترس نیست.")

async def is_member(context, user_id):
    try:
        member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "creator", "administrator"]
    except:
        return False

# ---------------- اجرا ----------------

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(help_menu, pattern="help"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="back"))
    app.add_handler(CallbackQueryHandler(support, pattern="support"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    app.run_webhook(port=10000, listen="0.0.0.0", webhook_url="https://chatgpt-qg71.onrender.com")

if __name__ == "__main__":
    main()
