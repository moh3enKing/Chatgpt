import logging
import re
import requests
import time
import pymongo
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# اطلاعات
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
MONGO_URL = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "@netgoris"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"

# تنظیمات
logging.basicConfig(level=logging.INFO)
client = MongoClient(MONGO_URL)
db = client['botdb']
users = db['users']
spam = {}

# توابع چک عضویت
async def is_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=update.effective_user.id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_joined(update, context):
        btn = [
            [InlineKeyboardButton("💠 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join")]
        ]
        await update.message.reply_text("🔒 برای استفاده از ربات ابتدا در کانال عضو شوید.", reply_markup=InlineKeyboardMarkup(btn))
        return

    if not users.find_one({"user_id": user_id}):
        users.insert_one({"user_id": user_id})
        await context.bot.send_message(chat_id=OWNER_ID, text=f"🎉 کاربر جدید: {user_id}")

    btn = [[InlineKeyboardButton("📖 راهنما", callback_data="help")], [InlineKeyboardButton("🛠 پشتیبانی", callback_data="support")]]
    await update.message.reply_text(
        f"🎊 خوش آمدید {update.effective_user.first_name}!\nاز امکانات هوش مصنوعی، ساخت عکس و دانلودر لذت ببرید.",
        reply_markup=InlineKeyboardMarkup(btn)
    )

# دکمه ها
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check_join":
        if await is_joined(update, context):
            await query.edit_message_text("✅ عضویت تایید شد. خوش آمدید!")
            await start(update, context)
        else:
            await query.answer("⛔️ هنوز عضو نشدید!", show_alert=True)

    elif query.data == "help":
        btn = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
        text = (
            "📖 *راهنمای استفاده از ربات*\n\n"
            "🚀 این ربات در نسخه اولیه است و به مرور بروزرسانی می‌شود.\n"
            "✅ امکانات فعلی:\n"
            "- چت هوش مصنوعی: فقط کافیست پیام بفرستید.\n"
            "- ساخت عکس انگلیسی: دستور `عکس` بزنید و متن انگلیسی بنویسید.\n"
            "- دانلود اینستاگرام، اسپاتیفای و پینترست: لینک را ارسال کنید.\n\n"
            "⚠️ قوانین:\n"
            "- رعایت ادب الزامی است.\n"
            "- اسپم بیش از ۴ پیام پشت سر هم = سکوت ۲ دقیقه‌ای.\n"
            "- لینک غیرمجاز یا تبلیغ ارسال نکنید.\n"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(btn), parse_mode="Markdown")

    elif query.data == "back":
        btn = [[InlineKeyboardButton("📖 راهنما", callback_data="help")], [InlineKeyboardButton("🛠 پشتیبانی", callback_data="support")]]
        await query.edit_message_text(
            "🎊 بازگشت به صفحه اصلی.\nاز امکانات هوش مصنوعی، ساخت عکس و دانلودر لذت ببرید.",
            reply_markup=InlineKeyboardMarkup(btn)
        )

    elif query.data == "support":
        await query.message.reply_text("🛠 لطفا پیام خود را ارسال کنید. برای لغو /cancel بزنید.")
        context.user_data["support"] = True

# پیام‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if not await is_joined(update, context):
        return

    if spam.get(user_id, {"count": 0})["count"] >= 4:
        if time.time() - spam[user_id]["time"] < 120:
            return
        else:
            spam[user_id] = {"count": 0, "time": 0}

    spam.setdefault(user_id, {"count": 0, "time": 0})
    spam[user_id]["count"] += 1
    if spam[user_id]["count"] == 4:
        spam[user_id]["time"] = time.time()
        await update.message.reply_text("⏳ لطفا ۲ دقیقه صبر کنید.")
        return

    # پشتیبانی
    if context.user_data.get("support"):
        await context.bot.send_message(chat_id=OWNER_ID, text=f"🛠 پیام جدید از {user_id}:\n{text}")
        await update.message.reply_text("✅ پیام شما ارسال شد.")
        context.user_data["support"] = False
        return

    # چت AI
    if not text.startswith("عکس") and not re.match(r"https?://", text):
        for url in [
            f"https://starsshoptl.ir/Ai/index.php?text={text}",
            f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
            f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
        ]:
            try:
                r = requests.get(url, timeout=5).text
                if r:
                    await update.message.reply_text(r)
                    return
            except:
                continue
        await update.message.reply_text("⛔️ مشکلی در پاسخگویی پیش آمد.")
        return

    # ساخت عکس
    if text.startswith("عکس"):
        msg = text.replace("عکس", "").strip()
        if not msg:
            await update.message.reply_text("لطفاً متن انگلیسی برای ساخت عکس بنویسید.")
            return
        res = requests.get(f"https://v3.api-free.ir/image/?text={msg}").json()
        if res.get("ok"):
            await update.message.reply_photo(photo=res["result"])
        else:
            await update.message.reply_text("⛔️ ساخت عکس با خطا مواجه شد.")
        return

    # دانلودر اینستا
    if "instagram.com" in text:
        res = requests.get(f"https://pouriam.top/eyephp/instagram?url={text}").json()
        for link in res.get("links", []):
            if link.endswith(".mp4"):
                await update.message.reply_video(link)
            else:
                await update.message.reply_photo(link)
        return

    # اسپاتیفای
    if "spotify.com" in text:
        res = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={text}").json()
        if res.get("ok"):
            await update.message.reply_audio(audio=res["data"]["track"]["download_url"])
        return

    # پینترست
    if "pin.it" in text or "pinterest.com" in text:
        res = requests.get(f"https://haji.s2025h.space/pin/?url={text}&client_key=keyvip").json()
        if res.get("status"):
            await update.message.reply_photo(res["download_url"])
        return

    await update.message.reply_text("⛔️ لینک یا پیام نامعتبر.")

# شروع
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.start()
    await app.updater.start_webhook(listen="0.0.0.0", port=10000, url_path=BOT_TOKEN, webhook_url=WEBHOOK_URL + "/" + BOT_TOKEN)
    await app.updater.idle()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
