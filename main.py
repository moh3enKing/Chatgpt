import os
import logging
import re
import time
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
from flask import Flask, request

# تنظیمات اولیه
TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
ADMIN_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"
DB_PASSWORD = "RIHPhDJPhd9aNJvC"
MONGODB_URI = f"mongodb+srv://mohsenfeizi1386:{DB_PASSWORD}@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
RENDER_URL = "https://chatgpt-qg71.onrender.com"

# اتصال به دیتابیس
client = MongoClient(MONGODB_URI)
db = client.telegram_bot
users_col = db.users

# وب‌سرویس‌ها
CHAT_SERVICES = [
    "https://starsshoptl.ir/Ai/index.php?text=",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text=",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text="
]

DOWNLOAD_SERVICES = {
    "instagram": "https://pouriam.top/eyephp/instagram?url=",
    "spotify": "http://api.cactus-dev.ir/spotify.php?url=",
    "pinterest": "https://haji.s2025h.space/pin/?url={}&client_key=keyvip",
    "image": "https://v3.api-free.ir/image/?text="
}

# تنظیم لاگ‌گیری
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ایجاد اپلیکیشن Flask برای وب‌هوک
flask_app = Flask(__name__)

# --- توابع کمکی ---
async def is_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

async def send_join_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("✅ تایید عضویت", callback_data="verify_join")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = await update.message.reply_text(
        "📣 برای استفاده از ربات، ابتدا در کانال ما عضو شوید:",
        reply_markup=reply_markup
    )
    context.user_data["join_message_id"] = message.message_id

async def delete_join_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    try:
        await context.bot.delete_message(chat_id, message_id)
    except:
        pass

# --- دستورات اصلی ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data["first_start"] = True
    
    # ثبت کاربر جدید در دیتابیس
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({
            "user_id": user_id,
            "joined_at": datetime.now(),
            "verified": False,
            "message_count": 0,
            "last_message_time": datetime.now()
        })
    
    # چک کردن عضویت
    if await is_member(user_id, context):
        await welcome_user(update, context)
    else:
        await send_join_message(update, context)

async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # حذف پیام عضویت اجباری
    if "join_message_id" in context.user_data:
        await delete_join_message(
            context,
            update.effective_chat.id,
            context.user_data["join_message_id"]
        )
    
    # آپدیت وضعیت کاربر
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {"verified": True}}
    )
    
    # ارسال پیام خوش‌آمدگویی
    keyboard = [
        [KeyboardButton("📚 راهنمای استفاده")],
        [KeyboardButton("🆘 پشتیبانی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "✨ به ربات هوش مصنوعی خوش آمدید!\n\n"
        "✅ عضویت شما با موفقیت تایید شد.\n"
        "لطفاً برای آشنایی با قابلیت‌های ربات از راهنمای استفاده کمک بگیرید.",
        reply_markup=reply_markup
    )

# --- مدیریت عضویت ---
async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if await is_member(query.from_user.id, context):
        await welcome_user_callback(query, context)
    else:
        await query.edit_message_text(
            "❌ هنوز در کانال عضو نشده‌اید!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                [InlineKeyboardButton("✅ تایید عضویت", callback_data="verify_join")]
            ])
        )

