import os
import logging
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# --- تنظیمات اولیه ---
# توکن ربات شما
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
# لینک دیتابیس MongoDB شما
MONGODB_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# آیدی عددی صاحب ربات
OWNER_ID = 5637609683
# آیدی کانال (باید با @ شروع شود)
CHANNEL_USERNAME = "@netgoris"
# لینک کانال برای دکمه (معمولا t.me/channel_username)
CHANNEL_LINK = "https://t.me/netgoris"
# دامنه هاست شما در Render
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"

# --- پیکربندی لاگینگ (برای نمایش رویدادها در کنسول) ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- اتصال به دیتابیس MongoDB ---
try:
    client = MongoClient(MONGODB_URI)
    db = client.get_database("telegram_bot_db")  # نام دیتابیس
    users_collection = db.users  # کالکشن برای ذخیره کاربران
    logger.info("Successfully connected to MongoDB.")
except Exception as e:
    logger.error(f"Error connecting to MongoDB: {e}")
    # در یک ربات واقعی، شاید بخواهید در اینجا ربات را متوقف کنید یا به مدیر اطلاع دهید.

# --- توابع کمکی ---
async def is_user_member(user_id: int) -> bool:
    """بررسی می‌کند که آیا کاربر در کانال عضو است یا خیر."""
    try:
        # get_chat_member فقط برای اعضای کانال کار میکنه، اگه عضو نباشه خطا میده
        # برای همین از try-except استفاده میکنیم
        chat_member = await application.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        # وضعیت هایی که نشان دهنده عضویت هستن: member, administrator, creator
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        # کاربر عضو نیست یا خطای دیگری رخ داده است (مثلا ربات ادمین کانال نیست)
        logger.error(f"Error checking channel membership for user {user_id}: {e}")
        return False

