import os
import logging
import pymongo
from pymongo import MongoClient
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaAudio
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler
)
import requests
from datetime import datetime, timedelta
from urllib.parse import quote

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تنظیمات پایگاه داده MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = "telegram_bot_db"

# تنظیمات ربات
TOKEN = os.getenv("TOKEN", "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0")
OWNER_ID = int(os.getenv("OWNER_ID", "5637609683"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@netgoris")
CHANNEL_LINK = f"https://t.me/{CHANNEL_USERNAME[1:]}"
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@mohsenfeizi")

# URLهای سرویس‌های خارجی
AI_SERVICES = [
    "https://starsshoptl.ir/Ai/index.php?text=",
    "https://starsshoptl.ir/Ai/index.php?model=gpt&text=",
    "https://starsshoptl.ir/Ai/index.php?model=deepseek&text="
]
INSTA_DOWNLOADER = "https://pouriam.top/eyephp/instagram?url="
SPOTIFY_DOWNLOADER = "http://api.cactus-dev.ir/spotify.php?url="
PINTEREST_DOWNLOADER = "https://haji.s2025h.space/pin/?url={}&client_key=keyvip"
IMAGE_GENERATOR = "https://v3.api-free.ir/image/?text="

# حالت‌های گفتگو
JOIN_CHANNEL, MAIN_MENU, SUPPORT, ADMIN_PANEL = range(4)

# اتصال به MongoDB
try:
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    users_col = db["users"]
    admins_col = db["admins"]
    logger.info("Connected to MongoDB successfully!")
except Exception as e:
    logger.error(f"Error connecting to MongoDB: {e}")
    exit()

def is_user_member(user_id: int, context: CallbackContext) -> bool:
    try:
        member = context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

def create_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("راهنمای ربات 📚", callback_data="help")],
        [InlineKeyboardButton("پشتیبانی 👨‍💻", callback_data="support")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_join_keyboard():
    keyboard = [
        [InlineKeyboardButton("عضویت در کانال 📢", url=CHANNEL_LINK)],
        [InlineKeyboardButton("تایید عضویت ✅", callback_data="check_join")]
    ]
    return InlineKeyboardMarkup(keyboard)

def send_welcome_message(update: Update, context: CallbackContext):
    user = update.effective_user
    welcome_text = f"""
سلام {user.first_name} عزیز! 👋

به ربات هوش مصنوعی ما خوش آمدید! 🤖✨

شما می‌توانید از این ربات برای:
- چت هوشمند با هوش مصنوعی
- دانلود محتوای اینستاگرام، اسپاتیفای و پینترست
- تولید تصاویر با هوش مصنوعی

استفاده کنید.

لطفا برای شروع از دکمه‌های زیر استفاده نمایید.
"""
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_text,
        reply_markup=create_main_keyboard()
    )

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = user.id
    
    user_data = {
        "user_id": user_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "join_date": datetime.now(),
        "last_activity": datetime.now(),
        "message_count": 0,
        "is_member": False
    }
    
    users_col.update_one(
        {"user_id": user_id},
        {"$set": user_data},
        upsert=True
    )
    
    if users_col.count_documents({"user_id": user_id}) == 1:
        context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"👤 کاربر جدید:\n\nID: {user_id}\nName: {user.full_name}\nUsername: @{user.username}"
        )
    
    join_text = """
🔹 برای استفاده از ربات، لطفا در کانال ما عضو شوید.

پس از عضویت، روی دکمه «تایید عضویت» کلیک کنید.
"""
    message = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=join_text,
        reply_markup=create_join_keyboard()
    )
    
    context.user_data["join_message_id"] = message.message_id
    return JOIN_CHANNEL

def check_join(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    
    if is_user_member(user_id, context):
        try:
            context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=context.user_data["join_message_id"]
            )
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
        
        users_col.update_one(
            {"user_id": user_id},
            {"$set": {"is_member": True}}
        )
        
        send_welcome_message(update, context)
        query.answer("✅ عضویت شما تایید شد! اکنون می‌توانید از ربات استفاده کنید.")
        return MAIN_MENU
    else:
        query.answer("❌ شما هنوز در کانال عضو نشده‌اید! لطفا ابتدا عضو شوید.", show_alert=True)
        return JOIN_CHANNEL