async def welcome_user_callback(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    
    # حذف پیام عضویت اجباری
    await delete_join_message(
        context,
        query.message.chat_id,
        query.message.message_id
    )
    
    # آپدیت وضعیت کاربر
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {"verified": True}}
    )
    
    # ارسال پیام خوش‌آمدگویی
    keyboard = [
        [KeyboardButton("📚 راهنمای استفاده")],
        [KeyboardButton("🆘 پشتیبانی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await context.bot.send_message(
        query.message.chat_id,
        "✨ به ربات هوش مصنوعی خوش آمدید!\n\n"
        "✅ عضویت شما با موفقیت تایید شد.\n"
        "لطفاً برای آشنایی با قابلیت‌های ربات از راهنمای استفاده کمک بگیرید.",
        reply_markup=reply_markup
    )

# --- راهنمای استفاده ---
async def show_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="exit_guide")],
        [InlineKeyboardButton("🌟 ما همیشه در خدمت شما هستیم", callback_data="service_message")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    guide_text = (
        "📚 راهنمای جامع استفاده از ربات:\n\n"
        "🔹 <b>قابلیت‌های اصلی:</b>\n"
        "- چت هوش مصنوعی (GPT, DeepSeek)\n"
        "- دانلود از اینستاگرام: ارسال لینک پست\n"
        "- دانلود از اسپاتیفای: ارسال لینک آهنگ\n"
        "- دانلود از پینترست: ارسال لینک پین\n"
        "- تولید تصاویر هوش مصنوعی: /image متن\n\n"
        "🔹 <b>نحوه استفاده:</b>\n"
        "1. برای چت متنی، پیام خود را ارسال کنید\n"
        "2. برای دانلود، لینک پست را ارسال کنید\n"
        "3. برای ساخت تصویر: /image متن توصیفی\n\n"
        "⚠️ <b>قوانین و هشدارها:</b>\n"
        "- ارسال هرزنامه ممنوع (4 پیام در 2 دقیقه = محدودیت)\n"
        "- استفاده غیراخلاقی ممنوع\n"
        "- ربات فقط برای استفاده شخصی\n"
        "- هر کاربر حداکثر 10 درخواست در ساعت\n\n"
        "🛑 تخلف از قوانین منجر به مسدود شدن خواهد شد!"
    )
    
    # ویرایش پیام فعلی به جای ارسال پیام جدید
    if update.message:
        await update.message.reply_text(
            guide_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.message.reply_text(
            guide_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    context.user_data["in_guide"] = True

# --- پشتیبانی ---
async def support_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 لطفاً پیام خود را برای پشتیبانی ارسال کنید:",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data["awaiting_support"] = True

async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    
    # ارسال به ادمین با ریپلای
    forward_msg = await context.bot.send_message(
        ADMIN_ID,
        f"✉️ پیام پشتیبانی از کاربر:\n"
        f"👤: {user.full_name} [@{user.username or 'N/A'}]",
        reply_to_message_id=context.user_data.get("support_thread_id")
    )
    
    await context.bot.forward_message(
        ADMIN_ID,
        message.chat_id,
        message.message_id
    )
    
    # ذخیره اطلاعات برای پاسخ
    context.user_data["support_thread_id"] = forward_msg.message_id
    context.user_data["support_user_id"] = user.id
    
    # پاسخ به کاربر
    await message.reply_text(
        "✅ پیام شما برای پشتیبانی ارسال شد. به زودی پاسخ داده خواهد شد.",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📚 راهنمای استفاده")],
            [KeyboardButton("🆘 پشتیبانی")]
        ], resize_keyboard=True)
    )
    context.user_data["awaiting_support"] = False

# --- ضد اسپم ---
def check_spam(user_id: int) -> bool:
    user = users_col.find_one({"user_id": user_id})
    if not user:
        return True
    
    current_time = datetime.now()
    last_time = user.get("last_message_time", datetime.min)
    count = user.get("message_count", 0)
    
    # اگر بیش از 2 دقیقه گذشته باشد، ریست کن
    if (current_time - last_time).total_seconds() > 120:
        users_col.update_one(
            {"user_id": user_id},
            {"$set": {"message_count": 1, "last_message_time": current_time}}
        )
        return True
    
    # اگر کمتر از 2 دقیقه و بیش از 4 پیام
    if count >= 4:
        return False
    
    # افزایش تعداد پیام‌ها
    users_col.update_one(
        {"user_id": user_id},
        {"$inc": {"message_count": 1}}
    )
    return True

# --- مدیریت پیام‌ها ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # چک عضویت در کانال
    user_data = users_col.find_one({"user_id": user_id})
    if not user_data or not user_data.get("verified"):
        await send_join_message(update, context)
        return
    
    # مدیریت پشتیبانی
    if context.user_data.get("awaiting_support"):
        await forward_to_admin(update, context)
        return
    
    # ضد اسپم
    if not check_spam(user_id):
        await update.message.reply_text("⏳ لطفاً 2 دقیقه صبر کنید و سپس دوباره امتحان کنید.")
        return
    
    # پردازش لینک‌ها
    message_text = update.message.text or update.message.caption or ""
    
    # تشخیص نوع لینک
    if "instagram.com" in message_text:
        await handle_instagram(update, context)
    elif "spotify.com" in message_text:
        await handle_spotify(update, context)
    elif "pinterest.com" in message_text:
        await handle_pinterest(update, context)
    elif message_text.startswith("/image"):
        await generate_image(update, context)
    else:
        await handle_ai_chat(update, context)

# --- هوش مصنوعی ---
async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text
    
    # ارسال به وب‌سرویس‌ها
    response = None
    for service in CHAT_SERVICES:
        try:
            # شبیه‌سازی ارسال درخواست
            # در نسخه واقعی از requests استفاده می‌شود
            response = f"🤖 پاسخ هوش مصنوعی:\n\nبرای '{message}'"
            break
        except:
            continue
    
    if response:
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("⚠️ سرویس هوش مصنوعی در دسترس نیست. لطفاً بعداً تلاش کنید.")

# --- مدیریت دانلود ---
async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    service_url = DOWNLOAD_SERVICES["instagram"] + url
    # شبیه‌سازی دریافت پاسخ
    await update.message.reply_text("📥 در حال دانلود از اینستاگرام...")
    await update.message.reply_video("https://example.com/video.mp4")

async def handle_spotify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    service_url = DOWNLOAD_SERVICES["spotify"] + url
    # شبیه‌سازی دریافت پاسخ
    await update.message.reply_text("🎵 در حال دانلود از اسپاتیفای...")
    await update.message.reply_audio("https://example.com/song.mp3")

async def handle_pinterest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    service_url = DOWNLOAD_SERVICES["pinterest"].format(url)
    # شبیه‌سازی دریافت پاسخ
    await update.message.reply_text("📌 در حال دانلود از پینترست...")
    await update.message.reply_photo("https://example.com/image.jpg")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/image", "").strip()
    service_url = DOWNLOAD_SERVICES["image"] + text
    # شبیه‌سازی دریافت پاسخ
    await update.message.reply_text("🎨 در حال تولید تصویر...")
    await update.message.reply_photo("https://example.com/generated_image.jpg")

# --- مدیریت ادمین ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    keyboard = [
        ["📊 آمار کاربران"],
        ["📣 ارسال همگانی"],
        ["🚫 مدیریت کاربران"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🔐 پنل مدیریت:\n"
        "لطفاً گزینه مورد نظر را انتخاب کنید:",
        reply_markup=reply_markup
    )

# --- راه‌اندازی وب‌هوک ---
def setup_application():
    # ساخت اپلیکیشن تلگرام
    application = Application.builder().token(TOKEN).build()
    
    # ثبت هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(verify_join, pattern="^verify_join$"))
    
    # راهنما و پشتیبانی
    application.add_handler(MessageHandler(filters.Regex("📚 راهنمای استفاده"), show_guide))
    application.add_handler(MessageHandler(filters.Regex("🆘 پشتیبانی"), support_request))
    
    return application

# --- راه‌اندازی سرور Flask ---
@flask_app.route('/webhook', methods=['POST'])
async def webhook():
    application = setup_application()
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return 'ok'

@flask_app.route('/set_webhook', methods=['GET'])
def set_webhook():
    application = setup_application()
    url = f"{RENDER_URL}/webhook"
    application.bot.set_webhook(url)
    return f"Webhook set to {url}"

@flask_app.route('/')
def index():
    return "Bot is running!"

if __name__ == '__main__':
    # برای اجرای محلی
    # application = setup_application()
    # application.run_polling()
    
    # برای اجرا در Render
    port = int(os.environ.get("PORT", 1000))
    flask_app.run(host="0.0.0.0", port=port)