async def send_force_join_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام عضویت اجباری را ارسال می‌کند."""
    keyboard = [
        [InlineKeyboardButton("💎 کانال نت گورس 💎", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ تایید عضویت ✅", callback_data="check_membership")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text(
        "👋 **سلام کاربر عزیز!**\n\n"
        "برای استفاده از ربات، لطفاً ابتدا در کانال ما عضو شوید:\n"
        f"➡️ {CHANNEL_USERNAME}\n\n"
        "پس از عضویت، روی دکمه **'تایید عضویت'** بزنید تا ربات فعال شود.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام خوش‌آمدگویی را ارسال می‌کند."""
    keyboard = [
        [InlineKeyboardButton("📚 راهنمای استفاده 📚", callback_data="show_guide")],
        # دکمه های دیگر که بعدا اضافه میشن
        [InlineKeyboardButton("👨‍💻 پشتیبانی 👨‍💻", callback_data="support_chat")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.effective_message.reply_text(
        "🎉 **به ربات هوش مصنوعی خوش آمدید!** 🎉\n\n"
        "از اینکه به جمع ما پیوستید، سپاسگزاریم. "
        "من اینجا هستم تا در کارهای مختلف به شما کمک کنم.\n\n"
        "برای آشنایی بیشتر با قابلیت‌ها و نحوه استفاده از ربات، "
        "لطفاً روی دکمه **'راهنمای استفاده'** در پایین کلیک کنید 👇",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# --- هندلرهای دستورات و CallbackQuery ها ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دستور /start."""
    user = update.effective_user
    user_id = user.id
    
    # بررسی اینکه آیا کاربر قبلاً در دیتابیس ثبت شده است یا خیر
    user_data = users_collection.find_one({"_id": user_id})

    if not user_data:
        # کاربر برای اولین بار استارت کرده
        users_collection.insert_one({"_id": user_id, "first_start": True, "is_member": False})
        logger.info(f"New user started the bot: {user_id} - @{user.username}")
        # اطلاع‌رسانی به صاحب ربات
        if OWNER_ID:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"🚀 کاربر جدیدی ربات را استارت کرد:\n"
                     f"🆔: `{user_id}`\n"
                     f"👤 نام: {user.full_name}\n"
                     f"@{user.username if user.username else 'ندارد'}",
                parse_mode="Markdown"
            )
        
    is_member = await is_user_member(user_id)
    
    if is_member:
        # اگر کاربر عضو بود، مستقیماً پیام خوش‌آمدگویی را ارسال کن
        users_collection.update_one({"_id": user_id}, {"$set": {"is_member": True}})
        await send_welcome_message(update, context)
    else:
        # اگر عضو نبود، پیام عضویت اجباری را ارسال کن
        users_collection.update_one({"_id": user_id}, {"$set": {"is_member": False}})
        await send_force_join_message(update, context)

async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دکمه 'تایید عضویت'."""
    query = update.callback_query
    await query.answer() # ضروری برای جلوگیری از حالت لودینگ دکمه

    user_id = query.from_user.id
    is_member = await is_user_member(user_id)

    if is_member:
        # اگر کاربر عضو شد
        users_collection.update_one({"_id": user_id}, {"$set": {"is_member": True}})
        await query.edit_message_text(
            "✅ تبریک! عضویت شما تایید شد. از این پس می‌توانید از تمام امکانات ربات استفاده کنید."
        )
        # حذف پیام عضویت اجباری و ارسال پیام خوش‌آمدگویی جدید
        await send_welcome_message(update, context)
    else:
        # اگر کاربر هنوز عضو نشده بود
        await query.edit_message_text(
            "❌ هنوز عضویت شما تایید نشده است. لطفاً ابتدا در کانال عضو شوید و سپس دوباره روی 'تایید عضویت' کلیک کنید.",
            reply_markup=query.message.reply_markup # کیبورد قبلی رو دوباره نشون بده
        )

async def show_guide_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دکمه 'راهنمای استفاده'."""
    query = update.callback_query
    await query.answer()

    guide_text = (
        "📚 **راهنمای جامع استفاده از ربات** 📚\n\n"
        "به بخش راهنما خوش آمدید! در اینجا می‌توانید با تمام قابلیت‌ها و قوانین استفاده از ربات آشنا شوید.\n\n"
        "---"
        "\n\n"
        "✨ **قابلیت‌های اصلی ربات:**\n"
        "1.  **هوش مصنوعی چت:** با ارسال هر متنی، ربات با استفاده از مدل‌های پیشرفته هوش مصنوعی به شما پاسخ می‌دهد. (مثال: `سلام، حالت چطوره؟`)\n"
        "2.  **دانلودر شبکه‌های اجتماعی:**\n"
        "    * **اینستاگرام:** کافیست لینک پست (ویدئو، عکس، ریلز) اینستاگرام را ارسال کنید تا محتوا را دریافت کنید.\n"
        "    * **اسپاتیفای:** لینک آهنگ اسپاتیفای را بفرستید تا فایل MP3 آن را دریافت کنید.\n"
        "    * **پینترست:** با ارسال لینک هر پین، تصویر یا ویدئوی مربوطه را برای شما ارسال می‌کنیم.\n"
        "    ⚠️ **نکته:** ربات به صورت خودکار نوع لینک را تشخیص می‌دهد و نیازی به دستور خاصی نیست.\n"
        "3.  **ساخت عکس از متن:** متن مورد نظر خود را ارسال کنید تا ربات یک تصویر بر اساس آن ایجاد کند. (مثال: `گل رز قرمز`)\n\n"
        "---"
        "\n\n"
        "🚨 **اخطارها و قوانین استفاده:** 🚨\n"
        "1.  **محدودیت اسپم:** برای جلوگیری از سوءاستفاده، شما مجاز به ارسال حداکثر **۴ پیام در هر ۲ دقیقه** هستید. در صورت تجاوز از این حد، ربات موقتاً به پیام‌های شما پاسخ نخواهد داد.\n"
        "2.  **محتوای نامناسب:** ارسال هرگونه محتوای غیرقانونی، غیراخلاقی، توهین‌آمیز یا مرتبط با خشونت، نفرت‌پراکنی و فعالیت‌های غیرمجاز اکیداً ممنوع است و می‌تواند منجر به مسدود شدن دسترسی شما به ربات شود.\n"
        "3.  **احترام متقابل:** لطفاً در تعامل با ربات و در صورت استفاده از بخش پشتیبانی، احترام متقابل را رعایت کنید.\n"
        "4.  **حریم خصوصی:** اطلاعات چت‌های شما با ربات محرمانه تلقی می‌شود و با هیچ شخص ثالثی به اشتراک گذاشته نخواهد شد.\n"
        "5.  **سوءاستفاده از سرویس‌ها:** هرگونه تلاش برای ایجاد اختلال در عملکرد ربات یا سوءاستفاده از وب‌سرویس‌ها منجر به مسدود شدن دسترسی خواهد شد.\n\n"
        "---"
        "\n\n"
        "🙏 **با تشکر از همراهی شما!**\n"
        "تیم ما همیشه در تلاش است تا بهترین خدمات را به شما ارائه دهد."
    )

    # دکمه ای که برنمیگرده به صفحه قبلی و فقط یه پیام تشکر نشون میده
    keyboard = [
        [InlineKeyboardButton("💖 ما همیشه خدمت‌گزار شماییم 💖", callback_data="thank_you_message")],
        [InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="back_to_main_menu")] # دکمه بازگشت
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        guide_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def thank_you_message_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دکمه 'ما همیشه خدمت‌گزار شماییم'."""
    query = update.callback_query
    await query.answer()
    
    # این دکمه قرار نیست برگرده به صفحه قبلی، فقط یه پیام تشکر نشون میده و همینجا تموم میشه
    # میتونیم همون کیبورد راهنما رو دوباره نشون بدیم یا یه کیبورد جدید
    keyboard = [
        [InlineKeyboardButton("💖 ما همیشه خدمت‌گزار شماییم 💖", callback_data="thank_you_message")],
        [InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="back_to_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "✨ **با افتخار، تیم ما همیشه در خدمت شماست!** ✨\n\n"
        "هدف ما ارائه بهترین تجربه کاربری است. اگر سوالی دارید، "
        "دکمه راهنما همچنان در دسترس شماست.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def back_to_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دکمه 'بازگشت به منوی اصلی' از راهنما."""
    query = update.callback_query
    await query.answer()

    # ارسال مجدد پیام خوش آمدگویی
    await send_welcome_message(update, context)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر خطاها."""
    logger.error(f"Update {update} caused error {context.error}")
    # اینجا میتونید به مدیر ربات هم خطا رو گزارش بدید
    if update.effective_chat:
        try:
            await update.effective_chat.send_message("متاسفم، مشکلی پیش آمد. لطفا دوباره تلاش کنید.")
        except Exception:
            pass # اگه نتونستیم پیام خطا رو هم بفرستیم، لاگ میکنیم

# --- تابع اصلی برای راه‌اندازی ربات ---
def main() -> None:
    """تابع اصلی برای راه‌اندازی ربات."""
    global application # برای دسترسی از تابع is_user_member

    # ساخت شی Application
    application = Application.builder().token(BOT_TOKEN).build()

    # --- افزودن هندلرها ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(check_membership_callback, pattern="^check_membership$"))
    application.add_handler(CallbackQueryHandler(show_guide_callback, pattern="^show_guide$"))
    application.add_handler(CallbackQueryHandler(thank_you_message_callback, pattern="^thank_you_message$"))
    application.add_handler(CallbackQueryHandler(back_to_main_menu_callback, pattern="^back_to_main_menu$"))


    # --- تنظیم وب‌هوک برای Render ---
    port = int(os.environ.get("PORT", "8443")) # پورت پیش‌فرض Render
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN, # مسیر URL برای وب‌هوک
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )
    logger.info(f"Webhook set up at {WEBHOOK_URL}/{BOT_TOKEN} on port {port}")

if __name__ == "__main__":
    main()
