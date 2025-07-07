import logging
import asyncio
import requests
import time
from telegram import *
from telegram.ext import *
from pymongo import MongoClient

BOT_TOKEN = '8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0'
CHANNEL_ID = '@netgoris'
ADMIN_ID = 5637609683
DB_PASS = 'RIHPhDJPhd9aNJvC'
MONGO_URI = f"mongodb+srv://mohsenfeizi1386:{DB_PASS}@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client['TellGPT']
users = db['users']
support = db['support']
spam_data = {}

logging.basicConfig(level=logging.INFO)
bot_app = Application.builder().token(BOT_TOKEN).build()

# ضداسپم
def is_spam(user_id):
    now = time.time()
    history = spam_data.get(user_id, [])
    history = [t for t in history if now - t < 120]
    if len(history) >= 4:
        return True
    history.append(now)
    spam_data[user_id] = history
    return False

# چک عضویت
async def is_member(user_id):
    try:
        chat_member = await bot_app.bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ['member', 'creator', 'administrator']
    except:
        return False

# استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_member(user.id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.replace('@','')}")],
            [InlineKeyboardButton("✅ تایید عضویت", callback_data="check_join")]
        ])
        await update.message.reply_text("🚫 لطفا ابتدا عضو کانال شوید:", reply_markup=btn)
    else:
        users.update_one({'_id': user.id}, {'$set': {'username': user.username}}, upsert=True)
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 راهنما", callback_data="help")]
        ])
        await update.message.reply_text(
            f"🎉 {user.first_name} عزیز، به ربات ما خوش آمدید!\nاز ربات می‌توانید برای چت هوش مصنوعی، دانلود مستقیم و امکانات دیگر استفاده کنید.",
            reply_markup=markup
        )
        if users.count_documents({'_id': user.id}) == 0:
            await bot_app.bot.send_message(ADMIN_ID, f"🔔 کاربر جدید: @{user.username} ({user.id})")

# دکمه‌ها
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if query.data == "check_join":
        if not await is_member(user.id):
            await query.message.reply_text("⛔ هنوز عضو کانال نیستید!")
        else:
            await query.message.delete()
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 راهنما", callback_data="help")]
            ])
            await query.message.reply_text(
                f"🎉 {user.first_name} عزیز، به ربات ما خوش آمدید!\nبرای استفاده، از دکمه‌های زیر کمک بگیرید.",
                reply_markup=markup
            )
    elif query.data == "help":
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]])
        help_text = (
            "📋 راهنمای ربات TellGPT:\n\n"
            "🤖 امکانات:\n"
            "- چت با هوش مصنوعی (فقط کافیست پیام بفرستید)\n"
            "- دانلود اینستاگرام، اسپاتیفای، پینترست (لینک بفرستید)\n"
            "- ساخت عکس با دستور: `عکس متن`\n\n"
            "⚠️ قوانین:\n"
            "- ارسال اسپم ممنوع (۴ پیام پشت هم → ۲ دقیقه سکوت)\n"
            "- برای ساخت عکس فقط متن انگلیسی بزنید\n"
            "- لینک‌های غیرمجاز شناسایی نمی‌شود\n"
            "- ربات در نسخه اولیه است، منتظر آپدیت‌های بعدی باشید\n"
        )
        await query.message.edit_text(help_text, reply_markup=back_btn, parse_mode="Markdown")

    elif query.data == "back":
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 راهنما", callback_data="help")]
        ])
        await query.message.edit_text("✅ ممنون که ربات ما را انتخاب کردید، امیدوارم لذت ببرید!", reply_markup=markup)

# پیام‌ها
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if is_spam(user.id):
        return

    if not await is_member(user.id):
        return await start(update, context)

    if text.lower().startswith("عکس"):
        msg = await update.message.reply_text("🖼️ در حال ساخت تصویر...")
        query = text.split(maxsplit=1)[-1]
        res = requests.get(f"https://v3.api-free.ir/image/?text={query}").json()
        if res.get("ok"):
            await msg.edit_text(res["result"])
        else:
            await msg.edit_text("⛔ خطا در ساخت عکس")
        return

    # تشخیص لینک‌ها
    if "instagram.com" in text:
        msg = await update.message.reply_text("⏳ در حال پردازش اینستاگرام...")
        try:
            res = requests.get(f"https://pouriam.top/eyephp/instagram?url={text}").json()
            for link in res.get("links", []):
                await update.message.reply_text(link)
            await msg.delete()
        except:
            await msg.edit_text("⛔ خطا در دانلود اینستاگرام")
        return

    if "spotify.com" in text:
        msg = await update.message.reply_text("⏳ در حال پردازش اسپاتیفای...")
        try:
            res = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={text}").json()
            await update.message.reply_text(res["data"]["download_url"])
            await msg.delete()
        except:
            await msg.edit_text("⛔ خطا در اسپاتیفای")
        return

    if "pin.it" in text or "pinterest.com" in text:
        msg = await update.message.reply_text("⏳ در حال پردازش پینترست...")
        try:
            res = requests.get(f"https://haji.s2025h.space/pin/?url={text}&client_key=keyvip").json()
            await update.message.reply_text(res["download_url"])
            await msg.delete()
        except:
            await msg.edit_text("⛔ خطا در پینترست")
        return

    # چت هوش مصنوعی
    msg = await update.message.reply_text("...")
    for url in [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}",
    ]:
        try:
            res = requests.get(url, timeout=10).text
            if res:
                await msg.edit_text(res)
                return
        except:
            continue
    await msg.edit_text("⛔ خطا در پاسخ هوش مصنوعی")

# پشتیبانی
async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.message.chat.type != "private":
        return
    support.insert_one({"user_id": user.id})
    markup = ReplyKeyboardRemove()
    await update.message.reply_text("✉️ لطفا پیام خود را ارسال کنید. برای لغو، /cancel بزنید.", reply_markup=markup)

# دریافت پیام‌های پشتیبانی
async def support_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if support.find_one({"user_id": user.id}):
        await bot_app.bot.send_message(ADMIN_ID, f"📩 پیام از @{user.username}:\n\n{update.message.text}")
        support.delete_one({"user_id": user.id})
        markup = ReplyKeyboardMarkup([["پشتیبانی"]], resize_keyboard=True)
        await update.message.reply_text("✅ پیام شما ارسال شد.", reply_markup=markup)

# تنظیمات هندلرها
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(button))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
bot_app.add_handler(CommandHandler("cancel", start))
bot_app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, support_messages))
bot_app.add_handler(CommandHandler("پشتیبانی", support_cmd))

# اجرای وب‌هوک
async def run():
    await bot_app.bot.set_webhook("https://chatgpt-qg71.onrender.com")
    await bot_app.start()
    await bot_app.updater.start_polling()
    await bot_app.updater.idle()

if __name__ == "__main__":
    asyncio.run(run())
