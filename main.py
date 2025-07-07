import logging
from telegram import (
    Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import aiohttp
import asyncio
from pymongo import MongoClient
from datetime import datetime, timedelta

# توکن و دیتابیس
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
DB_PASS = "RIHPhDJPhd9aNJvC"
MONGO_URI = f"mongodb+srv://mohsenfeizi1386:{DB_PASS}@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"

client = MongoClient(MONGO_URI)
db = client["TelegramBot"]
users = db["users"]
spam = {}

logging.basicConfig(level=logging.INFO)
bot_app = Application.builder().token(BOT_TOKEN).build()


# دکمه‌های ثابت
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💡 راهنما", callback_data="help")],
        [InlineKeyboardButton("🆘 پشتیبانی", callback_data="support")]
    ])


# چک عضویت
async def is_member(user_id):
    try:
        chat_member = await bot_app.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except:
        return False


# پیام استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    member = await is_member(user.id)

    if not member:
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("✅ تایید عضویت", callback_data="verify")]
        ])
        msg = await update.message.reply_text("⚠️ لطفا ابتدا در کانال عضو شوید سپس تایید کنید.", reply_markup=buttons)
        context.user_data["join_msg"] = msg.message_id
        return

    # ذخیره کاربر
    if not users.find_one({"user_id": user.id}):
        users.insert_one({"user_id": user.id, "joined": datetime.utcnow()})
        await bot_app.bot.send_message(OWNER_ID, f"👤 کاربر جدید: {user.full_name} - @{user.username}")

    msg = await update.message.reply_text(
        f"👋 سلام {user.first_name} عزیز!\nخوش آمدید به ربات ما.",
        reply_markup=main_menu()
    )
    context.user_data["welcome_msg"] = msg.message_id


# تایید عضویت
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if query.data == "verify":
        if await is_member(user.id):
            try:
                await bot_app.bot.delete_message(user.id, context.user_data["join_msg"])
            except:
                pass
            msg = await query.message.reply_text(
                f"✅ عضویت تایید شد.\nاز امکانات ربات استفاده کنید.",
                reply_markup=main_menu()
            )
            context.user_data["welcome_msg"] = msg.message_id
        else:
            await query.message.reply_text("🚫 شما هنوز عضو کانال نیستید!")

    elif query.data == "help":
        text = (
            "📌 راهنمای استفاده از ربات:\n\n"
            "- ارسال متن: پاسخ هوش مصنوعی دریافت می‌کنید.\n"
            "- ارسال لینک اینستاگرام، اسپاتیفای یا پینترست: دانلود مستقیم.\n"
            "- دستور ساخت عکس: `عکس متن`\n"
            "- لینک‌های ناشناس: خطا می‌دهد.\n\n"
            "⚠️ قوانین:\n"
            "⛔ ارسال اسپم بیش از ۴ پیام پشت سر هم = سکوت ۲ دقیقه\n"
            "🚀 این نسخه اولیه ربات است و بروزرسانی خواهد شد.\n"
        )
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="back")]
        ]))

    elif query.data == "back":
        msg = await query.message.edit_text(
            "🌟 ممنون که ربات ما رو انتخاب کردید.\nدر خدمت شما هستیم.",
            reply_markup=main_menu()
        )
        context.user_data["welcome_msg"] = msg.message_id

    elif query.data == "support":
        await bot_app.bot.send_message(user.id, "📝 لطفا پیام خود را ارسال کنید، پشتیبانی به زودی پاسخ می‌دهد.")
        context.user_data["support"] = True


# پیام‌های عادی
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if not await is_member(user.id):
        return

    # ضد اسپم
    now = datetime.utcnow()
    msgs = spam.get(user.id, [])
    msgs = [t for t in msgs if now - t < timedelta(minutes=2)]
    msgs.append(now)
    spam[user.id] = msgs

    if len(msgs) > 4:
        await update.message.reply_text("⛔ لطفا اسپم ارسال نکنید. ۲ دقیقه سکوت.")
        return

    # پشتیبانی
    if context.user_data.get("support"):
        await bot_app.bot.send_message(OWNER_ID, f"💬 پیام کاربر:\n{user.full_name} - @{user.username}\n{text}")
        context.user_data["support"] = False
        await update.message.reply_text("✅ پیام شما ارسال شد.")
        return

    # تشخیص لینک‌ها
    if "instagram.com" in text:
        await handle_instagram(update, text)
    elif "spotify.com" in text:
        await handle_spotify(update, text)
    elif "pin.it" in text or "pinterest.com" in text:
        await handle_pinterest(update, text)
    elif text.startswith("عکس "):
        await handle_image(update, text[4:])
    else:
        await handle_ai(update, text)


# هوش مصنوعی با fallback
async def handle_ai(update, text):
    urls = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]
    for url in urls:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        msg = await resp.text()
                        if msg.strip():
                            await update.message.reply_text(msg)
                            return
        except:
            continue
    await update.message.reply_text("❌ مشکلی در پاسخ‌دهی هوش مصنوعی پیش آمد.")


# اینستاگرام
async def handle_instagram(update, url):
    api = f"https://pouriam.top/eyephp/instagram?url={url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as resp:
                data = await resp.json()
                for link in data["links"]:
                    await update.message.reply_video(link) if ".mp4" in link else await update.message.reply_photo(link)
    except:
        await update.message.reply_text("❌ دریافت محتوا از اینستاگرام ممکن نشد.")


# اسپاتیفای
async def handle_spotify(update, url):
    api = f"http://api.cactus-dev.ir/spotify.php?url={url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as resp:
                data = await resp.json()
                await update.message.reply_audio(data["data"]["download_url"])
    except:
        await update.message.reply_text("❌ دانلود از اسپاتیفای ممکن نشد.")


# پینترست
async def handle_pinterest(update, url):
    api = f"https://haji.s2025h.space/pin/?url={url}&client_key=keyvip"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as resp:
                data = await resp.json()
                await update.message.reply_photo(data["download_url"])
    except:
        await update.message.reply_text("❌ دریافت عکس از پینترست ممکن نشد.")


# ساخت عکس
async def handle_image(update, text):
    api = f"https://v3.api-free.ir/image/?text={text}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as resp:
                data = await resp.json()
                await update.message.reply_photo(data["result"])
    except:
        await update.message.reply_text("❌ تولید عکس ممکن نشد.")


# شروع ربات
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(handle_buttons))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


if __name__ == "__main__":
    bot_app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=WEBHOOK_URL
    )
