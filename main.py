import os
import time
import re
import threading
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.error import TelegramError
from flask import Flask, request
import logging

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تنظیمات محیطی
BOT_TOKEN = os.getenv("BOT_TOKEN", "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
ADMIN_ID = int(os.getenv("ADMIN_ID", 5637609683))
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002762412959")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com/" + BOT_TOKEN

# Flask برای Webhook
app = Flask(__name__)

# اتصال به MongoDB
client = MongoClient(MONGO_URI)
db = client["bot_db"]
users_collection = db["users"]
support_chats_collection = db["support_chats"]

# ذخیره پیام‌ها در رم
messages = {}

# تابع پاک‌سازی پیام‌های قدیمی (۲۴ ساعته)
def cleanup_messages():
    while True:
        current_time = time.time()
        for user_id in list(messages.keys()):
            messages[user_id] = [
                msg for msg in messages[user_id]
                if current_time - msg["timestamp"] < 24 * 3600
            ]
            if not messages[user_id]:
                del messages[user_id]
        time.sleep(3600)  # هر ساعت چک کن

# شروع ترد پاک‌سازی
threading.Thread(target=cleanup_messages, daemon=True).start()

# چک کردن عضویت در کانال
async def check_membership(update: Update, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except TelegramError:
        return False

# چک کردن ضداسپم
async def check_spam(user_id: int):
    user = users_collection.find_one({"user_id": user_id})
    if not user or user.get("is_vip"):
        return True
    current_time = time.time()
    last_time = user.get("last_message_time", 0)
    message_count = user.get("message_count_spam", 0)
    if current_time - last_time < 5:  # ۵ ثانیه
        message_count += 1
        if message_count >= 3:
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"last_message_time": current_time + 120, "message_count_spam": 0}}
            )
            return False
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"message_count_spam": message_count, "last_message_time": current_time}}
        )
    else:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"message_count_spam": 1, "last_message_time": current_time}}
        )
    return True

# چک کردن محدودیت‌ها
async def check_limits(user_id: int, limit_type: str):
    user = users_collection.find_one({"user_id": user_id})
    if not user or user.get("is_vip"):
        return True
    current_time = time.time()
    reset_time = user.get("reset_time", 0)
    if current_time - reset_time > 24 * 3600:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"message_count": 0, "download_requests": 0, "image_requests": 0, "reset_time": current_time}}
        )
        user = users_collection.find_one({"user_id": user_id})
    if limit_type == "chat" and user.get("message_count", 0) >= 200:
        return False
    if limit_type == "download" and user.get("download_requests", 0) >= 5:
        return False
    if limit_type == "image" and user.get("image_requests", 0) >= 3:
        return False
    return True

# تابع وب‌سرویس‌های چت
async def get_chat_response(user_id: int, text: str):
    context = messages.get(user_id, [])[-5:]  # ۵ پیام آخر
    context_text = "\n".join([f"{'Bot' if msg['is_bot'] else 'User'}: {msg['text']}" for msg in context])
    full_text = f"Context:\n{context_text}\nMessage: {text}" if context else text
    services = [
        f"https://starsshoptl.ir/Ai/index.php?text={full_text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={full_text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={full_text}",
    ]
    for service in services:
        try:
            response = requests.get(service, timeout=10)
            if response.status_code == 200:
                return response.text.strip()
        except:
            continue
    return None

