import logging
import re
import requests
import time
from telegram import (
    Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from pymongo import MongoClient

# اطلاعات شما:
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
OWNER_ID = 5637609683
CHANNEL_ID = "@netgoris"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"

# اتصال به دیتابیس:
client = MongoClient(f"mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["bot_database"]
users_col = db["users"]
spam_col = db["spam"]

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    member = await context.bot.get_chat_member(CHANNEL_ID, user_id)

    if member.status not in ["member", "administrator", "creator"]:
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.replace('@','')}")],
            [InlineKeyboardButton("✅ عضو شدم", callback_data="check")]
        ]
        await update.message.reply_text(
            "🚫 برای استفاده از ربات لطفاً ابتدا در کانال عضو شوید.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({"user_id": user_id})
        await context.bot.send_message(chat_id=OWNER_ID, text=f"🔔 کاربر جدید:\n[{update.effective_user.first_name}](tg://user?id={user_id})", parse_mode="Markdown")

    keyboard = [[InlineKeyboardButton("📚 راهنما", callback_data="help")],
                [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")]]
    await update.message.reply_text(
        f"🎉 سلام {update.effective_user.first_name} عزیز!\nبه ربات خوش آمدید.\nنسخه اولیه فعال است، ربات به‌مرور کامل‌تر می‌شود.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    member = await context.bot.get_chat_member(CHANNEL_ID, user_id)

    if member.status not in ["member", "administrator", "creator"]:
        await query.answer("❌ هنوز عضو نشدی!", show_alert=True)
    else:
        await query.message.delete()
        keyboard = [[InlineKeyboardButton("📚 راهنما", callback_data="help")],
                    [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")]]
        await query.message.reply_text(
            f"🎉 عضویت شما تایید شد!\nبه ربات خوش آمدید.\nنسخه اولیه فعال است، ربات به‌مرور کامل‌تر می‌شود.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    help_text = (
        "📚 *راهنمای جامع ربات:*\n\n"
        "🚀 ارسال لینک‌های اینستاگرام، اسپاتیفای یا پینترست برای دانلود مستقیم محتوا.\n"
        "🎨 ارسال دستور `عکس متن انگلیسی` برای ساخت تصویر.\n"
        "💡 چت آزاد با ربات، کافی‌ست پیام خود را بفرستید.\n\n"
        "⚠️ قوانین:\n"
        "➖ ارسال بیش از ۴ پیام پشت سر هم باعث ۲ دقیقه سکوت می‌شود.\n"
        "➖ عضویت در کانال الزامی‌ست.\n"
        "➖ در استفاده صحیح و محترمانه کوشا باشید.\n"
    )
    keyboard = [[InlineKeyboardButton("⬅️ بازگشت", callback_data="back")]]
    await query.message.edit_text(help_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [[InlineKeyboardButton("📚 راهنما", callback_data="help")],
                [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")]]
    await query.message.edit_text(
        "🏠 شما به منوی اصلی بازگشتید.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.reply_text(
        "💬 لطفاً سوال یا مشکل خود را ارسال کنید، تیم پشتیبانی پاسخگو خواهد بود."
    )
    context.user_data["support"] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # ضداسپم:
    now = int(time.time())
    spam_data = spam_col.find_one({"user_id": user_id})
    if spam_data:
        if now - spam_data["time"] < 120 and spam_data["count"] >= 4:
            return
        elif now - spam_data["time"] > 120:
            spam_col.update_one({"user_id": user_id}, {"$set": {"count": 1, "time": now}})
        else:
            spam_col.update_one({"user_id": user_id}, {"$inc": {"count": 1}})
    else:
        spam_col.insert_one({"user_id": user_id, "count": 1, "time": now})

    # پشتیبانی:
    if context.user_data.get("support"):
        await context.bot.send_message(OWNER_ID, f"📩 پیام جدید از [{update.effective_user.first_name}](tg://user?id={user_id}):\n{update.message.text}", parse_mode="Markdown")
        context.user_data.pop("support")
        await update.message.reply_text("✅ پیام شما ارسال شد.")
        return

    text = update.message.text

    if text.startswith("عکس "):
        query = text.replace("عکس ", "").strip()
        img = requests.get(f"https://v3.api-free.ir/image/?text={query}").json()
        if img["ok"]:
            await update.message.reply_photo(img["result"])
        else:
            await update.message.reply_text("❌ مشکلی در ساخت عکس پیش آمد.")
        return

    if "instagram.com" in text:
        res = requests.get(f"https://pouriam.top/eyephp/instagram?url={text}").json()
        for link in res.get("links", []):
            if link.endswith(".mp4"):
                await update.message.reply_video(link)
            else:
                await update.message.reply_photo(link)
        return

    if "spotify.com" in text:
        res = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={text}").json()
        if res.get("ok"):
            await update.message.reply_audio(res["data"]["download_url"])
        return

    if "pin.it" in text or "pinterest.com" in text:
        url = text
        res = requests.get(f"https://haji.s2025h.space/pin/?url={url}&client_key=keyvip").json()
        if res.get("status"):
            await update.message.reply_photo(res["download_url"])
        return

    # وب‌سرویس چت:
    services = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]
    for url in services:
        try:
            res = requests.get(url, timeout=5)
            if res.ok:
                await update.message.reply_text(res.text)
                return
        except:
            continue

    await update.message.reply_text("❓ متوجه منظورت نشدم یا لینک نامعتبر بود.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check, pattern="check"))
    app.add_handler(CallbackQueryHandler(help_menu, pattern="help"))
    app.add_handler(CallbackQueryHandler(back, pattern="back"))
    app.add_handler(CallbackQueryHandler(support, pattern="support"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        url_path="",
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    main()
