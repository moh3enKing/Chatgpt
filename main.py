import logging
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import aiohttp
import os

# تنظیمات
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_USERNAME = "netgoris"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com/webhook"

# لاگ
logging.basicConfig(level=logging.INFO)
bot_app = Application.builder().token(BOT_TOKEN).build()

# Flask
app = Flask(__name__)

# استارت با چک جوین
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_member = await bot_app.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
    if chat_member.status in ["left", "kicked"]:
        buttons = [
            [InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("✅ عضویت انجام شد", callback_data="verify")]
        ]
        await update.message.reply_text(
            "⚠️ برای استفاده از ربات لطفاً ابتدا عضو کانال ما شوید.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await welcome_message(update)

# پیام خوش‌آمد
async def welcome_message(update):
    buttons = [[InlineKeyboardButton("📖 راهنما", callback_data="help")]]
    await update.message.reply_text(
        "🎉 خوش آمدید! از ربات ما لذت ببرید.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# هندل دکمه‌ها
@bot_app.callback_query_handler()
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "verify":
        chat_member = await bot_app.bot.get_chat_member(f"@{CHANNEL_USERNAME}", query.from_user.id)
        if chat_member.status in ["left", "kicked"]:
            await query.edit_message_text("❌ هنوز عضو نشدید! لطفاً عضو کانال شوید.")
        else:
            await query.message.delete()
            await welcome_message(query.message)
    elif query.data == "help":
        buttons = [[InlineKeyboardButton("🏡 بازگشت", callback_data="back")]]
        await query.edit_message_text(
            "📚 راهنمای استفاده از ربات:\n"
            "- برای دانلود از اینستاگرام، اسپاتیفای، یا پینترست کافیست لینک را ارسال کنید.\n"
            "- برای ساخت عکس دستور `عکس متن` را بنویسید (متن انگلیسی باشد).\n"
            "- این ربات در نسخه آزمایشی است و آپدیت می‌شود.\n"
            "- قوانین:\n"
            "  * ارسال لینک غیرمجاز ممنوع است.\n"
            "  * رعایت ادب الزامی است.\n",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif query.data == "back":
        buttons = [[InlineKeyboardButton("📖 راهنما", callback_data="help")]]
        await query.edit_message_text(
            "✅ ممنون که از ربات ما استفاده می‌کنید، هر مشکلی داشتید از پشتیبانی بپرسید.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

# هندل پیام‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "instagram.com" in text:
        await download_instagram(update, text)
    elif "spotify.com" in text:
        await download_spotify(update, text)
    elif "pin.it" in text or "pinterest.com" in text:
        await download_pinterest(update, text)
    elif text.startswith("عکس"):
        await generate_image(update, text.replace("عکس", "").strip())
    else:
        await ai_chat(update, text)

# دانلود اینستاگرام
async def download_instagram(update, url):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://pouriam.top/eyephp/instagram?url={url}") as resp:
            data = await resp.json()
            if data.get("links"):
                for link in data["links"]:
                    await update.message.reply_document(link)
            else:
                await update.message.reply_text("⚠️ لینک نامعتبر یا خطا در دانلود.")

# دانلود اسپاتیفای
async def download_spotify(update, url):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://api.cactus-dev.ir/spotify.php?url={url}") as resp:
            data = await resp.json()
            if data.get("data") and data["data"].get("download_url"):
                await update.message.reply_document(data["data"]["download_url"])
            else:
                await update.message.reply_text("⚠️ لینک نامعتبر یا خطا در دانلود.")

# دانلود پینترست
async def download_pinterest(update, url):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://haji.s2025h.space/pin/?url={url}&client_key=keyvip") as resp:
            data = await resp.json()
            if data.get("download_url"):
                await update.message.reply_document(data["download_url"])
            else:
                await update.message.reply_text("⚠️ لینک نامعتبر یا خطا در دانلود.")

# ساخت عکس
async def generate_image(update, text):
    if not text:
        await update.message.reply_text("⚠️ لطفاً بعد از دستور 'عکس' متن انگلیسی وارد کنید.")
        return
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://v3.api-free.ir/image/?text={text}") as resp:
            data = await resp.json()
            if data.get("result"):
                await update.message.reply_document(data["result"])
            else:
                await update.message.reply_text("⚠️ خطا در ساخت تصویر.")

# چت هوش مصنوعی
async def ai_chat(update, text):
    urls = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]
    for url in urls:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    res_text = await resp.text()
                    if res_text:
                        await update.message.reply_text(res_text)
                        return
        except:
            continue
    await update.message.reply_text("⚠️ خطا در پاسخ هوش مصنوعی.")

# ثبت هندلرها
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT, handle_message))

# مسیر وب‌هوک
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.json, bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "OK"

# ران
if __name__ == "__main__":
    bot_app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        url_path="webhook",
        webhook_url=WEBHOOK_URL
    )
    app.run(host="0.0.0.0", port=10000)
