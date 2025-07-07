import os
import re
import time
import logging
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InputMediaPhoto,
    InputMediaVideo
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

# تنظیمات اولیه
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"
DATABASE_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "ai_telegram_bot"
PORT = 1000  # پورت برای اجرا در Render

# حالت‌های گفتگو
SUPPORT, ADMIN_REPLY = range(2)

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
admin_col = db["admin"]

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# مدیریت خطاهای وب‌سرویس
class ServiceError(Exception):
    pass

# --- توابع کمکی ---
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """بررسی عضویت کاربر در کانال"""
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

async def is_admin(user_id: int) -> bool:
    """بررسی ادمین بودن کاربر"""
    return user_id == OWNER_ID or admin_col.find_one({"user_id": user_id})

async def delete_join_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """حذف پیام عضویت اجباری"""
    if "join_message_id" in context.user_data:
        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=context.user_data["join_message_id"]
            )
            del context.user_data["join_message_id"]
        except Exception as e:
            logger.error(f"Error deleting join message: {e}")

async def update_user_data(user: dict):
    """به‌روزرسانی اطلاعات کاربر در دیتابیس"""
    user_data = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "last_activity": datetime.now(),
        "message_count": 1
    }
    users_col.update_one({"user_id": user.id}, {"$set": user_data, "$inc": {"total_messages": 1}}, upsert=True)

# --- دستورات اصلی ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دستور /start"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    await update_user_data(user)
    
    # بررسی عضویت
    if await check_membership(user.id, context):
        users_col.update_one({"user_id": user.id}, {"$set": {"is_member": True}})
        await send_welcome(update, context)
        return
    
    # ارسال پیام عضویت اجباری
    keyboard = [
        [InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("✅ تایید عضویت", callback_data="verify_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = await update.message.reply_text(
        "👋 سلام! برای استفاده از ربات باید در کانال ما عضو شوید:\n\n"
        f"📢 کانال: {CHANNEL_USERNAME}\n\n"
        "پس از عضویت روی دکمه «تایید عضویت» کلیک کنید.",
        reply_markup=reply_markup
    )
    
    context.user_data["join_message_id"] = message.message_id

async def verify_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تایید عضویت کاربر در کانال"""
    query = update.callback_query
    user = query.from_user
    
    if await check_membership(user.id, context):
        users_col.update_one({"user_id": user.id}, {"$set": {"is_member": True}})
        await delete_join_message(context, query.message.chat_id)
        await send_welcome(update, context)
    else:
        await query.answer("❗️ هنوز در کانال عضو نشده‌اید! لطفاً ابتدا عضو شوید.", show_alert=True)

async def send_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام خوش‌آمدگویی"""
    query = update.callback_query if update.callback_query else None
    user = query.from_user if query else update.effective_user
    chat_id = query.message.chat_id if query else update.effective_chat.id

    # ایجاد کیبورد
    keyboard = [
        [KeyboardButton("📚 راهنما"), KeyboardButton("🛠 پشتیبانی")],
        [KeyboardButton("🎨 ساخت تصویر")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # پیام خوش‌آمد
    welcome_text = (
        f"✨ سلام {user.first_name}!\n\n"
        "به ربات هوش مصنوعی خوش آمدید! 🤖\n\n"
        "🔹 می‌توانید با ربات چت کنید\n"
        "🔹 لینک‌های اینستاگرام، اسپاتیفای و پینترست را ارسال کنید\n"
        "🔹 با دستور /image تصویر تولید کنید\n\n"
        "برای شروع از دکمه‌های زیر استفاده کنید:"
    )

    if query:
        await query.edit_message_text(
            text=welcome_text,
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_text,
            reply_markup=reply_markup
        )

async def show_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش راهنمای ربات"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # محتوای راهنما
    guide_text = """
📚 راهنمای کامل استفاده از ربات:

🔹 چت هوش مصنوعی:
• هر پیام متنی را ارسال کنید تا توسط هوش مصنوعی پردازش شود

🔹 دانلود محتوا:
• اینستاگرام: ارسال لینک پست/ریلز/استوری
• اسپاتیفای: ارسال لینک آهنگ
• پینترست: ارسال لینک پین

🔹 تولید تصویر:
• با دستور /image متن مورد نظر
مثال: 
/image منظره کوهستان با درختان سبز

⚠️ قوانین و هشدارها:
1. ارسال محتوای غیراخلاقی ممنوع است
2. استفاده از ربات برای اهداف غیرقانونی ممنوع است
3. محدودیت 4 درخواست در 2 دقیقه
4. در صورت سوءاستفاده حساب کاربری مسدود می‌شود

🛠 پشتیبانی:
• برای گزارش مشکلات از دکمه «پشتیبانی» استفاده کنید
• پاسخگویی در کمتر از 24 ساعت

🔔 نکته:
ربات از چندین سرویس هوش مصنوعی استفاده می‌کند و ممکن است پاسخ‌ها متفاوت باشند
    """
    
    keyboard = [
        [InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # ویرایش پیام قبلی یا ارسال جدید
    try:
        if "welcome_message_id" in context.user_data:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=context.user_data["welcome_message_id"],
                text=guide_text,
                reply_markup=reply_markup
            )
        else:
            message = await update.message.reply_text(
                text=guide_text,
                reply_markup=reply_markup
            )
            context.user_data["guide_message_id"] = message.message_id
    except Exception as e:
        logger.error(f"Error showing guide: {e}")
        message = await update.message.reply_text(
            text=guide_text,
            reply_markup=reply_markup
        )
        context.user_data["guide_message_id"] = message.message_id

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به صفحه اصلی"""
    query = update.callback_query
    await query.answer()
    await send_welcome(update, context)

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های دریافتی"""
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
            await message.reply_text("⏳ لطفاً 2 دقیقه صبر کنید و سپس پیام جدید ارسال کنید!")
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
    """پردازش پیام‌های متنی"""
    user = update.effective_user
    text = update.message.text
    
    # پاسخ موقت
    temp_msg = await update.message.reply_text("🔍 در حال پردازش درخواست...")
    
    # استفاده از وب‌سرویس‌های چت
    for service in CHAT_SERVICES:
        try:
            response = requests.get(service.format(text=text), timeout=10)
            if response.status_code == 200 and response.text.strip():
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=temp_msg.message_id)
                await update.message.reply_text(response.text)
                return
        except Exception as e:
            logger.error(f"Chat service error ({service}): {e}")
            continue
    
    # اگر همه سرویس‌ها خطا دادند
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=temp_msg.message_id)
    await update.message.reply_text("⚠️ متأسفیم! سرویس هوش مصنوعی در حال حاضر پاسخگو نیست. لطفاً کمی بعد تلاش کنید.")

async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش لینک‌های دریافتی"""
    url = update.message.text
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # پاسخ موقت
    temp_msg = await update.message.reply_text("⏳ در حال دریافت محتوا...")
    
    # تشخیص نوع لینک
    if 'instagram.com' in url:
        service_type = "instagram"
    elif 'spotify.com' in url:
        service_type = "spotify"
    elif 'pinterest.' in url:
        service_type = "pinterest"
    else:
        await context.bot.delete_message(chat_id=chat_id, message_id=temp_msg.message_id)
        await update.message.reply_text("⚠️ لینک ارسالی پشتیبانی نمی‌شود.")
        return
    
    try:
        service_url = DOWNLOAD_SERVICES[service_type].format(url=url)
        response = requests.get(service_url, timeout=15)
        data = response.json()
        
        await context.bot.delete_message(chat_id=chat_id, message_id=temp_msg.message_id)
        
        # پردازش پاسخ‌های مختلف
        if service_type == "instagram":
            if "links" in data:
                media_group = []
                for i, media_url in enumerate(data["links"][:10]):  # حداکثر 10 مدیا
                    if media_url.endswith(('.mp4', '.mov')):
                        if i == 0:
                            media_group.append(InputMediaVideo(media=media_url))
                        else:
                            media_group.append(InputMediaVideo(media=media_url))
                    else:
                        if i == 0:
                            media_group.append(InputMediaPhoto(media=media_url))
                        else:
                            media_group.append(InputMediaPhoto(media=media_url))
                
                if media_group:
                    await context.bot.send_media_group(chat_id=chat_id, media=media_group)
            else:
                raise ServiceError("پاسخ نامعتبر از سرویس اینستاگرام")
        
        elif service_type == "spotify":
            if data.get("ok") and "download_url" in data.get("data", {}).get("track", {}):
                await update.message.reply_audio(
                    audio=data["data"]["track"]["download_url"],
                    title=data["data"]["track"]["name"],
                    performer=data["data"]["track"]["artists"],
                    duration=int(data["data"]["track"]["duration"].split(':')[0])*60 + int(data["data"]["track"]["duration"].split(':')[1])
                )
            else:
                raise ServiceError("پاسخ نامعتبر از سرویس اسپاتیفای")
        
        elif service_type == "pinterest":
            if data.get("status") and "download_url" in data:
                await update.message.reply_photo(data["download_url"])
            else:
                raise ServiceError("پاسخ نامعتبر از سرویس پینترست")
                
    except Exception as e:
        logger.error(f"Download error ({service_type}): {e}")
        await context.bot.delete_message(chat_id=chat_id, message_id=temp_msg.message_id)
        await update.message.reply_text("❌ خطا در دریافت محتوا. لطفاً از معتبر بودن لینک اطمینان حاصل کنید.")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تولید تصویر با هوش مصنوعی"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        text = update.message.text.replace('/image', '').strip()
        if not text:
            await update.message.reply_text("❌ لطفاً متن توصیفی را وارد کنید.\nمثال: /image منظره کوهستان با آسمان آبی")
            return
        
        # پاسخ موقت
        temp_msg = await update.message.reply_text("🎨 در حال تولید تصویر...")
        
        service_url = DOWNLOAD_SERVICES["image"].format(text=text)
        response = requests.get(service_url, timeout=20)
        data = response.json()
        
        await context.bot.delete_message(chat_id=chat_id, message_id=temp_msg.message_id)
        
        if data.get("ok") and "result" in data:
            await update.message.reply_photo(
                photo=data["result"],
                caption=f"🖼 تصویر تولید شده برای:\n{text}"
            )
        else:
            raise ServiceError("پاسخ نامعتبر از سرویس تولید تصویر")
            
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        await context.bot.delete_message(chat_id=chat_id, message_id=temp_msg.message_id)
        await update.message.reply_text("❌ خطا در تولید تصویر. لطفاً متن دیگری امتحان کنید.")

# --- سیستم پشتیبانی ---
async def support_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند پشتیبانی"""
    await update.message.reply_text(
        "📩 لطفاً پیام خود را برای پشتیبانی ارسال کنید:\n\n"
        "برای لغو دستور /cancel را ارسال کنید.",
        reply_markup=ReplyKeyboardRemove()
    )
    return SUPPORT

async def process_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش پیام پشتیبانی"""
    user = update.effective_user
    message = update.effective_message
    
    # ارسال پیام به مالک
    forward_text = (
        f"📩 پیام پشتیبانی جدید\n\n"
        f"👤 کاربر: {user.full_name}\n"
        f"🆔 ID: {user.id}\n"
        f"📧 @{user.username}\n\n"
        f"📝 پیام:\n{message.text}"
    )
    
    keyboard = [[InlineKeyboardButton("✍️ پاسخ", callback_data=f"reply_{user.id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=forward_text,
        reply_markup=reply_markup
    )
    
    await update.message.reply_text(
        "✅ پیام شما با موفقیت ارسال شد!\n"
        "پاسخ شما در همین چت ارسال خواهد شد.\n\n"
        "برای بازگشت به منوی اصلی /start را ارسال کنید.",
        reply_markup=ReplyKeyboardMarkup.from_button(KeyboardButton("🏠 منوی اصلی"))
    )
    
    return ConversationHandler.END

async def cancel_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو درخواست پشتیبانی"""
    await update.message.reply_text(
        "❌ درخواست پشتیبانی لغو شد.",
        reply_markup=ReplyKeyboardMarkup.from_button(KeyboardButton("🏠 منوی اصلی"))
    )
    return ConversationHandler.END

async def admin_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع پاسخ ادمین"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    context.user_data["reply_user_id"] = user_id
    
    await query.message.reply_text(
        "✍️ لطفاً پاسخ خود را وارد کنید:\n\n"
        "برای لغو /cancel را ارسال کنید."
    )
    return ADMIN_REPLY

async def admin_reply_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پاسخ ادمین به کاربر"""
    user_id = context.user_data["reply_user_id"]
    reply_text = update.message.text
    
    try:
        # ارسال پاسخ به کاربر
        await context.bot.send_message(
            chat_id=user_id,
            text=f"📬 پاسخ پشتیبانی:\n\n{reply_text}"
        )
        
        # اطلاع به ادمین
        await update.message.reply_text(
            f"✅ پاسخ به کاربر {user_id} ارسال شد.",
            reply_markup=ReplyKeyboardMarkup.from_button(KeyboardButton("🏠 منوی اصلی"))
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ ارسال ناموفق: {e}",
            reply_markup=ReplyKeyboardMarkup.from_button(KeyboardButton("🏠 منوی اصلی"))
        )
    
    return ConversationHandler.END

async def admin_reply_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو پاسخ ادمین"""
    await update.message.reply_text(
        "❌ پاسخ دهی لغو شد.",
        reply_markup=ReplyKeyboardMarkup.from_button(KeyboardButton("🏠 منوی اصلی"))
    )
    return ConversationHandler.END

# --- مدیریت ربات ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار ربات (فقط برای ادمین)"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ دسترسی denied!")
        return
    
    total_users = users_col.count_documents({})
    active_users = users_col.count_documents({"last_activity": {"$gt": datetime.now() - timedelta(days=1)}})
    total_messages = messages_col.count_documents({})
    
    stats_text = (
        "📊 آمار ربات:\n\n"
        f"👥 کاربران کل: {total_users}\n"
        f"🟢 کاربران فعال (24h): {active_users}\n"
        f"📩 پیام‌های کل: {total_messages}"
    )
    
    await update.message.reply_text(stats_text)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام همگانی (فقط برای ادمین)"""
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ دسترسی denied!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ لطفاً پیام را وارد کنید.\nمثال: /broadcast متن پیام")
        return
    
    message_text = ' '.join(context.args)
    users = users_col.find({})
    success = 0
    failed = 0
    
    progress_msg = await update.message.reply_text(f"⏳ ارسال پیام به کاربران...\nموفق: {success} | ناموفق: {failed}")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user["user_id"],
                text=message_text
            )
            success += 1
        except:
            failed += 1
        
        if (success + failed) % 10 == 0:
            await progress_msg.edit_text(f"⏳ ارسال پیام به کاربران...\nموفق: {success} | ناموفق: {failed}")
    
    await progress_msg.edit_text(f"✅ ارسال همگانی تکمیل شد!\nموفق: {success} | ناموفق: {failed}")

# --- تنظیمات اصلی ---
def main() -> None:
    """راه‌اندازی ربات"""
    # ساخت اپلیکیشن
    application = Application.builder().token(BOT_TOKEN).build()
    
    # مدیریت گفتگوها
    conv_handler_support = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🛠 پشتیبانی$"), support_request)],
        states={
            SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_support_message)]
        },
        fallbacks=[CommandHandler("cancel", cancel_support)],
        allow_reentry=True
    )
    
    conv_handler_admin_reply = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_reply_start, pattern=r"^reply_\d+$")],
        states={
            ADMIN_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply_send)]
        },
        fallbacks=[CommandHandler("cancel", admin_reply_cancel)],
        allow_reentry=True
    )
    
    # دستورات عمومی
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("image", generate_image))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("broadcast", broadcast))
    
    # کال‌بک‌ها
    application.add_handler(CallbackQueryHandler(verify_membership, pattern="^verify_membership$"))
    application.add_handler(CallbackQueryHandler(show_guide, pattern="^back_to_main$"))
    
    # پیام‌ها
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    application.add_handler(MessageHandler(filters.Regex("^📚 راهنما$"), show_guide))
    
    # اضافه کردن مدیریت گفتگوها
    application.add_handler(conv_handler_support)
    application.add_handler(conv_handler_admin_reply)
    
    # اجرای ربات
    if os.environ.get('RENDER'):
        # اجرا در Render با وب‌هوک
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"
        )
    else:
        # اجرای محلی با پولینگ
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
