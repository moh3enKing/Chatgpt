import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from pymongo import MongoClient
from datetime import datetime, timedelta
import re
import asyncio
import logging

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# تنظیمات ربات
TOKEN = "7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE"
ADMIN_ID = 5637609683
MONGO_URI = "mongodb+srv://mohsenfeizi1386:p%40ssw0rd%279%27%21@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"
PORT = 1000

# تنظیمات دیتابیس
client = MongoClient(MONGO_URI)
db = client["chatroom_db"]
users_collection = db["users"]
messages_collection = db["messages"]

# لیست کلمات ممنوعه برای نام کاربری
FORBIDDEN_NAMES = {"admin", "administrator", "mod", "moderator", "support"}

# متغیر برای وضعیت ربات
bot_active = True

# متن قوانین
RULES_TEXT = """
سلام کاربر @{}  
به ربات Chat Room خوش آمدید!  

اینجا می‌توانید به‌صورت ناشناس با دیگر اعضای گروه چت کنید، با هم آشنا شوید و لذت ببرید.  

اما قوانینی وجود دارد که باید رعایت کنید تا از ربات مسدود نشوید:  

1. این ربات صرفاً برای سرگرمی، چت و دوست‌یابی است. از ربات برای تبلیغات، درخواست پول یا موارد مشابه استفاده نکنید.  
2. ارسال گیف به‌دلیل شلوغ نشدن ربات ممنوع است. اما ارسال عکس، موسیقی و موارد مشابه آزاد است، به‌شرطی که محتوای غیراخلاقی نباشد.  
3. ربات دارای سیستم ضداسپم است. در صورت اسپم کردن، به‌مدت ۲ دقیقه محدود خواهید شد.  
4. به یکدیگر احترام بگذارید. اگر فحاشی یا محتوای غیراخلاقی دیدید، با ریپلای روی پیام و ارسال دستور /report به ادمین اطلاع دهید.  

ربات در نسخه اولیه است و آپدیت‌های جدید در راه است.  
دوستان خود را به ربات دعوت کنید تا تجربه بهتری از چت داشته باشید.  
موفق باشید!
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = users_collection.find_one({"user_id": user_id})

    if user and user.get("registered", False):
        await update.message.reply_text(f"قبلاً ثبت‌نام کردی، خوش اومدی @{user['username']}!")
        return

    keyboard = [[InlineKeyboardButton("تأیید", callback_data="confirm_start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "لطفاً برای ادامه، یک پیام به @netgoris ارسال کنید و سپس روی دکمه تأیید کلیک کنید.",
        reply_markup=reply_markup
    )

async def confirm_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.message.delete()
    keyboard = [[InlineKeyboardButton("قوانین", callback_data="show_rules")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "آیا قوانین و مقررات را تأیید می‌کنید؟",
        reply_markup=reply_markup
    )

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    user = users_collection.find_one({"user_id": user_id})
    username = user.get("username", "کاربر") if user else "کاربر"
    await query.message.edit_text(RULES_TEXT.format(username))
    keyboard = [[InlineKeyboardButton("تأیید قوانین", callback_data="confirm_rules")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("لطفاً قوانین را تأیید کنید.", reply_markup=reply_markup)

async def confirm_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.callback_query.message.delete()
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"state": "awaiting_username"}},
        upsert=True
    )
    await update.callback_query.message.reply_text("لطفاً نام کاربری خود را (به انگلیسی) ارسال کنید. از اسامی مانند admin خودداری کنید.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_active
    if not bot_active and update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("ربات در حال حاضر غیرفعال است.")
        return

    user_id = update.effective_user.id
    user = users_collection.find_one({"user_id": user_id})

    if not user or not user.get("registered", False):
        if user and user.get("state") == "awaiting_username":
            username = update.message.text.strip()
            if not re.match("^[a-zA-Z0-9_]+$", username):
                await update.message.reply_text("نام کاربری باید به انگلیسی و بدون کاراکترهای خاص باشد.")
                return
            if username.lower() in FORBIDDEN_NAMES:
                await update.message.reply_text("این نام کاربری مجاز نیست. نام دیگری انتخاب کنید.")
                return
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"username": username, "registered": True, "state": "active"}}
            )
            await update.message.reply_text(f"نام کاربری @{username} ثبت شد. حالا می‌توانید چت کنید!")
            return

    if update.message.animation:
        await update.message.reply_text("ارسال گیف ممنوع است!")
        return

    # ضد اسپم
    now = datetime.utcnow()
    messages_collection.insert_one({
        "user_id": user_id,
        "timestamp": now,
        "message_id": update.message.message_id,
        "chat_id": update.message.chat_id
    })
    recent_messages = messages_collection.count_documents({
        "user_id": user_id,
        "timestamp": {"$gte": now - timedelta(seconds=10)}
    })
    if recent_messages > 5:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"muted_until": now + timedelta(minutes=2)}}
        )
        await update.message.reply_text("شما به دلیل اسپم به مدت ۲ دقیقه محدود شدید.")
        return

    if user.get("muted_until") and user["muted_until"] > now:
        await update.message.reply_text("شما موقتاً محدود شده‌اید. لطفاً کمی صبر کنید.")
        return

    # ارسال پیام به همه کاربران فعال
    username = user["username"] if user.get("registered") else "ادمین" if user_id == ADMIN_ID else "ناشناس"
    message_text = f"@{username}: {update.message.text}"
    if update.message.reply_to_message:
        reply_user = users_collection.find_one({"user_id": update.message.reply_to_message.from_user.id})
        reply_username = reply_user["username"] if reply_user and reply_user.get("registered") else "ناشناس"
        message_text = f"@{username} در پاسخ به @{reply_username}: {update.message.text}"

    active_users = users_collection.find({"registered": True})
    for active_user in active_users:
        if active_user["user_id"] != user_id:
            try:
                await context.bot.send_message(
                    chat_id=active_user["user_id"],
                    text=message_text,
                    reply_to_message_id=update.message.reply_to_message.message_id if update.message.reply_to_message else None
                )
            except Exception as e:
                logger.error(f"Error sending message to {active_user['user_id']}: {e}")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("فقط ادمین می‌تواند از این دستور استفاده کند.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("لطفاً روی پیام کاربر ریپلای کنید.")
        return
    target_user_id = update.message.reply_to_message.from_user.id
    users_collection.update_one(
        {"user_id": target_user_id},
        {"$set": {"banned": True}}
    )
    await update.message.reply_text(f"کاربر @{users_collection.find_one({'user_id': target_user_id})['username']} بن شد.")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("فقط ادمین می‌تواند از این دستور استفاده کند.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("لطفاً روی پیام کاربر ریپلای کنید.")
        return
    target_user_id = update.message.reply_to_message.from_user.id
    users_collection.update_one(
        {"user_id": target_user_id},
        {"$set": {"banned": False}}
    )
    await update.message.reply_text(f"کاربر @{users_collection.find_one({'user_id': target_user_id})['username']} آن‌بان شد.")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("لطفاً روی پیام موردنظر ریپلای کنید.")
        return
    target_user_id = update.message.reply_to_message.from_user.id
    target_user = users_collection.find_one({"user_id": target_user_id})
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"گزارش از @{update.effective_user.username}: پیام از @{target_user['username']}\nمتن: {update.message.reply_to_message.text}"
    )
    await update.message.reply_text("گزارش شما به ادمین ارسال شد.")

async def toggle_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_active
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("فقط ادمین می‌تواند ربات را روشن یا خاموش کند.")
        return
    bot_active = not bot_active
    status = "روشن" if bot_active else "خاموش"
    await update.message.reply_text(f"ربات {status} شد.")

async def clean_old_messages(context: ContextTypes.DEFAULT_TYPE):
    while True:
        messages_collection.delete_many({"timestamp": {"$lte": datetime.utcnow() - timedelta(hours=24)}})
        await asyncio.sleep(3600)  # هر ساعت بررسی کن

async def main():
    app = Application.builder().token(TOKEN).build()

    # اضافه کردن هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(confirm_start, pattern="confirm_start"))
    app.add_handler(CallbackQueryHandler(show_rules, pattern="show_rules"))
    app.add_handler(CallbackQueryHandler(confirm_rules, pattern="confirm_rules"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("toggle", toggle_bot))

    # تمیز کردن پیام‌های قدیمی
    app.job_queue.run_repeating(clean_old_messages, interval=3600, first=10)

    # تنظیم وب‌هوک
    logger.info(f"Setting webhook to {WEBHOOK_URL}/{TOKEN}")
    await app.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")

    # شروع ربات با وب‌هوک
    async with app:
        await app.start()
        await app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=f"/{TOKEN}",
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
        )

if __name__ == "__main__":
    asyncio.run(main())
