import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from pymongo import MongoClient
from datetime import datetime, timedelta
import logging

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# تنظیمات بات
TOKEN = "7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE"
ADMIN_ID = 5637609683
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com/webhook"
PORT = 10000
MONGO_URI = "mongodb+srv://mohsenfeizi1386:p%40ssw0rd%279%27%21@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "chatroom"
COLLECTION_USERS = "users"

# متن قوانین
RULES_TEXT = """
سلام کاربر @{username}
به ربات Chat Room خوش آمدید!

اینجا شما آزاد هستید که به‌صورت ناشناس با دیگر اعضای گروه در ارتباط باشید، چت کنید و با هم آشنا شوید.

اما قوانینی وجود دارد که باید رعایت کنید تا از ربات مسدود نشوید:

1. این ربات صرفاً برای سرگرمی، چت و دوست‌یابی طراحی شده است.
   از ربات برای تبلیغات، درخواست پول یا موارد مشابه استفاده نکنید.
2. ارسال گیف (GIF) به‌دلیل شلوغ نشدن ربات ممنوع است.
   اما ارسال عکس، موسیقی و غیره آزاد است، به‌شرطی که محتوای غیراخلاقی نباشد.
3. ربات دارای سیستم ضداسپم است. از اسپم کردن ربات خودداری کنید، وگرنه برای 2 دقیقه محدود خواهید شد.
4. به یکدیگر احترام بگذارید. در صورت مشاهده فحاشی یا محتوای غیراخلاقی، با ریپلای روی پیام و ارسال دستور /report به ادمین اطلاع دهید.

ربات در نسخه اولیه است و به‌روزرسانی‌های جدید در راه است.
دوستان خود را به ربات دعوت کنید تا تجربه بهتری در چت کردن داشته باشید.
موفق باشید!
"""

# اتصال به MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users_collection = db[COLLECTION_USERS]

# بررسی فونت گرافیکی
def is_graphical_text(text):
    graphical_pattern = re.compile(r'[^\u0600-\u06FFa-zA-Z0-9\s!@#$%^&*(),.?":{}|<>]')
    return bool(graphical_pattern.search(text))

# بررسی اسپم
async def check_spam(user_id, context):
    now = datetime.now()
    user_data = context.user_data.get("messages", [])
    user_data.append(now)
    user_data = [t for t in user_data if now - t < timedelta(seconds=5)]
    context.user_data["messages"] = user_data
    if len(user_data) > 5:
        context.user_data["spam_block_until"] = now + timedelta(minutes=2)
        return True
    return False

# شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = users_collection.find_one({"user_id": user_id})

    if user_data and user_data.get("banned"):
        await update.message.reply_text("شما از ربات مسدود شده‌اید.")
        return

    if not user_data:
        keyboard = [[InlineKeyboardButton("تأیید", callback_data="confirm_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "لطفاً به @netgoris پیام دهید تا ادامه دهید.",
            reply_markup=ForceReply(selective=True),
        )

# مدیریت پاسخ اجباری
async def handle_force_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.reply_to_message and "@netgoris" in update.message.reply_to_message.text:
        keyboard = [[InlineKeyboardButton("قوانین", callback_data="show_rules")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.delete()
        await update.message.reply_text(
            "قوانین و مقررات را تأیید می‌کنید؟", reply_markup=reply_markup
        )

# نمایش قوانین
async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = users_collection.find_one({"user_id": user_id}, {"username": 1}) or {}
    username = username.get("username", query.from_user.username or "کاربر")
    await query.message.edit_text(RULES_TEXT.format(username=username))
    await query.message.reply_text("لطفاً نام خود را برای استفاده در چت ارسال کنید.")

# ثبت نام کاربر
async def set_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.message.text.strip()

    if users_collection.find_one({"user_id": user_id, "username": {"$exists": True}}):
        await update.message.reply_text("شما قبلاً نام خود را انتخاب کرده‌اید.")
        return

    if is_graphical_text(username):
        await update.message.reply_text("لطفاً از فونت‌های ساده استفاده کنید (بدون فونت گرافیکی).")
        return

    if users_collection.find_one({"username": username}):
        await update.message.reply_text("این نام قبلاً انتخاب شده است. لطفاً نام دیگری انتخاب کنید.")
        return

    users_collection.update_one(
        {"user_id": user_id}, {"$set": {"username": username, "banned": False}}, upsert=True
    )
    await update.message.reply_text(f"نام شما با موفقیت به {username} تنظیم شد. حالا می‌توانید چت کنید!")

# مدیریت پیام‌های چت
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = users_collection.find_one({"user_id": user_id})

    if not user_data or not user_data.get("username"):
        await update.message.reply_text("لطفاً ابتدا نام خود را تنظیم کنید.")
        return

    if user_data.get("banned"):
        await update.message.reply_text("شما از ربات مسدود شده‌اید.")
        return

    if context.user_data.get("spam_block_until") and datetime.now() < context.user_data["spam_block_until"]:
        await update.message.reply_text("شما به دلیل اسپم برای 2 دقیقه محدود شده‌اید.")
        return

    if await check_spam(user_id, context):
        await update.message.reply_text("شما به دلیل اسپم برای 2 دقیقه محدود شده‌اید.")
        return

    if update.message.animation:
        await update.message.reply_text("ارسال گیف ممنوع است!")
        return

    username = "ادمین" if user_id == ADMIN_ID else user_data["username"]
    message_text = f"{username}: {update.message.text}"
    for user in users_collection.find({"banned": False}):
        if user["user_id"] != user_id:
            try:
                await context.bot.send_message(user["user_id"], message_text)
            except:
                pass

# گزارش تخلف
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("لطفاً روی پیام موردنظر ریپلای کنید.")
        return

    reported_message = update.message.reply_to_message.text
    reported_user_id = update.message.reply_to_message.from_user.id
    reported_user = users_collection.find_one({"user_id": reported_user_id})
    reported_username = reported_user.get("username", "ناشناس") if reported_user else "ناشناس"
    await context.bot.send_message(
        ADMIN_ID, f"گزارش تخلف از کاربر {reported_username}:\n{reported_message}"
    )
    await update.message.reply_text("گزارش شما به ادمین ارسال شد.")

# بن کردن کاربر
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("فقط ادمین می‌تواند از این دستور استفاده کند.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("لطفاً روی پیام کاربر موردنظر ریپلای کنید.")
        return

    target_user_id = update.message.reply_to_message.from_user.id
    users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": True}})
    await update.message.reply_text("کاربر مسدود شد.")

# رفع بن
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("فقط ادمین می‌تواند از این دستور استفاده کند.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("لطفاً روی پیام کاربر موردنظر ریپلای کنید.")
        return

    target_user_id = update.message.reply_to_message.from_user.id
    users_collection.update_one({"user_id": target_user_id}, {"$set": {"banned": False}})
    await update.message.reply_text("کاربر رفع مسدودی شد.")

# روشن/خاموش کردن ربات
async def toggle_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("فقط ادمین می‌تواند از این دستور استفاده کند.")
        return

    bot_status = context.bot_data.get("bot_enabled", True)
    context.bot_data["bot_enabled"] = not bot_status
    status_text = "فعال" if context.bot_data["bot_enabled"] else "غیرفعال"
    await update.message.reply_text(f"ربات {status_text} شد.")

# مدیریت callbackها
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_start":
        await handle_force_reply(update, context)
    elif query.data == "show_rules":
        await show_rules(update, context)

# خطاها
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.REPLY, handle_force_reply))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, set_username))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("toggle", toggle_bot))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)

    # تنظیم Webhook
    await app.bot.set_webhook(url=WEBHOOK_URL)
    await app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="/webhook",
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
