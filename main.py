import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
from pymongo import MongoClient
import os

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# توکن ربات و اطلاعات API
BOT_TOKEN = "8175470749:AAGjaYSVosmfk6AmuqXvcVbSUJAqS200q3c"
GEMINI_API_KEY = "AIzaSyDvvYZuvKhwCMMGPE7NHV2JkkhPTJ2BHQ0"
CHANNEL_ID = "@netgoris"
MONGO_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com/webhook"

# اتصال به MongoDB
client = MongoClient(MONGO_URI)
db = client['chatbot']
users_collection = db['users']

# بررسی عضویت کاربر در کانال
async def check_channel_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

# تابع شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
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
    app = Application.builder().token(BOT_TOKEN).build()
    await app.bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")

# تابع Webhook برای هاست رندر
async def webhook(request):
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(verify_membership, pattern="verify_membership"))
    
    update = Update.de_json(request.get_json(force=True), app.bot)
    await app.process_update(update)
    return {"status": "ok"}

# تابع اصلی برای اجرای ربات
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(verify_membership, pattern="verify_membership"))
    
    # تنظیم Webhook برای رندر
    import asyncio
    asyncio.run(set_webhook())
    
# راه‌اندازی Flask
if __name__ == "__main__":
    application.bot.set_webhook(WEBHOOK_URL)
    app.run(host="0.0.0.0", port=PORT)
