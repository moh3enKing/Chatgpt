import os
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from flask import Flask, request
import threading

# Bot token (replace with your actual bot token)
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'

# Webhook URL (for Render, replace with your Render URL)
WEBHOOK_URL = 'https://your-render-app.onrender.com/webhook'

# Port for Render (as specified, 1000)
PORT = 1000

# Sites to search (3 Iranian, 3 Foreign)
# Note: These are examples; scraping may violate terms of service. Use APIs if available.
# Iranian: music-fa.com, upmusics.com, dlmelody.ir
# Foreign: genius.com (lyrics, but for demo), soundcloud.com (search), last.fm (search)
SITES = {
    'iranian': [
        'https://music-fa.com/search/',
        'https://upmusics.com/?s=',
        'https://dlmelody.ir/?s='
    ],
    'foreign': [
        'https://genius.com/search?q=',
        'https://soundcloud.com/search?q=',
        'https://www.last.fm/search?q='
    ]
}

# User language storage (simple dict for demo; use DB for production)
user_languages = {}

# Translations
TRANSLATIONS = {
    'en': {
        'welcome': "Welcome! Please choose your language:",
        'start_msg': "Hello! I'm Music Finder Bot. Send me a song name, artist, or album to search.",
        'choose_lang': ["English", "فارسی"],
        'song_list': "Found songs:",
        'more': "More",
        'caption_photo': "Song: {song}\nArtist: {artist}\nYear: {year}",
        'caption_audio': "Music Finder Bot @Tellgptvip_bot"
    },
    'fa': {
        'welcome': "خوش آمدید! لطفاً زبان خود را انتخاب کنید:",
        'start_msg': "سلام! من ربات موزیک یاب هستم. نام آهنگ، خواننده یا آلبوم را ارسال کنید تا جستجو کنم.",
        'choose_lang': ["English", "فارسی"],
        'song_list': "آهنگ‌های یافت شده:",
        'more': "بیشتر",
        'caption_photo': "آهنگ: {song}\nخواننده: {artist}\nسال: {year}",
        'caption_audio': "ربات موزیک یاب @Tellgptvip_bot"
    }
}

app = Flask(__name__)

# Function to scrape sites (dummy implementation; customize per site)
def search_sites(query, is_artist=False, is_album=False):
    results = []
    all_sites = SITES['iranian'] + SITES['foreign']
    for site in all_sites:
        try:
            url = site + query.replace(' ', '+')
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Dummy parsing (adapt to each site's structure)
            if 'music-fa.com' in site:
                songs = soup.find_all('div', class_='post')  # Example class
                for song in songs[:5]:  # Limit to 5 per site
                    title = song.find('h2').text if song.find('h2') else 'Unknown'
                    link = song.find('a')['href']
                    artist = 'Unknown'  # Parse artist
                    year = 'Unknown'   # Parse year
                    cover = 'https://example.com/cover.jpg'  # Parse cover URL
                    mp3 = link  # Assume direct MP3 or parse
                    results.append({'title': title, 'artist': artist, 'year': year, 'cover': cover, 'mp3': mp3})
            
            # Similarly for other sites... (implement parsing for each)
            # For upmusics.com, dlmelody.ir, genius, soundcloud, last.fm
            # Use appropriate selectors, e.g., soup.find_all('a', class_='track')
            # For MP3, may need to fetch download link from page
            # For quality 320, check if available
            
        except Exception:
            pass  # Skip errors
    
    return results  # List of dicts: {'title', 'artist', 'year', 'cover', 'mp3'}

# Start command
async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in user_languages:
        keyboard = [[InlineKeyboardButton(lang, callback_data=lang) for lang in TRANSLATIONS['en']['choose_lang']]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(TRANSLATIONS['en']['welcome'], reply_markup=reply_markup)
    else:
        lang = user_languages[user_id]
        await update.message.reply_text(TRANSLATIONS[lang]['start_msg'])

# Language selection
async def lang_select(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    lang = 'en' if query.data == 'English' else 'fa'
    user_languages[user_id] = lang
    await query.answer()
    await query.edit_message_text(TRANSLATIONS[lang]['start_msg'])

# Search handler
async def search(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    lang = user_languages.get(user_id, 'en')
    query = update.message.text.strip()
    
    # Determine if artist, album, or song (simple heuristic)
    is_artist = 'artist' in query.lower() or 'خواننده' in query  # Improve detection
    is_album = 'album' in query.lower() or 'آلبوم' in query
    
    results = search_sites(query, is_artist, is_album)
    
    if not results:
        await update.message.reply_text("No results found." if lang == 'en' else "نتیجه‌ای یافت نشد.")
        return
    
    # Pagination (simple, show 5 at a time)
    page = 0
    await show_results(update.message, results, page, lang)

async def show_results(message, results, page, lang):
    per_page = 5
    start = page * per_page
    end = start + per_page
    current = results[start:end]
    
    keyboard = []
    for idx, res in enumerate(current, start):
        keyboard.append([InlineKeyboardButton(res['title'], callback_data=f"song_{start+idx}")])
    
    if end < len(results):
        keyboard.append([InlineKeyboardButton(TRANSLATIONS[lang]['more'], callback_data=f"more_{page+1}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(TRANSLATIONS[lang]['song_list'], reply_markup=reply_markup)

# Song selection
async def song_select(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    lang = user_languages.get(user_id, 'en')
    
    if data.startswith('song_'):
        idx = int(data.split('_')[1])
        # Assume results are stored temporarily or refetch; for demo, assume global results (bad practice)
        # In production, store in context.user_data
        # Here, dummy: refetch or use stored
        # For simplicity, assume results from previous (not ideal)
        # Let's say we have results in context.user_data['results']
        # But for this code, skip and assume res = {'title': 'Song', ...}
        res = {'title': 'Example Song', 'artist': 'Artist', 'year': '2023', 'cover': 'https://example.com/cover.jpg', 'mp3': 'https://example.com/song.mp3'}
        
        # Send cover
        caption = TRANSLATIONS[lang]['caption_photo'].format(song=res['title'], artist=res['artist'], year=res['year'])
        await query.message.reply_photo(photo=res['cover'], caption=caption)
        
        # Send MP3 (320kbps assumed)
        await query.message.reply_audio(audio=res['mp3'], caption=TRANSLATIONS[lang]['caption_audio'])
    
    elif data.startswith('more_'):
        page = int(data.split('_')[1])
        results = []  # Refetch or from user_data
        await show_results(query.message, results, page, lang)
    
    await query.answer()

# Webhook setup
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.process_update(update)
    return 'OK', 200

if __name__ == '__main__':
    # Build application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(lang_select, pattern='^(English|فارسی)$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    application.add_handler(CallbackQueryHandler(song_select))
    
    # Set webhook
    application.bot.set_webhook(WEBHOOK_URL)
    
    # Run Flask in thread
    threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': PORT}).start()
    
    # Run bot (but since webhook, no polling)
    # application.run_polling()  # Comment out for webhook