# تابع دانلودرها
async def download_file(url: str, service_type: str):
    if service_type == "instagram":
        response = requests.get(f"https://pouriam.top/eyephp/instagram?url={url}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("links", [])[0] if data.get("links") else None
    elif service_type == "spotify":
        response = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={url}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("track", {}).get("download_url")
    elif service_type == "pinterest":
        response = requests.get(f"https://haji.s2025h.space/pin/?url={url}&client_key=keyvip", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("download_url")
    return None

# تابع ساخت عکس
async def generate_image(text: str):
    if not re.match(r"^[a-zA-Z\s]+$", text):
        return None, "لطفاً فقط متن انگلیسی وارد کنید!"
    response = requests.get(f"https://v3.api-free.ir/image/?text={text}", timeout=10)
    if response.status_code == 200:
        data = response.json()
        return data.get("result"), None
    return None, "خطا در تولید عکس!"

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "کاربر"
    if await check_membership(update, user_id, context):
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"is_member": True, "joined_at": time.time()}},
            upsert=True
        )
        # اطلاع به ادمین
        await context.bot.send_message(
            ADMIN_ID,
            f"کاربر جدید: @{username} (ID: {user_id})\nزمان: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        keyboard = [
            [InlineKeyboardButton("راهنما", callback_data="help")],
            [InlineKeyboardButton("پشتیبانی", callback_data="support")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"خوش اومدی @{username}! 🎉\nحالا می‌تونی از قابلیت‌های ربات استفاده کنی.\nبرای اطلاعات بیشتر، دکمه راهنما رو بزن.",
            reply_markup=reply_markup
        )
        # چک کردن زیرمجموعه‌گیری
        if update.message.text.startswith("/start ") and len(update.message.text.split()) > 1:
            referrer_id = int(update.message.text.split()[1])
            if referrer_id != user_id:
                users_collection.update_one(
                    {"user_id": referrer_id},
                    {"$inc": {"referral_count": 1}},
                    upsert=True
                )
                user = users_collection.find_one({"user_id": referrer_id})
                if user.get("referral_count", 0) >= 3 and not user.get("is_vip"):
                    users_collection.update_one(
                        {"user_id": referrer_id},
                        {"$set": {"is_vip": True}}
                    )
                    await context.bot.send_message(
                        referrer_id,
                        "موفق شدی! 🎉 به لیست ویژه‌ها اضافه شدی و حالا می‌تونی بدون محدودیت از ربات استفاده کنی."
                    )
    else:
        keyboard = [
            [InlineKeyboardButton("جوین به کانال", url="https://t.me/netgoris")],
            [InlineKeyboardButton("تأیید عضویت", callback_data="check_membership")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "برای استفاده از ربات، باید عضو کانال @netgoris باشید! 👇",
            reply_markup=reply_markup
        )

# دکمه‌های شیشه‌ای
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username or "کاربر"
    if query.data == "check_membership":
        if await check_membership(update, user_id, context):
            await query.message.delete()
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"is_member": True, "joined_at": time.time()}},
                upsert=True
            )
            # اطلاع به ادمین
            await context.bot.send_message(
                ADMIN_ID,
                f"کاربر جدید: @{username} (ID: {user_id})\nزمان: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            keyboard = [
                [InlineKeyboardButton("راهنما", callback_data="help")],
                [InlineKeyboardButton("پشتیبانی", callback_data="support")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                user_id,
                f"خوش اومدی @{username}! 🎉\nحالا می‌تونی از قابلیت‌های ربات استفاده کنی.\nبرای اطلاعات بیشتر، دکمه راهنما رو بزن.",
                reply_markup=reply_markup
            )
        else:
            await query.message.reply_text("لطفاً اول به کانال @netgoris ملحق بشید!")
    elif query.data == "help":
        keyboard = [
            [InlineKeyboardButton("زیرمجموعه‌گیری", callback_data="referral")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            f"""سلام کاربر @{username}
امیدوارم از ربات راضی باشید!

📖 راهنمای استفاده از ربات:
1. 💬 چت هوش مصنوعی: هر متنی بفرستید، ربات با هوش مصنوعی جواب می‌ده.
2. 📹 دانلود از اینستاگرام: لینک پست یا ریلز بفرستید تا ویدیو/عکس براتون ارسال بشه.
3. 🎵 دانلود از اسپاتیفای: لینک آهنگ بفرستید تا فایل MP3 براتون بیاد.
4. 🖼 دانلود از پینترست: لینک پین بفرستید تا عکس براتون ارسال بشه.
5. 🖌 ساخت عکس: از دستور /image <متن انگلیسی> (مثل /image flower) استفاده کنید.
6. 📞 پشتیبانی: با دکمه پشتیبانی، می‌تونید با ادمین چت کنید.

📜 قوانین:
- اسپم نکنید (بیش از ۳ پیام پشت‌سرهم ممنوع).
- محتوای غیرمجاز نفرستید، وگرنه بن می‌شید.
- فقط لینک‌های معتبر اینستاگرام، اسپاتیفای، یا پینترست بفرستید.
- برای ساخت عکس، فقط متن انگلیسی وارد کنید.

⚠️ محدودیت‌ها:
- چت: ۲۰۰ پیام در ۲۴ ساعت
- دانلود (اینستاگرام، اسپاتیفای، پینترست): ۵ درخواست در ۲۴ ساعت
- ساخت عکس: ۳ درخواست در ۲۴ ساعت
* کاربران ویژه هیچ محدودیتی ندارن.

🎉 اگه می‌خوای از ربات بدون محدودیت استفاده کنی، روی دکمه زیر بزن و زیرمجموعه جمع کن!""",
            reply_markup=reply_markup
        )
    elif query.data == "support":
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"in_support_mode": True}},
            upsert=True
        )
        support_chats_collection.update_one(
            {"user_id": user_id},
            {"$set": {"in_support_mode": True}},
            upsert=True
        )
        await query.message.reply_text("لطفاً پیام خودتون رو بنویسید تا به ادمین منتقل بشه.")
    elif query.data == "referral":
        referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
        keyboard = [
            [InlineKeyboardButton("اشتراک‌گذاری ربات", url=f"https://t.me/share/url?url={referral_link}&text=سلام دوست گلم\nمن نیاز به امتیاز دارم ممنون میشم با لینک من وارد ربات بشی تا بتونم بدون محدودیت از ربات استفاده کنم\nراستی خودت هم می‌تونی از قابلیت‌های خفن ربات استفاده کنی\nتستش ضرر نداره 😎")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            f"""🗣 با دعوت دوستانت، درآمد و امتیاز بگیر! 🎉
هر کسی که با لینک دعوت تو به ربات ملحق بشه،
تو امتیاز می‌گیری و به امکانات ویژه‌تری دسترسی پیدا می‌کنی! 🚀✨

🔗 لینک اختصاصی دعوتت رو به دوستات بفرست
🎁 هر دعوت = جوایز و مزایای بیشتر برای تو
💡 راحت، سریع و کاملاً رایگان""",
            reply_markup=reply_markup
        )

# دستور /image
async def image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_membership(update, user_id, context):
        await update.message.reply_text("لطفاً اول به کانال @netgoris ملحق بشید!")
        return
    if not await check_spam(user_id):
        await update.message.reply_text("لطفاً ۲ دقیقه صبر کنید!")
        return
    if not await check_limits(user_id, "image"):
        await update.message.reply_text("شما به حد مجاز ساخت عکس (۳ درخواست در ۲۴ ساعت) رسیدید!")
        return
    if len(context.args) == 0:
        await update.message.reply_text("لطفاً یه متن انگلیسی وارد کنید! مثال: /image flower")
        return
    text = " ".join(context.args)
    processing_msg = await update.message.reply_text("در حال پردازش...")
    image_url, error = await generate_image(text)
    if error:
        await processing_msg.delete()
        await update.message.reply_text(error)
        return
    if image_url:
        users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"image_requests": 1}}
        )
        await processing_msg.delete()
        await update.message.reply_photo(image_url)
    else:
        await processing_msg.delete()
        await update.message.reply_text("خطا در تولید عکس!")

