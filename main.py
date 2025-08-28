import os
import requests
from telebot import TeleBot, types
from flask import Flask, request

# توکن ربات (درست و واقعی)
TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
bot = TeleBot(TOKEN)
app = Flask(__name__)

PORT = int(os.environ.get("PORT", 1000))

# ======== مدیریت زبان ========
user_language = {}

LANGUAGES = {
    "فارسی": "fa",
    "English": "en"
}

MESSAGES = {
    "fa": {
        "welcome": "سلام! لطفاً زبان خود را انتخاب کنید:",
        "instruction": "برای جستجوی آهنگ، نام آهنگ، خواننده یا آلبوم را وارد کنید."
    },
    "en": {
        "welcome": "Hello! Please select your language:",
        "instruction": "To search for music, type the song name, artist, or album."
    }
}

# ======== صفحه استارت ========
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    for lang in LANGUAGES.keys():
        markup.add(types.InlineKeyboardButton(text=lang, callback_data=f"lang_{lang}"))
    bot.send_message(chat_id, "🌍 لطفاً زبان خود را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def language_choice(call):
    lang = call.data.split("_")[1]
    user_language[call.message.chat.id] = LANGUAGES[lang]
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=MESSAGES[LANGUAGES[lang]]["instruction"])

# ======== جستجوی آهنگ (نمونه تستی) ========
def search_music(query):
    # 🔴 فعلاً نتایج تستی برمی‌گردونیم
    # بعد میشه وصلش کرد به API سایت‌های واقعی
    results = [
        {
            "title": "Sample Song",
            "artist": "Test Artist",
            "year": "2025",
            "cover": "https://upload.wikimedia.org/wikipedia/commons/4/4f/Musical_notes.png",
            "mp3": "https://filesamples.com/samples/audio/mp3/sample3.mp3"
        }
    ]
    return results

@bot.message_handler(func=lambda m: True)
def handle_search(message):
    query = message.text
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "🔎 در حال جستجو...")
    tracks = search_music(query)
    bot.delete_message(chat_id, msg.message_id)

    if not tracks:
        bot.send_message(chat_id, "❌ هیچ آهنگی پیدا نشد.")
        return

    for track in tracks:
        caption = f"{track.get('title')} - {track.get('artist')} ({track.get('year')})\n🎵 @Tellgptvip_bot"
        try:
            bot.send_photo(chat_id, track.get("cover"), caption=caption)
            bot.send_audio(chat_id, track.get("mp3"),
                           title=track.get('title'),
                           performer=track.get('artist'))
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ خطا در ارسال آهنگ: {e}")

# ======== Flask برای Render ========
@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    json_str = request.get_data().decode('utf-8')
    update = types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

@app.route("/")
def index():
    return "Bot is running ✅"

# ======== راه‌اندازی Webhook ========
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://chatgpt-qg71.onrender.com/{TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