def show_help(update: Update, context: CallbackContext):
    query = update.callback_query
    help_text = """
📚 راهنمای استفاده از ربات:

🔹 چت هوشمند:
فقط متن خود را ارسال کنید تا ربات پاسخ دهد.

🔹 دانلود محتوا:
• اینستاگرام: ارسال لینک پست/ریلز/استوری
• اسپاتیفای: ارسال لینک آهنگ
• پینترست: ارسال لینک پین

🔹 تولید تصویر:
ارسال دستور /image به همراه متن مورد نظر
مثال: /image گل رز

⚠️ قوانین و هشدارها:
1. استفاده از ربات برای اهداف غیراخلاقی ممنوع است.
2. ارسال اسپم و پیام‌های مکرر باعث محدودیت دسترسی می‌شود.
3. ربات را برای دیگران فوروارد نکنید.
4. در صورت مشاهده هرگونه مشکل با پشتیبانی در ارتباط باشید.

ما همیشه در خدمت شما هستیم! 🤝
"""
    keyboard = [
        [InlineKeyboardButton("بازگشت ↩️", callback_data="back_to_main")]
    ]
    
    query.edit_message_text(
        text=help_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def support(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    
    support_text = f"""
پشتیبانی 👨‍💻

شما می‌توانید سوالات و مشکلات خود را از طریق ایدی زیر با ما در میان بگذارید:

{SUPPORT_USERNAME}

لطفا پیام خود را به صورت مستقیم برای پشتیبانی ارسال کنید.
"""
    
    keyboard = [
        [InlineKeyboardButton("بازگشت ↩️", callback_data="back_to_main")]
    ]
    
    query.edit_message_text(
        text=support_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"📩 درخواست پشتیبانی از:\n\n👤 کاربر: {user.full_name}\n🆔 ID: {user.id}\n📌 یوزرنیم: @{user.username}"
    )
    
    return SUPPORT

def back_to_main(update: Update, context: CallbackContext):
    query = update.callback_query
    send_welcome_message(update, context)
    return MAIN_MENU

def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text
    
    user_data = users_col.find_one({"user_id": user_id})
    if not user_data or not user_data.get("is_member", False):
        update.message.reply_text("⚠️ لطفا ابتدا در کانال عضو شوید و سپس از ربات استفاده کنید.")
        return JOIN_CHANNEL
    
    last_message_time = user_data.get("last_message_time", datetime.min)
    message_count = user_data.get("message_count", 0)
    
    if (datetime.now() - last_message_time) < timedelta(minutes=2) and message_count >= 4:
        update.message.reply_text("⏳ لطفا برای جلوگیری از اسپم، 2 دقیقه صبر کنید و سپس پیام جدید ارسال کنید.")
        return
    
    users_col.update_one(
        {"user_id": user_id},
        {
            "$set": {"last_message_time": datetime.now()},
            "$inc": {"message_count": 1}
        }
    )
    
    if text.startswith(("http://", "https://")):
        handle_url(update, context)
    else:
        handle_ai_request(update, context)

def handle_ai_request(update: Update, context: CallbackContext):
    text = update.message.text
    chat_id = update.effective_chat.id
    
    context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    response = None
    for service in AI_SERVICES:
        try:
            url = service + quote(text)
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200 and resp.text.strip():
                response = resp.text
                break
        except Exception as e:
            logger.error(f"Error with AI service {service}: {e}")
            continue
    
    if response:
        update.message.reply_text(response)
    else:
        update.message.reply_text("⚠️ متاسفانه در حال حاضر سرویس هوش مصنوعی در دسترس نیست. لطفا بعدا تلاش کنید.")

def handle_url(update: Update, context: CallbackContext):
    url = update.message.text
    chat_id = update.effective_chat.id
    
    context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")
    
    if "instagram.com" in url:
        download_instagram(update, context)
    elif "spotify.com" in url:
        download_spotify(update, context)
    elif "pinterest.com" in url:
        download_pinterest(update, context)
    else:
        update.message.reply_text("⚠️ لینک ارسالی معتبر نیست. لطفا فقط لینک‌های اینستاگرام، اسپاتیفای یا پینترست ارسال کنید.")

def download_instagram(update: Update, context: CallbackContext):
    url = update.message.text
    try:
        response = requests.get(INSTA_DOWNLOADER + url, timeout=15)
        data = response.json()
        
        if "links" in data:
            media_list = []
            for i, link in enumerate(data["links"][:10]):
                if link.lower().endswith((".jpg", ".jpeg", ".png")):
                    if i == 0:
                        media_list.append(InputMediaPhoto(link))
                    else:
                        media_list.append(InputMediaPhoto(link))
                elif link.lower().endswith((".mp4", ".mov")):
                    if i == 0:
                        media_list.append(InputMediaVideo(link))
                    else:
                        media_list.append(InputMediaVideo(link))
            
            if media_list:
                context.bot.send_media_group(
                    chat_id=update.effective_chat.id,
                    media=media_list
                )
            else:
                update.message.reply_text("⚠️ محتوای قابل دانلود یافت نشد.")
        else:
            update.message.reply_text("⚠️ خطا در دریافت محتوای اینستاگرام. لطفا لینک را بررسی کنید.")
    except Exception as e:
        logger.error(f"Error downloading Instagram content: {e}")
        update.message.reply_text("⚠️ خطا در پردازش لینک اینستاگرام. لطفا بعدا تلاش کنید.")

def download_spotify(update: Update, context: CallbackContext):
    url = update.message.text
    try:
        response = requests.get(SPOTIFY_DOWNLOADER + url, timeout=15)
        data = response.json()
        
        if data.get("ok", False):
            track = data["data"]["track"]
            caption = f"🎵 {track['name']}\n🎤 {track['artists']}\n⏳ مدت: {track['duration']}"
            
            duration_parts = track["duration"].split(":")
            duration_seconds = int(duration_parts[0]) * 60 + int(duration_parts[1])
            
            context.bot.send_audio(
                chat_id=update.effective_chat.id,
                audio=track["download_url"],
                caption=caption,
                title=track["name"],
                performer=track["artists"],
                duration=duration_seconds
            )
        else:
            update.message.reply_text("⚠️ خطا در دریافت آهنگ اسپاتیفای. لطفا لینک را بررسی کنید.")
    except Exception as e:
        logger.error(f"Error downloading Spotify track: {e}")
        update.message.reply_text("⚠️ خطا در پردازش لینک اسپاتیفای. لطفا بعدا تلاش کنید.")

def download_pinterest(update: Update, context: CallbackContext):
    url = update.message.text
    try:
        response = requests.get(PINTEREST_DOWNLOADER.format(quote(url)), timeout=15)
        data = response.json()
        
        if data.get("status", False):
            if data["download_url"].lower().endswith((".jpg", ".jpeg", ".png")):
                context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=data["download_url"]
                )
            elif data["download_url"].lower().endswith((".mp4", ".mov")):
                context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=data["download_url"]
                )
            else:
                context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=data["download_url"]
                )
        else:
            update.message.reply_text("⚠️ خطا در دریافت محتوای پینترست. لطفا لینک را بررسی کنید.")
    except Exception as e:
        logger.error(f"Error downloading Pinterest content: {e}")
        update.message.reply_text("⚠️ خطا در پردازش لینک پینترست. لطفا بعدا تلاش کنید.")

