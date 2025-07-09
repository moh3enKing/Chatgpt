import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ContextTypes
import requests
from pymongo import MongoClient
from datetime import datetime, timedelta
import asyncio
from aiohttp import web
import json

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# توکن ربات و اطلاعات API
BOT_TOKEN = "8175470749:AAGjaYSVosmfk6AmuqXvcVbSUJAqS200q3c"
GEMINI_API_KEY = "AIzaSyDvvYZuvKhwCMMGPE7NHV2JkkhPTJ2BHQ0"
CHANNEL_ID = "@netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com/webhook"
PORT = 10000  # پورت پیش‌فرض Render برای اکانت رایگان

# اتصال به MongoDB
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client['chatbot']
users_collection = db['users']
chat_history_collection = db['chat_history']

# ذخیره تاریخچه چت در حافظه (RAM)
chat_history = {}  # ساختار: {user_id: [{"timestamp": datetime, "message": str}, ...]}

# بررسی عضویت کاربر در کانال
async def check_channel_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

# ذخیره اطلاعات کاربر در MongoDB
def save_user_to_db(user_id: int, username: str, first_name: str):
    try:
        users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "username": username,
                    "first_name": first_name,
                    "join_time": datetime.utcnow()
                }
            },
            upsert=True
        )
        logger.info(f"User {user_id} saved to database.")
    except Exception as e:
        logger.error(f"Error saving user to DB: {e}")

# ذخیره پیام در حافظه و حذف پیام‌های قدیمی‌تر از 24 ساعت
def save_to_chat_history(user_id: int, message: str):
    current_time = datetime.utcnow()
    if user_id not in chat_history:
        chat_history[user_id] = []
    
    chat_history[user_id].append({"timestamp": current_time, "message": message})
    
    # حذف پیام‌های قدیمی‌تر از 24 ساعت
    chat_history[user_id] = [
        msg for msg in chat_history[user_id]
        if current_time - msg["timestamp"] <= timedelta(hours=24)
    ]

# دریافت تاریخچه چت برای API جیمینی
def get_chat_history(user_id: int) -> str:
    if user_id in chat_history:
        return "\n".join([msg["message"] for msg in chat_history[user_id]])
    return ""

# تابع شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "N/A"
    first_name = update.effective_user.first_name or "N/A"
    
    # ذخیره اطلاعات کاربر
    save_user_to_db(user_id, username, first_name)
    
    if await check_channel_membership(context, user_id):
        await update.message.reply_text("شما قبلاً در کانال عضو هستید! می‌توانید از ربات استفاده کنید.")
        return

    # دکمه‌های شیشه‌ای
    keyboard = [
        [InlineKeyboardButton("ورود", url=f"https://t.me/{CHANNEL_ID[1:]}")],
        [InlineKeyboardButton("✅ تأیید", callback_data="verify_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await update.message.reply_text(
        f"لطفاً ابتدا در کانال {CHANNEL_ID} عضو شوید و سپس دکمه تأیید را بزنید.",
        reply_markup=reply_markup
    )
    # ذخیره پیام برای حذف بعدی
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"join_message_id": message.message_id}},
        upsert=True
    )

# تابع مدیریت پیام‌های متنی
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # ذخیره پیام در حافظه
    save_to_chat_history(user_id, message_text)
    
    if not await check_channel_membership(context, user_id):
        await update.message.reply_text(f"لطفاً ابتدا در کانال {CHANNEL_ID} عضو شوید.")
        return
    
    # ارسال پیام موقت
    temp_message = await update.message.reply_text("…")
    
    # فراخوانی API جیمینی با تاریخچه چت
    try:
        history = get_chat_history(user_id)
        prompt = f"Chat history:\n{history}\n\nCurrent message: {message_text}"
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            params={"key": GEMINI_API_KEY}
        )
        response.raise_for_status()
        gemini_response = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "پاسخ از API دریافت نشد.")
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        gemini_response = "خطا در دریافت پاسخ از API."
    
    # ویرایش پیام موقت
    await temp_message.edit_text(gemini_response)

# تابع تأیید عضویت
async def verify_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()

    if await check_channel_membership(context, user_id):
        # حذف پیام جوین
        user_data = users_collection.find_one({"user_id": user_id})
        if user_data and "join_message_id" in user_data:
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=user_data["join_message_id"])
            except Exception as e:
                logger.error(f"Error deleting message: {e}")

        # ارسال پیام موقت
        temp_message = await query.message.reply_text("…")
        
        # فراخوانی API جیمینی
        try:
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": "سلام، خوش آمدید!"}]}]},
                params={"key": GEMINI_API_KEY}
            )
            response.raise_for_status()
            gemini_response = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "پاسخ از API دریافت نشد.")
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            gemini_response = "خطا در دریافت پاسخ از API."

        # ویرایش پیام موقت
        await temp_message.edit_text(gemini_response)
    else:
        await query.message.reply_text(f"شما هنوز در کانال {CHANNEL_ID} عضو نشده‌اید. لطفاً ابتدا عضو شوید.")

# تابع تنظیم Webhook
async def set_webhook():
    application = Application.builder().token(BOT_TOKEN).build()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")

# تابع Webhook برای Render
async def webhook(request):
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(verify_membership, pattern="verify_membership"))
    application.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
    return web.json_response({"status": "ok"})

# تابع اصلی سرور
async def main():
    # تنظیم Webhook
    await set_webhook()
    
    # تنظیم سرور aiohttp برای Render
    app = web.Application()
    app.router.add_post('/webhook', webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Server running on port {PORT}")
    
# راه‌اندازی Flask
if __name__ == "__main__":
    application.bot.set_webhook(WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)
