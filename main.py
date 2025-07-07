import logging, aiohttp, time
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from pymongo import MongoClient

BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
CHANNEL_USERNAME = "@netgoris"
OWNER_ID = 5637609683
MONGO_LINK = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

logging.basicConfig(level=logging.INFO)
app = Application.builder().token(BOT_TOKEN).build()
db = MongoClient(MONGO_LINK).bot
users = db.users
support_state = {}

spam_tracker = {}  # ضد اسپم

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_member(context, user.id):
        btn = [[InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
               [InlineKeyboardButton("✅ تایید عضویت", callback_data="check_join")]]
        await update.message.reply_text("لطفاً ابتدا عضو کانال شوید 👇", reply_markup=InlineKeyboardMarkup(btn))
    else:
        btn = [[InlineKeyboardButton("📋 راهنما", callback_data="help_menu")]]
        await update.message.reply_text(f"سلام {user.first_name} عزیز، خوش آمدید ✨", reply_markup=InlineKeyboardMarkup(btn))
    if not users.find_one({"user_id": user.id}):
        users.insert_one({"user_id": user.id})
        await context.bot.send_message(OWNER_ID, f"👤 کاربر جدید:\n{user.mention_html()}", parse_mode="HTML")

async def is_member(context, user_id):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "check_join":
        if not await is_member(context, query.from_user.id):
            await query.answer("⛔ هنوز عضو نیستید!", show_alert=True)
        else:
            await query.message.delete()
            btn = [[InlineKeyboardButton("📋 راهنما", callback_data="help_menu")]]
            await query.message.reply_text(f"✅ عضویت تایید شد!\nبرای مشاهده راهنما دکمه زیر را بزنید.", reply_markup=InlineKeyboardMarkup(btn))
    elif query.data == "help_menu":
        btn = [[InlineKeyboardButton("⬅️ بازگشت", callback_data="final_msg")]]
        await query.message.edit_text(
            "📖 راهنمای ربات:\n"
            "- ارسال لینک اینستاگرام = دریافت ویدیو یا عکس\n"
            "- ارسال لینک اسپاتیفای = دریافت موزیک MP3\n"
            "- ارسال لینک پینترست = دریافت تصویر\n"
            "- دستور `عکس متن` (فقط انگلیسی) = ساخت عکس سفارشی\n\n"
            "⚠️ اسپم یا ارسال محتوای غیرمجاز ممنوع است.\n"
            "⚠️ درحال حاضر نسخه اولیه ربات است و بروزرسانی خواهد شد.\n"
            "📩 برای سوال یا مشکل دکمه پشتیبانی را بزنید.", 
            reply_markup=InlineKeyboardMarkup(btn), parse_mode="Markdown")
    elif query.data == "final_msg":
        btn = [[InlineKeyboardButton("📋 راهنما", callback_data="help_menu")]]
        await query.message.edit_text("ممنون از انتخاب ربات ما ❤️", reply_markup=InlineKeyboardMarkup(btn))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_id = update.effective_user.id

    # ضد اسپم
    now = time.time()
    if user_id not in spam_tracker:
        spam_tracker[user_id] = []
    spam_tracker[user_id] = [t for t in spam_tracker[user_id] if now - t < 120]
    spam_tracker[user_id].append(now)
    if len(spam_tracker[user_id]) > 4:
        await update.message.reply_text("⏳ لطفاً کمی صبر کنید (ضداسپم فعال شد).")
        return

    # پشتیبانی
    if msg == "پشتیبانی":
        support_state[user_id] = True
        await update.message.reply_text("✉️ لطفاً پیام خود را ارسال کنید. کیبورد بسته شد.",
                                        reply_markup=ReplyKeyboardMarkup([["لغو"]], resize_keyboard=True))
        return
    if support_state.get(user_id):
        if msg == "لغو":
            support_state.pop(user_id, None)
            await update.message.reply_text("✅ خارج شدید.", reply_markup=default_keyboard())
        else:
            await context.bot.send_message(OWNER_ID, f"📨 پیام پشتیبانی از {update.effective_user.mention_html()}:\n{msg}",
                                           parse_mode="HTML")
            support_state.pop(user_id, None)
            await update.message.reply_text("✅ پیام شما ارسال شد.", reply_markup=default_keyboard())
        return

    # لینک‌ها
    if "instagram.com" in msg:
        await insta(update)
    elif "spotify.com" in msg:
        await spotify(update)
    elif "pin.it" in msg or "pinterest" in msg:
        await pinterest(update)
    elif msg.lower().startswith("عکس "):
        await image_gen(update)
    else:
        await ai_chat(update)

async def ai_chat(update):
    txt = update.message.text
    urls = [
        f"https://starsshoptl.ir/Ai/index.php?text={txt}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={txt}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={txt}"
    ]
    for url in urls:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.text()
                    if data.strip():
                        await update.message.reply_text(data)
                        return
        except:
            continue
    await update.message.reply_text("❌ خطا در دریافت پاسخ.")

async def insta(update):
    url = update.message.text
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://pouriam.top/eyephp/instagram?url={url}") as resp:
                data = await resp.json()
                for link in data["links"]:
                    await update.message.reply_video(link) if link.endswith(".mp4") else await update.message.reply_photo(link)
    except:
        await update.message.reply_text("❌ خطا در دریافت اینستا.")

async def spotify(update):
    url = update.message.text
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://api.cactus-dev.ir/spotify.php?url={url}") as resp:
                data = await resp.json()
                await update.message.reply_audio(data["data"]["download_url"])
    except:
        await update.message.reply_text("❌ خطا در دریافت موزیک.")

async def pinterest(update):
    url = update.message.text
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://haji.s2025h.space/pin/?url={url}&client_key=keyvip") as resp:
                data = await resp.json()
                await update.message.reply_photo(data["download_url"])
    except:
        await update.message.reply_text("❌ خطا در دریافت تصویر.")

async def image_gen(update):
    txt = update.message.text.replace("عکس ", "")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://v3.api-free.ir/image/?text={txt}") as resp:
                data = await resp.json()
                await update.message.reply_photo(data["result"])
    except:
        await update.message.reply_text("❌ خطا در ساخت عکس.")

def default_keyboard():
    return ReplyKeyboardMarkup([["پشتیبانی"]], resize_keyboard=True)

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callbacks))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

if __name__ == "__main__":
    app.run_webhook(listen="0.0.0.0", port=10000, webhook_url="https://chatgpt-qg71.onrender.com")