def generate_image(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("⚠️ لطفا متن مورد نظر را بعد از دستور /image وارد کنید.\nمثال: /image گل رز")
        return
    
    text = " ".join(context.args)
    chat_id = update.effective_chat.id
    
    context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")
    
    try:
        response = requests.get(IMAGE_GENERATOR + quote(text), timeout=20)
        data = response.json()
        
        if data.get("ok", False):
            context.bot.send_photo(
                chat_id=chat_id,
                photo=data["result"],
                caption=f"تصویر تولید شده برای: {text}"
            )
        else:
            update.message.reply_text("⚠️ خطا در تولید تصویر. لطفا بعدا تلاش کنید.")
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        update.message.reply_text("⚠️ خطا در تولید تصویر. لطفا بعدا تلاش کنید.")

def admin_panel(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("⛔ دسترسی denied!")
        return
    
    keyboard = [
        [InlineKeyboardButton("آمار کاربران 📊", callback_data="user_stats")],
        [InlineKeyboardButton("ارسال پیام به همه 📢", callback_data="broadcast")],
        [InlineKeyboardButton("بازگشت ↩️", callback_data="back_to_main")]
    ]
    
    update.message.reply_text(
        "پنل مدیریت 👨‍💼",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ADMIN_PANEL

def show_user_stats(update: Update, context: CallbackContext):
    query = update.callback_query
    total_users = users_col.count_documents({})
    active_users = users_col.count_documents({"last_activity": {"$gt": datetime.now() - timedelta(days=7)}})
    members = users_col.count_documents({"is_member": True})
    
    stats_text = f"""
📊 آمار کاربران:

👥 کاربران کل: {total_users}
🟢 کاربران فعال (7 روز اخیر): {active_users}
✅ اعضای کانال: {members}
"""
    
    keyboard = [
        [InlineKeyboardButton("بازگشت ↩️", callback_data="back_to_admin")]
    ]
    
    query.edit_message_text(
        text=stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ADMIN_PANEL

def start_broadcast(update: Update, context: CallbackContext):
    query = update.callback_query
    context.user_data["broadcast_mode"] = True
    
    query.edit_message_text("لطفا پیامی که می‌خواهید برای همه کاربران ارسال کنید را بنویسید:")
    
    return ADMIN_PANEL

def process_broadcast(update: Update, context: CallbackContext):
    if "broadcast_mode" not in context.user_data:
        return
    
    message = update.message.text
    users = users_col.find({})
    success = 0
    failed = 0
    
    update.message.reply_text("⏳ در حال ارسال پیام به کاربران...")
    
    for user in users:
        try:
            context.bot.send_message(
                chat_id=user["user_id"],
                text=message
            )
            success += 1
        except Exception as e:
            logger.error(f"Error sending to user {user['user_id']}: {e}")
            failed += 1
    
    del context.user_data["broadcast_mode"]
    
    update.message.reply_text(
        f"✅ ارسال پیام همگانی تکمیل شد:\n\nارسال موفق: {success}\nارسال ناموفق: {failed}"
    )
    
    return admin_panel(update, context)

def back_to_admin(update: Update, context: CallbackContext):
    query = update.callback_query
    return admin_panel(update, context)

def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Update {update} caused error {context.error}")
    if update.effective_message:
        update.effective_message.reply_text("⚠️ خطایی رخ داد. لطفا دوباره تلاش کنید.")

def main():
    # ایجاد آپدیتور و دیسپچر
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # ایجاد هندلر گفتگو
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            JOIN_CHANNEL: [
                CallbackQueryHandler(check_join, pattern='^check_join$')
            ],
            MAIN_MENU: [
                CallbackQueryHandler(show_help, pattern='^help$'),
                CallbackQueryHandler(support, pattern='^support$'),
                CallbackQueryHandler(back_to_main, pattern='^back_to_main$')
            ],
            SUPPORT: [
                CallbackQueryHandler(back_to_main, pattern='^back_to_main$')
            ],
            ADMIN_PANEL: [
                CallbackQueryHandler(show_user_stats, pattern='^user_stats$'),
                CallbackQueryHandler(start_broadcast, pattern='^broadcast$'),
                CallbackQueryHandler(back_to_main, pattern='^back_to_main$'),
                CallbackQueryHandler(back_to_admin, pattern='^back_to_admin$'),
                MessageHandler(Filters.text & ~Filters.command, process_broadcast)
            ]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    # ثبت هندلرها
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler("image", generate_image))
    dispatcher.add_handler(CommandHandler("admin", admin_panel))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dispatcher.add_error_handler(error_handler)

    # شروع ربات (برای Render)
    PORT = int(os.environ.get('PORT', 5000))
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://chatgpt-qg71.onrender.com") + "/" + TOKEN
    
    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL,
        drop_pending_updates=True
    )
    
    logger.info("Bot is running...")
    updater.idle()

if __name__ == '__main__':
    main()