# مدیریت پیام‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "کاربر"
    text = update.message.text

    # چک کردن بن
    user = users_collection.find_one({"user_id": user_id})
    if user and user.get("is_banned"):
        await update.message.reply_text("شما بن شدید و نمی‌تونید از ربات استفاده کنید!")
        return

    # چک کردن عضویت
    if not await check_membership(update, user_id, context):
        keyboard = [
            [InlineKeyboardButton("جوین به کانال", url="https://t.me/netgoris")],
            [InlineKeyboardButton("تأیید عضویت", callback_data="check_membership")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "برای استفاده از ربات، باید عضو کانال @netgoris باشید! 👇",
            reply_markup=reply_markup
        )
        return

    # چک کردن ضداسپم
    if not await check_spam(user_id):
        await update.message.reply_text("لطفاً ۲ دقیقه صبر کنید!")
        return

    # چک کردن حالت پشتیبانی
    support_chat = support_chats_collection.find_one({"user_id": user_id})
    if support_chat and support_chat.get("in_support_mode"):
        await context.bot.forward_message(ADMIN_ID, user_id, update.message.message_id)
        support_chats_collection.update_one(
            {"user_id": user_id},
            {"$set": {"last_message_id": update.message.message_id}}
        )
        if user_id not in messages:
            messages[user_id] = []
        messages[user_id].append({"text": text, "timestamp": time.time(), "is_bot": False})
        return

    # چک کردن لینک‌های دانلودر
    instagram_regex = r"(https?:\/\/(?:www\.)?instagram\.com\/.*)"
    spotify_regex = r"(https?:\/\/(?:open\.)?spotify\.com\/.*)"
    pinterest_regex = r"(https?:\/\/(?:www\.)?pinterest\.com\/.*)"
    if re.match(instagram_regex, text) or re.match(spotify_regex, text) or re.match(pinterest_regex, text):
        if not await check_limits(user_id, "download"):
            await update.message.reply_text("شما به حد مجاز دانلود (۵ درخواست در ۲۴ ساعت) رسیدید!")
            return
        processing_msg = await update.message.reply_text("در حال پردازش...")
        file_url = None
        if re.match(instagram_regex, text):
            file_url = await download_file(text, "instagram")
            if file_url and file_url.endswith((".mp4", ".m3u8")):
                await processing_msg.delete()
                await update.message.reply_video(file_url)
            elif file_url:
                await processing_msg.delete()
                await update.message.reply_photo(file_url)
        elif re.match(spotify_regex, text):
            file_url = await download_file(text, "spotify")
            if file_url:
                await processing_msg.delete()
                await update.message.reply_audio(file_url)
        elif re.match(pinterest_regex, text):
            file_url = await download_file(text, "pinterest")
            if file_url:
                await processing_msg.delete()
                await update.message.reply_photo(file_url)
        if file_url:
            users_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"download_requests": 1}}
            )
        else:
            await processing_msg.delete()
            await update.message.reply_text("خطا در دانلود فایل! لینک معتبر نیست.")
        return

    # مدیریت چت هوش مصنوعی
    if not await check_limits(user_id, "chat"):
        await update.message.reply_text("شما به حد مجاز چت (۲۰۰ پیام در ۲۴ ساعت) رسیدید!")
        return
    processing_msg = await update.message.reply_text("...")
    response = await get_chat_response(user_id, text)
    if response:
        await processing_msg.edit_text(response)
        users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"message_count": 1}}
        )
        if user_id not in messages:
            messages[user_id] = []
        messages[user_id].append({"text": text, "timestamp": time.time(), "is_bot": False})
        messages[user_id].append({"text": response, "timestamp": time.time(), "is_bot": True})
    else:
        await processing_msg.edit_text("متأسفم، مشکلی پیش اومد!")

