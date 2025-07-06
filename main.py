from flask import Flask, request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import threading
import requests
import os

# ============================= تنظیمات =============================
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
DOMAIN = "https://chatgpt-qg71.onrender.com"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{DOMAIN}{WEBHOOK_PATH}"
PORT = 10000

bot = Bot(token=BOT_TOKEN)

# ============================= ساخت ربات =============================
application = ApplicationBuilder().token(BOT_TOKEN).build()

# ============================= دستورات =============================

# استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/netgoris")],
        [InlineKeyboardButton("✅ تایید عضویت", callback_data="check_join")]
    ]
    await update.message.reply_text(
        "👋 سلام! لطفاً ابتدا در کانال ما عضو شوید.\nبدون عضویت ربات کار نخواهد کرد.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# بررسی عضویت
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    member = await bot.get_chat_member(chat_id="@netgoris", user_id=query.from_user.id)
    
    if member.status in ["member", "administrator", "creator"]:
        await query.edit_message_text(
            "🎉 خوش آمدید!\n\n✅ شما با موفقیت عضو شدید.\nبرای استفاده از امکانات، دستورات زیر را امتحان کنید:\n/help"
        )
    else:
        await query.answer("⚠️ هنوز عضو کانال نشدید!", show_alert=True)

# راهنما
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 راهنمای استفاده از ربات:\n\n"
        "✅ ارسال هر نوع پیام متنی: پاسخ هوش مصنوعی\n"
        "✅ ارسال لینک اینستاگرام: دریافت ویدیو یا عکس\n"
        "✅ ارسال لینک اسپاتیفای: دریافت موزیک\n"
        "✅ ارسال لینک پینترست: دریافت تصویر\n"
        "✅ دستور: `عکس متن انگلیسی`\n"
        "ساخت تصویر آنلاین\n\n"
        "⚠️ توجه: برای ساخت عکس، متن باید انگلیسی باشد.\n"
        "⚡️ این نسخه اولیه ربات است و به‌زودی امکانات بیشتری اضافه می‌شود."
    )
    await update.message.reply_text(text)

# پاسخ به متن
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    if text.startswith("عکس "):
        query = text.replace("عکس ", "")
        url = f"https://v3.api-free.ir/image/?text={query}"
        res = requests.get(url).json()
        
        if res.get("ok"):
            await update.message.reply_photo(photo=res["result"])
        else:
            await update.message.reply_text("⚠️ خطا در ساخت تصویر.")
    
    elif "instagram.com" in text:
        res = requests.get(f"https://pouriam.top/eyephp/instagram?url={text}").json()
        if res.get("links"):
            for link in res["links"]:
                if link.endswith(".mp4"):
                    await update.message.reply_video(video=link)
                else:
                    await update.message.reply_photo(photo=link)
        else:
            await update.message.reply_text("⚠️ خطا در دریافت از اینستاگرام.")
    
    elif "spotify.com" in text:
        res = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={text}").json()
        if res.get("ok"):
            await update.message.reply_audio(audio=res["data"]["track"]["download_url"])
        else:
            await update.message.reply_text("⚠️ خطا در دریافت موزیک.")
    
    elif "pin.it" in text or "pinterest.com" in text:
        res = requests.get(f"https://haji.s2025h.space/pin/?url={text}&client_key=keyvip").json()
        if res.get("status"):
            await update.message.reply_photo(photo=res["download_url"])
        else:
            await update.message.reply_text("⚠️ خطا در دریافت تصویر پینترست.")
    
    else:
        # چت هوش مصنوعی fallback
        msg = None
        for api in [
            f"https://starsshoptl.ir/Ai/index.php?text={text}",
            f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
            f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
        ]:
            try:
                res = requests.get(api).text
                if res:
                    msg = res
                    break
            except:
                continue
        
        if msg:
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("⚠️ خطا در پاسخ‌دهی هوش مصنوعی.")

# ============================= هندلرها =============================
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, start))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.COMMAND, help_command))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.add_handler(MessageHandler(filters.ALL, handle_message))

# دکمه‌های شیشه‌ای
from telegram.ext import CallbackQueryHandler
application.add_handler(CallbackQueryHandler(button))

# ============================= سرور Flask =============================
app = Flask(__name__)

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    application.update_queue.put_nowait(update)
    return "ok", 200

# ============================= اجرا =============================
def run_flask():
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}")
    threading.Thread(target=run_flask).start()
    application.run_polling()
