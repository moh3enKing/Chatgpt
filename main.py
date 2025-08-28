import os
import threading
import requests
from flask import Flask
from bs4 import BeautifulSoup
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# تنظیمات اولیه
BOT_TOKEN = "توکن_ربات_تو"
PORT = int(os.environ.get("PORT", 1000))
LANGUAGES = {"fa": "🇮🇷 فارسی", "en": "🇬🇧 English"}
user_language = {}
user_last_query = {}
user_last_type = {}

# راه‌اندازی Flask برای هاست Render
flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return "🎵 Music Bot is running!"

# شروع ربات با انتخاب زبان
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(LANGUAGES["fa"], callback_data="lang_fa")],
        [InlineKeyboardButton(LANGUAGES["en"], callback_data="lang_en")]
    ]
    await update.message.reply_text(
        "لطفاً زبان خود را انتخاب کنید:\nPlease choose your language:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ذخیره زبان انتخاب‌شده
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split("_")[1]
    user_language[query.from_user.id] = lang_code

    if lang_code == "fa":
        await query.edit_message_text("🎉 خوش آمدید به ربات موزیک‌یاب!\nنام آهنگ، خواننده یا آلبوم را وارد کنید.")
    else:
        await query.edit_message_text("🎉 Welcome to the Music Finder Bot!\nPlease enter a song name, artist or album.")

# دریافت ورودی کاربر و تشخیص نوع جستجو
async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_language.get(user_id, "fa")
    query = update.message.text.strip()

    user_last_query[user_id] = query
    user_last_type[user_id] = "song"  # فرض اولیه: جستجوی آهنگ

    if lang == "fa":
        await update.message.reply_text("🔍 در حال جستجو برای آهنگ‌ها...")
    else:
        await update.message.reply_text("🔍 Searching for songs...")

    await search_and_send_results(update, context, query, lang)

# جستجو در سایت‌ها (نمونه‌سازی شده)
def fake_music_sites(query):
    # شبیه‌سازی نتایج از چند سایت
    return [
        {
            "title": f"{query} - Artist A",
            "artist": "Artist A",
            "year": "2022",
            "cover": "https://via.placeholder.com/300x300.png?text=Cover+A",
            "mp3": "https://example.com/musicA.mp3"
        },
        {
            "title": f"{query} - Artist B",
            "artist": "Artist B",
            "year": "2021",
            "cover": "https://via.placeholder.com/300x300.png?text=Cover+B",
            "mp3": "https://example.com/musicB.mp3"
        }
    ]

# ارسال نتایج جستجو
async def search_and_send_results(update: Update, context: ContextTypes.DEFAULT_TYPE, query, lang):
    results = fake_music_sites(query)

    for item in results:
        caption = f"🎵 {item['title']}\n👤 {item['artist']}\n📅 {item['year']}\n\nربات موزیک‌یاب @Tellgptvip_bot" if lang == "fa" else \
                  f"🎵 {item['title']}\n👤 {item['artist']}\n📅 {item['year']}\n\nMusic Finder Bot @Tellgptvip_bot"

        await context.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=item["cover"],
            caption=caption
        )

        await context.bot.send_audio(
            chat_id=update.message.chat_id,
            audio=item["mp3"],
            title=item["title"],
            performer=item["artist"],
            caption="🎧 کیفیت ۳۲۰kbps" if lang == "fa" else "🎧 320kbps quality"
        )

# اجرای Flask در رشته جداگانه
def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT)

# اجرای ربات تلگرام
def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(set_language))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))
    app.run_polling()

# اجرای همزمان Flask و ربات
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