# مدیریت پیام‌های ادمین
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    text = update.message.text
    if text.startswith("/ban "):
        try:
            target_id = int(text.split()[1])
            users_collection.update_one(
                {"user_id": target_id},
                {"$set": {"is_banned": True}}
            )
            await update.message.reply_text(f"کاربر {target_id} بن شد.")
        except:
            await update.message.reply_text("لطفاً آیدی معتبر وارد کنید!")
    elif text.startswith("/unban "):
        try:
            target_id = int(text.split()[1])
            users_collection.update_one(
                {"user_id": target_id},
                {"$set": {"is_banned": False}}
            )
            await update.message.reply_text(f"کاربر {target_id} آن‌بان شد.")
        except:
            await update.message.reply_text("لطفاً آیدی معتبر وارد کنید!")
    elif text.startswith("/addvip "):
        try:
            target_id = int(text.split()[1])
            users_collection.update_one(
                {"user_id": target_id},
                {"$set": {"is_vip": True}}
            )
            await update.message.reply_text(f"کاربر {target_id} به ویژه‌ها اضافه شد.")
        except:
            await update.message.reply_text("لطفاً آیدی معتبر وارد کنید!")
    elif text.startswith("/removevip "):
        try:
            target_id = int(text.split()[1])
            users_collection.update_one(
                {"user_id": target_id},
                {"$set": {"is_vip": False}}
            )
            await update.message.reply_text(f"کاربر {target_id} از ویژه‌ها حذف شد.")
        except:
            await update.message.reply_text("لطفاً آیدی معتبر وارد کنید!")
    elif text == "/stats":
        total_users = users_collection.count_documents({})
        banned_users = users_collection.count_documents({"is_banned": True})
        vip_users = users_collection.count_documents({"is_vip": True})
        await update.message.reply_text(
            f"📊 آمار ربات:\n"
            f"کاربران: {total_users}\n"
            f"بن‌شده‌ها: {banned_users}\n"
            f"ویژه‌ها: {vip_users}"
        )
    else:
        # پاسخ به کاربر در حالت پشتیبانی
        support_chat = support_chats_collection.find_one({"in_support_mode": True})
        if support_chat:
            target_id = support_chat["user_id"]
            await context.bot.send_message(
                target_id,
                f"ارسال از صاحب ربات:\n{update.message.text}",
                reply_to_message_id=support_chat.get("last_message_id")
            )
            if target_id not in messages:
                messages[target_id] = []
            messages[target_id].append({"text": update.message.text, "timestamp": time.time(), "is_bot": True})

# تنظیم Webhook
@app.route("/" + BOT_TOKEN, methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return {"status": "ok"}

# راه‌اندازی ربات
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("image", image))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=ADMIN_ID), handle_admin_message))
application.add_handler(CallbackQueryHandler(button))

# راه‌اندازی Flask
if __name__ == "__main__":
    application.bot.set_webhook(WEBHOOK_URL)
    app.run(host="0.0.0.0", port=PORT)
