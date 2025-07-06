import os
import time
import requests
from flask import Flask, request
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from pymongo import MongoClient

# اطلاعات شما
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
CHANNEL_ID = "@netgoris"
OWNER_ID = 5637609683
MONGODB_URI = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

app = Flask(__name__)
bot = Bot(BOT_TOKEN)

client = MongoClient(MONGODB_URI)
db = client['bot_db']
users = db['users']
spam = {}

# متن راهنما
HELP_TEXT = """
📖 راهنمای کامل استفاده از ربات:

✅ این ربات در نسخه آزمایشی قرار دارد و به‌مرور امکانات بیشتری اضافه خواهد شد.

⚙️ امکانات فعلی ربات:

➖ ارسال لینک اینستاگرام → دریافت مستقیم ویدیو یا عکس
➖ ارسال لینک اسپاتیفای → دریافت آهنگ با کیفیت اصلی
➖ ارسال لینک پینترست → دریافت عکس با کیفیت
➖ ارسال متن انگلیسی با دستور: عکس [متن] → ساخت تصویر اختصاصی
➖ ارسال هر متن دیگر → پاسخ هوش مصنوعی (چت آزاد)

⚠️ قوانین و نکات مهم:
🔹 برای ساخت عکس حتما متن را انگلیسی وارد کنید
🔹 ارسال بیش از ۴ پیام پشت سر هم → سکوت ۲ دقیقه‌ای برای کاربر
🔹 لینک‌های غیرمجاز یا ناشناس ارسال نکنید
🔹 در صورت بروز مشکل می‌توانید از دکمه «پشتیبانی» استفاده کنید

💡 همیشه به‌روز باشید؛ امکانات جدید به زودی اضافه می‌شود.

🌟 ممنون که از ربات ما استفاده می‌کنید.
"""

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        application.update_queue.put(update)
    return "ok"

async def check_join(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_join(user_id):
        buttons = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")],
            [InlineKeyboardButton("✅ تایید عضویت", callback_data="check_join")]
        ]
        await update.message.reply_text("لطفاً ابتدا در کانال عضو شوید 👇", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        if not users.find_one({"_id": user_id}):
            users.insert_one({"_id": user_id})
            await bot.send_message(OWNER_ID, f"کاربر جدید استارت کرد:\n{update.effective_user.mention_html()}", parse_mode="HTML")
        await send_welcome(update, context)

async def send_welcome(update, context):
    buttons = [[InlineKeyboardButton("📖 راهنما", callback_data="help")]]
    msg = await update.message.reply_text("🎉 به ربات خوش آمدید!\nاز امکانات هوش مصنوعی و دانلودر لذت ببرید.", reply_markup=InlineKeyboardMarkup(buttons))
    context.user_data["welcome_msg"] = msg.message_id

async def help_menu(update, context):
    query = update.callback_query
    await query.answer()
    buttons = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
    await bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text=HELP_TEXT, reply_markup=InlineKeyboardMarkup(buttons))

async def back_menu(update, context):
    query = update.callback_query
    await query.answer()
    buttons = [[InlineKeyboardButton("📖 راهنما", callback_data="help")]]
    await bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text="✅ ممنون که ربات ما رو انتخاب کردید.\nامیدواریم لذت ببرید!", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = time.time()
    msgs = spam.get(user_id, [])
    msgs = [t for t in msgs if now - t < 120]
    msgs.append(now)
    spam[user_id] = msgs
    if len(msgs) > 4:
        return

    text = update.message.text.lower()

    if "instagram.com" in text:
        await insta(update)
    elif "spotify.com" in text:
        await spotify(update)
    elif "pin.it" in text or "pinterest.com" in text:
        await pinterest(update)
    elif text.startswith("عکس "):
        await image_gen(update)
    else:
        await chat_ai(update)

async def insta(update):
    url = update.message.text
    r = requests.get(f"https://pouriam.top/eyephp/instagram?url={url}").json()
    try:
        for link in r["links"]:
            await update.message.reply_document(link)
    except:
        await update.message.reply_text("❌ خطا در دریافت اطلاعات اینستاگرام")

async def spotify(update):
    url = update.message.text
    r = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={url}").json()
    try:
        await update.message.reply_audio(r["data"]["download_url"])
    except:
        await update.message.reply_text("❌ خطا در دریافت آهنگ")

async def pinterest(update):
    url = update.message.text
    r = requests.get(f"https://haji.s2025h.space/pin/?url={url}&client_key=keyvip").json()
    try:
        await update.message.reply_document(r["download_url"])
    except:
        await update.message.reply_text("❌ خطا در دریافت عکس")

async def image_gen(update):
    text = update.message.text.replace("عکس ", "")
    r = requests.get(f"https://v3.api-free.ir/image/?text={text}").json()
    try:
        await update.message.reply_photo(r["result"])
    except:
        await update.message.reply_text("❌ خطا در ساخت عکس")

async def chat_ai(update):
    text = update.message.text
    urls = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]
    for u in urls:
        try:
            r = requests.get(u, timeout=5).text
            if r:
                await update.message.reply_text(r)
                return
        except:
            continue
    await update.message.reply_text("❌ خطا در پاسخ هوش مصنوعی")

async def button_handler(update, context):
    query = update.callback_query
    if query.data == "check_join":
        if await check_join(query.from_user.id):
            await bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
            await send_welcome(update, context)
        else:
            await query.answer("لطفاً ابتدا عضو کانال شوید!", show_alert=True)
    elif query.data == "help":
        await help_menu(update, context)
    elif query.data == "back":
        await back_menu(update, context)

async def error_handler(update, context):
    print(f"Error: {context.error}")

application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
application.add_error_handler(error_handler)

if __name__ == "__main__":
    application.run_webhook(port=10000, listen="0.0.0.0", webhook_url="https://chatgpt-qg71.onrender.com/")
