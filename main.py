import logging
import aiohttp
import asyncio
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from pymongo import MongoClient

# ====== تنظیمات ======
BOT_TOKEN        = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
CHANNEL_USERNAME = "@netgoris"
OWNER_ID         = 5637609683
MONGO_URI        = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL      = "https://chatgpt-qg71.onrender.com"
PORT             = 10000

# ====== لاگ ======
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== دیتابیس ======
client      = MongoClient(MONGO_URI)
db          = client["BotDB"]
users_col   = db["Users"]
spam_col    = db["Spam"]
ban_col     = db["Bans"]

# ====== برنامه ======
app = Application.builder().token(BOT_TOKEN).build()

# ====== دکمه‌ها ======
def join_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("✅ تأیید عضویت", callback_data="verify")]
    ])

def main_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("📚 راهنما", callback_data="help")]])

# ====== کمک‌کننده‌ها ======
async def is_member(uid, bot):
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ("member","administrator","creator")
    except:
        return False

async def check_spam(uid):
    now = datetime.utcnow()
    doc = spam_col.find_one({"_id": uid})
    if doc:
        times = [t for t in doc["times"] if (now - t).seconds<120]
        times.append(now)
        spam_col.update_one({"_id":uid},{"$set":{"times":times}})
        if len(times)>4:
            return True
    else:
        spam_col.insert_one({"_id":uid,"times":[now]})
    return False

# ====== هندلرها ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if ban_col.find_one({"_id":uid}):
        return await update.message.reply_text("⛔ شما مسدود شده‌اید.")
    if not await is_member(uid, context.bot):
        return await update.message.reply_text(
            "🔒 ابتدا در کانال عضو شوید:", reply_markup=join_buttons()
        )
    if not users_col.find_one({"_id":uid}):
        users_col.insert_one({"_id":uid})
        await context.bot.send_message(OWNER_ID, f"👤 کاربر جدید: @{update.effective_user.username}")
    await update.message.reply_text(
        "🎉 خوش آمدید! برای راهنما دکمه زیر را بزنید.",
        reply_markup=main_menu()
    )

async def verify_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = q.from_user.id
    await q.answer()
    if await is_member(uid, context.bot):
        await q.message.delete()
        await context.bot.send_message(uid, "✅ عضویت تأیید شد!", reply_markup=main_menu())
    else:
        await q.answer("هنوز عضو نیستید!", show_alert=True)

async def help_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = (
        "📚 **راهنما**\n\n"
        "• `/start` — شروع مجدد ربات\n"
        "• ارسال متن → پاسخ هوش مصنوعی\n"
        "• `عکس <متن انگلیسی>` → ساخت تصویر\n"
        "• ارسال لینک اینستا/اسپاتی/پینترست → دانلود محتوا\n\n"
        "⚠️ قوانین:\n"
        "- فقط لینک‌های اینستاگرام، اسپاتیفای، پینترست\n"
        "- متن عکس فقط انگلیسی\n"
        "- ۴ پیام پی‌درپی → ۲ دقیقه سکوت\n"
        "- رعایت ادب الزامی است\n\n"
        "ربات در نسخه اولیه است."
    )
    await q.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت", callback_data="back")]]), parse_mode="Markdown")

async def back_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.edit_text("✅ متشکریم!", reply_markup=main_menu())

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if ban_col.find_one({"_id":uid}): return
    if not await is_member(uid, context.bot): return
    if await check_spam(uid):
        return await update.message.reply_text("🚫 به دلیل ارسال مکرر، ۲ دقیقه سکوت.")

    # لینک‌ها و ساخت عکس همه با پیام پردازش
    async def process_and_delete(func, *args):
        pm = await update.message.reply_text("🔄 در حال پردازش، لطفاً صبر کنید...")
        try:
            await func(*args)
        finally:
            await pm.delete()

    if text.lower().startswith("عکس "):
        prompt = text.split(" ",1)[1]
        await process_and_delete(generate_image, prompt, update)
    elif "instagram.com" in text:
        await process_and_delete(download_instagram, text, update)
    elif "spotify.com" in text:
        await process_and_delete(download_spotify, text, update)
    elif "pinterest.com" in text or "pin.it" in text:
        await process_and_delete(download_pinterest, text, update)
    else:
        # چت هوش مصنوعی (بدون پردازش پیام)
        await ai_chat(text, update)

# ====== پیاده‌سازی سرویس‌ها ======
async def generate_image(prompt, update):
    if re.search(r'[\u0600-\u06FF]', prompt):
        return await update.message.reply_text("⚠️ متن باید انگلیسی باشد.")
    url = f"https://v3.api-free.ir/image/?text={prompt}"
    async with aiohttp.ClientSession() as s:
        r = await s.get(url)
        data = await r.json()
        if data.get("ok"):
            await update.message.reply_photo(data["result"])
        else:
            await update.message.reply_text("❌ خطا در ساخت عکس.")

async def download_instagram(url, update):
    api = f"https://pouriam.top/eyephp/instagram?url={url}"
    async with aiohttp.ClientSession() as s:
        r = await s.get(api); d = await r.json()
    if "links" in d:
        for link in d["links"]:
            await update.message.reply_document(link)
    else:
        await update.message.reply_text("❌ خطا یا لینک نامعتبر.")

async def download_spotify(url, update):
    api = f"http://api.cactus-dev.ir/spotify.php?url={url}"
    async with aiohttp.ClientSession() as s:
        r = await s.get(api); d = await r.json()
    dl = d.get("data",{}).get("track",{}).get("download_url")
    if dl:
        await update.message.reply_audio(dl)
    else:
        await update.message.reply_text("❌ خطا یا لینک نامعتبر.")

async def download_pinterest(url, update):
    api = f"https://haji.s2025h.space/pin/?url={url}&client_key=keyvip"
    async with aiohttp.ClientSession() as s:
        r = await s.get(api); d = await r.json()
    if d.get("status"):
        await update.message.reply_photo(d["download_url"])
    else:
        await update.message.reply_text("❌ خطا یا لینک نامعتبر.")

async def ai_chat(text, update):
    endpoints = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]
    for url in endpoints:
        try:
            async with aiohttp.ClientSession() as s:
                r = await s.get(url); res = await r.text()
            if res and len(res)>2:
                return await update.message.reply_text(res)
        except:
            continue
    await update.message.reply_text("❌ پاسخ دریافت نشد.")

# ====== ثبت هندلرها ======
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(verify_cb, pattern="^verify$"))
app.add_handler(CallbackQueryHandler(help_cb, pattern="^help$"))
app.add_handler(CallbackQueryHandler(back_cb, pattern="^back$"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

# ====== راه‌اندازی وب‌هوک ======
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook(request):
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.update_queue.put(update)
    return "OK"

if __name__ == "__main__":
    print("🚀 ربات فعال شد.")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )
