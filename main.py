import os
import re
import time
import logging
from datetime import datetime
from pymongo import MongoClient
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# تنظیمات اولیه
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"
DATABASE_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "telegram_bot_db"

# وب‌سرویس‌ها
CHAT_SERVICES = [
    "https://starsshoptl.ir/Ai/index.php?text={text}",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
]

DOWNLOAD_SERVICES = {
    "instagram": "https://pouriam.top/eyephp/instagram?url={url}",
    "spotify": "http://api.cactus-dev.ir/spotify.php?url={url}",
    "pinterest": "https://haji.s2025h.space/pin/?url={url}&client_key=keyvip",
    "image": "https://v3.api-free.ir/image/?text={text}"
}

# اتصال به دیتابیس
client = MongoClient(DATABASE_URI)
db = client[DB_NAME]
users_col = db["users"]
messages_col = db["messages"]

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# مدیریت خطاهای وب‌سرویس
class ServiceError(Exception):
    pass

# --- توابع اصلی ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # ذخیره اطلاعات کاربر
    user_data = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_member": False,
        "join_date": datetime.now(),
        "last_message": datetime.now(),
        "message_count": 0
    }
    users_col.update_one({"user_id": user.id}, {"$set": user_data}, upsert=True)
    
    # بررسی عضویت در کانال
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user.id)
        if member.status in ["member", "administrator", "creator"]:
            users_col.update_one({"user_id": user.id}, {"$set": {"is_member": True}})
            await send_welcome(update, context)
            return
    except Exception as e:
        logger.error(f"Error checking membership: {e}")

    # ارسال پیام عضویت اجباری
    keyboard = [
        [InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("تایید عضویت", callback_data="verify_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = await update.message.reply_text(
        "📢 برای استفاده از ربات باید در کانال ما عضو شوید:\n\n"
        f"➖ {CHANNEL_USERNAME}\n\n"
        "پس از عضویت روی دکمه «تایید عضویت» کلیک کنید.",
        reply_markup=reply_markup
    )
    
    # ذخیره پیام برای حذف بعدی
    context.user_data["join_message_id"] = message.message_id

async def verify_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    
    # بررسی عضویت
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user.id)
        if member.status in ["member", "administrator", "creator"]:
            users_col.update_one({"user_id": user.id}, {"$set": {"is_member": True}})
            
            # حذف پیام عضویت اجباری
            if "join_message_id" in context.user_data:
                try:
                    await context.bot.delete_message(
                        chat_id=query.message.chat_id,
                        message_id=context.user_data["join_message_id"]
                    )
                except:
                    pass
            
            await send_welcome(update, context)
            return
    except Exception as e:
        logger.error(f"Error verifying membership: {e}")
    
    # کاربر عضو نیست
    await query.answer("❗️ هنوز در کانال عضو نشده‌اید!", show_alert=True)

async def send_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user if query else update.effective_user
    chat_id = query.message.chat_id if query else update.effective_chat.id

    # ایجاد کیبورد
    keyboard = [
        [KeyboardButton("پشتیبانی")],
        [KeyboardButton("راهنما")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # ارسال پیام خوش‌آمد
    message_text = (
        f"👋 سلام {user.first_name}!\n\n"
        "✅ عضویت شما با موفقیت تایید شد!\n"
        "به خانواده بزرگ ما خوش آمدید.\n\n"
        "با استفاده از دکمه‌های زیر می‌توانید از امکانات ربات استفاده کنید."
    )

    if query:
        await query.edit_message_text(
            text=message_text,
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=reply_markup
        )
    
    # ذخیره پیام راهنما
    context.user_data["welcome_message_id"] = message.message_id if query else None

async def show_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # محتوای راهنما
    guide_text = """
📚 راهنمای استفاده از ربات:

🔹 ارسال پیام متنی:
• هر پیام متنی را ارسال کنید تا توسط هوش مصنوعی پردازش شود

🔹 دانلود محتوا:
• اینستاگرام: ارسال لینک پست/ریلز/استوری
• اسپاتیفای: ارسال لینک آهنگ
• پینترست: ارسال لینک پین

🔹 تولید تصویر:
• با دستور /image متن مورد نظر
مثال: 
/image طبیعت بهاری

⚠️ قوانین و هشدارها:
1. ارسال محتوای غیراخلاقی ممنوع
2. استفاده از ربات برای اهداف غیرقانونی ممنوع
3. محدودیت 5 درخواست در دقیقه
4. در صورت سوءاستفاده حساب کاربری مسدود می‌شود

🛠 پشتیبانی:
• برای گزارش مشکلات از دکمه «پشتیبانی» استفاده کنید
    """
    
    keyboard = [
        [InlineKeyboardButton("بازگشت به صفحه اصلی", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # ویرایش پیام قبلی
    if "welcome_message_id" in context.user_data:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=context.user_data["welcome_message_id"],
                text=guide_text,
                reply_markup=reply_markup
            )
            return
        except:
            pass
    
    # ارسال پیام جدید
    message = await update.message.reply_text(
        text=guide_text,
        reply_markup=reply_markup
    )
    context.user_data["guide_message_id"] = message.message_id

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    chat_id = update.effective_chat.id
    
    # بررسی عضویت
    user_data = users_col.find_one({"user_id": user.id})
    if not user_data or not user_data.get("is_member", False):
        await start(update, context)
        return
    
    # ضد اسپم
    now = datetime.now()
    if "last_message" in user_data:
        last_msg_time = user_data["last_message"]
        time_diff = (now - last_msg_time).total_seconds()
        
        if time_diff < 120 and user_data.get("message_count", 0) >= 4:
            await message.reply_text("⏳ لطفاً 2 دقیقه صبر کنید!")
            return
    
    # به‌روزرسانی اطلاعات کاربر
    users_col.update_one(
        {"user_id": user.id},
        {
            "$set": {"last_message": now},
            "$inc": {"message_count": 1}
        }
    )
    
    # پردازش لینک‌ها
    if message.text and re.match(r'https?://\S+', message.text):
        await handle_links(update, context)
        return
    
    # پردازش دستورات
    if message.text and message.text.startswith('/image'):
        await generate_image(update, context)
        return
    
    # پردازش پیام متنی
    await handle_text(update, context)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    # استفاده از وب‌سرویس‌های چت
    for service in CHAT_SERVICES:
        try:
            response = requests.get(service.format(text=text), timeout=10)
            if response.status_code == 200:
                await update.message.reply_text(response.text)
                return
        except:
            continue
    
    # اگر همه سرویس‌ها خطا دادند
    await update.message.reply_text("⚠️ سرویس هوش مصنوعی در دسترس نیست. لطفاً بعداً تلاش کنید.")

async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    
    # تشخیص نوع لینک
    if 'instagram.com' in url:
        service_url = DOWNLOAD_SERVICES["instagram"].format(url=url)
    elif 'spotify.com' in url:
        service_url = DOWNLOAD_SERVICES["spotify"].format(url=url)
    elif 'pinterest.' in url:
        service_url = DOWNLOAD_SERVICES["pinterest"].format(url=url)
    else:
        await update.message.reply_text("⚠️ لینک ارسالی پشتیبانی نمی‌شود.")
        return
    
    try:
        response = requests.get(service_url, timeout=15)
        data = response.json()
        
        # پردازش پاسخ‌های مختلف
        if 'instagram.com' in url:
            if "links" in data:
                for media_url in data["links"]:
                    if media_url.endswith(('.mp4', '.mov')):
                        await update.message.reply_video(media_url)
                    else:
                        await update.message.reply_photo(media_url)
            else:
                raise ServiceError("Invalid Instagram response")
        
        elif 'spotify.com' in url:
            if data.get("ok") and "download_url" in data.get("data", {}).get("track", {}):
                await update.message.reply_audio(data["data"]["track"]["download_url"])
            else:
                raise ServiceError("Invalid Spotify response")
        
        elif 'pinterest.' in url:
            if data.get("status") and "download_url" in data:
                await update.message.reply_photo(data["download_url"])
            else:
                raise ServiceError("Invalid Pinterest response")
                
    except Exception as e:
        logger.error(f"Download error: {e}")
        await update.message.reply_text("❌ خطا در پردازش لینک. لطفاً دوباره تلاش کنید.")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.replace('/image', '').strip()
        if not text:
            await update.message.reply_text("❌ لطفاً متن توصیفی را وارد کنید.\nمثال: /image منظره کوهستان")
            return
        
        service_url = DOWNLOAD_SERVICES["image"].format(text=text)
        response = requests.get(service_url, timeout=20)
        data = response.json()
        
        if data.get("ok") and "result" in data:
            await update.message.reply_photo(data["result"])
        else:
            raise ServiceError("Invalid image response")
            
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        await update.message.reply_text("❌ خطا در تولید تصویر. لطفاً دوباره تلاش کنید.")

async def support_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📩 لطفاً پیام خود را ارسال کنید:",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data["awaiting_support"] = True

async def forward_to_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    
    if context.user_data.get("awaiting_support"):
        # ارسال پیام به مالک
        forward_text = (
            f"📩 پیام پشتیبانی از:\n"
            f"👤 {user.full_name} (@{user.username})\n"
            f"🆔 {user.id}\n\n"
            f"{message.text}"
        )
        
        keyboard = [[InlineKeyboardButton("پاسخ", callback_data=f"reply_{user.id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=forward_text,
            reply_markup=reply_markup
        )
        
        await update.message.reply_text(
            "✅ پیام شما با موفقیت ارسال شد!\n"
            "به زودی پاسخ خود را دریافت خواهید کرد.",
            reply_markup=ReplyKeyboardMarkup.from_button(KeyboardButton("راهنما"))
        )
        
        context.user_data["awaiting_support"] = False

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = int(query.data.split('_')[1])
    
    context.user_data["replying_to"] = user_id
    await query.message.reply_text("✍️ لطفاً پاسخ خود را وارد کنید:")

async def send_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "replying_to" in context.user_data:
        user_id = context.user_data["replying_to"]
        reply_text = update.message.text
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📬 پاسخ پشتیبانی:\n\n{reply_text}"
            )
            await update.message.reply_text("✅ پاسخ با موفقیت ارسال شد!")
        except Exception as e:
            await update.message.reply_text(f"❌ ارسال ناموفق: {e}")
        
        del context.user_data["replying_to"]

# --- تنظیمات اصلی ---
def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    # دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("image", generate_image))
    
    # کال‌بک‌ها
    application.add_handler(CallbackQueryHandler(verify_membership, pattern="^verify_membership$"))
    application.add_handler(CallbackQueryHandler(show_guide, pattern="^back_to_main$"))
    application.add_handler(CallbackQueryHandler(handle_admin_reply, pattern=r"^reply_\d+$"))
    
    # پیام‌ها
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    application.add_handler(MessageHandler(filters.Regex("^راهنما$"), show_guide))
    application.add_handler(MessageHandler(filters.Regex("^پشتیبانی$"), support_request))
    application.add_handler(MessageHandler(filters.TEXT & filters.User(OWNER_ID), send_admin_reply))
    application.add_handler(MessageHandler(filters.TEXT & filters.User(OWNER_ID), forward_to_owner))
    
    # اجرای ربات
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
