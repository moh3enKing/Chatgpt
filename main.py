import os
import time
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from pymongo import MongoClient
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0")
ADMIN_ID = 5637609683
CHANNEL_ID = "@netgoris"
DB_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# اتصال به دیتابیس
client = MongoClient(DB_URI)
db = client["telegram_bot"]
users_collection = db["users"]

# توابع کمکی
def is_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    try:
        member = context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def check_spam(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_data = users_collection.find_one({"user_id": user_id}) or {"user_id": user_id, "msg_count": 0, "last_msg_time": 0, "blocked_until": 0}
    current_time = time.time()
    
    if current_time < user_data.get("blocked_until", 0):
        return True
    if current_time - user_data["last_msg_time"] < 5:
        user_data["msg_count"] += 1
    else:
        user_data["msg_count"] = 1
    
    user_data["last_msg_time"] = current_time
    if user_data["msg_count"] >= 4:
        user_data["blocked_until"] = current_time + 120  # 2 دقیقه
        users_collection.update_one({"user_id": user_id}, {"$set": user_data}, upsert=True)
        return True
    
    users_collection.update_one({"user_id": user_id}, {"$set": user_data}, upsert=True)
    return False

# خوش‌آمدگویی
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_member(update, context):
        keyboard = [
            [InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_ID[1:]}")],
            [InlineKeyboardButton("تأیید عضویت", callback_data="check_membership")]
        ]
        await update.message.reply_text("لطفاً ابتدا در کانال @netgoris عضو شوید!", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # اعلان به مدیر
    if not users_collection.find_one({"user_id": user_id}):
        await context.bot.send_message(ADMIN_ID, f"کاربر جدید: {user_id}")
        users_collection.insert_one({"user_id": user_id, "msg_count": 0, "last_msg_time": 0, "blocked_until": 0, "support_mode": False})
    
    keyboard = [[InlineKeyboardButton("راهنما", callback_data="guide")], [InlineKeyboardButton("پشتیبانی", callback_data="support")]]
    await update.message.reply_text(
        "سلام! به ربات ما خوش آمدید 🎉\nاز شما تشکر می‌کنیم که همراه ما هستید!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# بررسی عضویت
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if is_member(update, context):
        await query.message.delete()
        keyboard = [[InlineKeyboardButton("راهنما", callback_data="guide")], [InlineKeyboardButton("پشتیبانی", callback_data="support")]]
        await context.bot.send_message(
            query.from_user.id,
            "سلام! به ربات ما خوش آمدید 🎉\nاز شما تشکر می‌کنیم که همراه ما هستید!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.answer("شما هنوز عضو کانال نیستید!", show_alert=True)

# راهنما
async def guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    guide_text = (
        "🎯 **راهنمای استفاده از ربات**\n"
        "1. برای چت با هوش مصنوعی، متن خود را بفرستید.\n"
        "2. برای دانلود، لینک اینستاگرام، اسپاتیفای یا پینترست بفرستید.\n"
        "3. برای تولید تصویر، متن مورد نظر را ارسال کنید.\n\n"
        "⚠️ **اخطارها و قوانین**\n"
        "- فقط از لینک‌های معتبر اینستاگرام، اسپاتیفای و پینترست استفاده کنید.\n"
        "- ارسال پیام‌های اسپم ممنوع است (حداکثر ۴ پیام پیاپی).\n"
        "- هرگونه تخلف منجر به مسدود شدن می‌شود.\n\n"
        "ما همیشه در خدمت شما هستیم! 🌟"
    )
    keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back")]]
    await query.edit_message_text(guide_text, reply_markup=InlineKeyboardMarkup(keyboard))

# بازگشت به منوی اصلی
async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [[InlineKeyboardButton("راهنما", callback_data="guide")], [InlineKeyboardButton("پشتیبانی", callback_data="support")]]
    await query.edit_message_text(
        "سلام! به ربات ما خوش آمدید 🎉\nاز شما تشکر می‌کنیم که همراه ما هستید!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# پشتیبانی
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    users_collection.update_one({"user_id": user_id}, {"$set": {"support_mode": True}})
    await query.edit_message_text("لطفاً پیام خود را برای پشتیبانی ارسال کنید. برای خروج '/cancel' را بفرستید.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if check_spam(user_id, context):
        await update.message.reply_text("شما به دلیل ارسال پیام‌های پیاپی به مدت ۲ دقیقه مسدود شدید!")
        return
    
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data.get("support_mode", False):
        if text == "/cancel":
            users_collection.update_one({"user_id": user_id}, {"$set": {"support_mode": False}})
            keyboard = [[InlineKeyboardButton("راهنما", callback_data="guide")], [InlineKeyboardButton("پشتیبانی", callback_data="support")]]
            await update.message.reply_text("شما از حالت پشتیبانی خارج شدید!", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await context.bot.send_message(ADMIN_ID, f"پیام از {user_id}:\n{text}")
            await update.message.reply_text("پیام شما به مدیر ارسال شد!")
        return
    
    if not is_member(update, context):
        await update.message.reply_text("لطفاً ابتدا در کانال @netgoris عضو شوید!")
        return
    
    # چت هوش مصنوعی
    for url in [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]:
        try:
            response = requests.get(url, timeout=5).text
            await update.message.reply_text(response)
            return
        except:
            continue
    
    # دانلودرها
    if "instagram.com" in text:
        try:
            response = requests.get(f"https://pouriam.top/eyephp/instagram?url={text}").json()
            for link in response["links"]:
                await update.message.reply_video(link) if link.endswith(".mp4") else await update.message.reply_photo(link)
            return
        except Exception as e:
            await update.message.reply_text(f"خطا در دانلود از اینستاگرام: {str(e)}")
    
    elif "spotify.com" in text:
        try:
            response = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={text}").json()
            await update.message.reply_audio(response["data"]["track"]["download_url"])
            return
        except Exception as e:
            await update.message.reply_text(f"خطا در دانلود از اسپاتیفای: {str(e)}")
    
    elif "pinterest.com" in text:
        try:
            response = requests.get(f"https://haji.s2025h.space/pin/?url={text}&client_key=keyvip").json()
            await update.message.reply_photo(response["download_url"])
            return
        except Exception as e:
            await update.message.reply_text(f"خطا در دانلود از پینترست: {str(e)}")
    
    # تولید تصویر
    try:
        response = requests.get(f"https://v3.api-free.ir/image/?text={text}").json()
        await update.message.reply_photo(response["result"])
        return
    except Exception as e:
        await update.message.reply_text(f"خطا در تولید تصویر: {str(e)}")

# پنل مدیریت
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("لطفاً متن پیام را وارد کنید: /admin <متن>")
        return
    context.user_data["admin_msg"] = " ".join(context.args)
    keyboard = [[InlineKeyboardButton("تأیید و ارسال", callback_data="send_admin_msg")]]
    await update.message.reply_text(f"پیام: {context.user_data['admin_msg']}\nتأیید کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_admin_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    msg = context.user_data.get("admin_msg", "")
    for user in users_collection.find():
        try:
            await context.bot.send_message(user["user_id"], msg)
        except:
            continue
    await query.edit_message_text("پیام با موفقیت ارسال شد!")

# تنظیم وب‌هوک برای Render
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
    app.add_handler(CallbackQueryHandler(guide, pattern="guide"))
    app.add_handler(CallbackQueryHandler(back, pattern="back"))
    app.add_handler(CallbackQueryHandler(support, pattern="support"))
    app.add_handler(CallbackQueryHandler(send_admin_msg, pattern="send_admin_msg"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تنظیم وب‌هوک
    app.run_webhook(
        listen="0.0.0.0",
        port=1000,
        url_path=TOKEN,
        webhook_url=f"https://chatgpt-qg71.onrender.com/{TOKEN}"
    )

if __name__ == "__main__":
    main()
