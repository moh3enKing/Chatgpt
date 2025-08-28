import os
import requests
from telebot import TeleBot, types
from flask import Flask, request

TOKEN = "توکن_ربات_تو_اینجا_بزار"
bot = TeleBot(TOKEN)
app = Flask(__name__)

PORT = int(os.environ.get("PORT", 1000))

# ======== مدیریت زبان ========
user_language = {}  # ذخیره زبان کاربر

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
    bot.send_message(chat_id, "سلام! لطفاً زبان خود را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def language_choice(call):
    lang = call.data.split("_")[1]
    user_language[call.message.chat.id] = LANGUAGES[lang]
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=MESSAGES[LANGUAGES[lang]]["instruction"])

# ======== جستجوی آهنگ ========
# لیست سایت‌ها (نمونه، باید API یا Web Scraping واقعی داشته باشی)
IRANIAN_SITES = [
    "https://www.radiojavan.com/api/search?q={}",
    "https://www.beeptunes.com/api/search?q={}",
    "https://www.persianmusic.com/api/search?q={}"
]

INTERNATIONAL_SITES = [
    "https://api.soundcloud.com/tracks?q={}&client_id=CLIENT_ID",
    "https://api.spotify.com/v1/search?q={}&type=track",
    "https://api.jamendo.com/v3.0/tracks/?client_id=CLIENT_ID&format=json&name={}"
]

def search_music(query):
    results = []
    # این قسمت نمونه هست و باید با API واقعی جایگزین شود
    for site in IRANIAN_SITES + INTERNATIONAL_SITES:
        url = site.format(query)
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                # فرض کنیم data لیستی از آهنگ‌ها با keys: title, artist, year, cover, mp3
                for track in data.get("tracks", []):
                    results.append(track)
        except:
            continue
    return results[:10]  # فقط ۱۰ نتیجه اول

@bot.message_handler(func=lambda m: True)
def handle_search(message):
    query = message.text
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "در حال جستجو…")
    tracks = search_music(query)
    bot.delete_message(chat_id, msg.message_id)

    if not tracks:
        bot.send_message(chat_id, "هیچ آهنگی پیدا نشد.")
        return

    for track in tracks:
        caption = f"{track.get('title')} - {track.get('artist')} ({track.get('year')})\n@Tellgptvip_bot"
        try:
            bot.send_photo(chat_id, track.get("cover"), caption=caption)
            bot.send_audio(chat_id, track.get("mp3"), title=track.get('title'), performer=track.get('artist'))
        except:
            continue

# ======== Flask برای Render ========
@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    json_str = request.get_data().decode('utf-8')
    update = types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

@app.route("/")
def index():
    return "Bot is running"

# ======== راه‌اندازی Webhook ========
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://YOUR_RENDER_APP_NAME.onrender.com/{TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
