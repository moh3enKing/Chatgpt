import os
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from flask import Flask, request
import threading
from pymongo import MongoClient
import yt_dlp  # For foreign sites, use YouTube as fallback for MP3

# Bot token
BOT_TOKEN = '8175470749:AAGjaYSVosmfk6AmuqXvcVbSUJAqS200q3c'

# Webhook URL
WEBHOOK_URL = 'https://srv-d1l6e56mcj7s73brcrv0.onrender.com/webhook'

# Port for Render
PORT = 1000

# MongoDB
MONGO_URL = 'mongodb+srv://username:RIHPhDJPhd9aNJvC@cluster0.mongodb.net/?retryWrites=true&w=majority'
client = MongoClient(MONGO_URL)
db = client['music_bot_db']
users = db['users']

# Sites
SITES = {
    'iranian': [
        'https://radiojavan.com/search?query=',  # Radio Javan
        'https://navahang.com/search/?q=',      # Navahang
        'https://music-fa.com/search/'          # Musicfa
    ],
    'foreign': [
        'https://genius.com/search?q=',         # Genius (lyrics, no MP3)
        'https://soundcloud.com/search?q=',     # SoundCloud (may need API for download)
        'https://www.last.fm/search?q='         # Last.fm (info, no MP3)
    ]
}

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

# Function to search sites
def search_sites(query, is_artist=False, is_album=False):
    results = []
    all_sites = SITES['iranian'] + SITES['foreign']
    for site in all_sites:
        try:
            url = site + query.replace(' ', '+')
            headers = {'User-Agent': 'Mozilla/5.0'}  # To avoid blocks
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parsing per site
            if 'radiojavan.com' in site:
                songs = soup.find_all('li', class_='mp3')
                for song in songs[:5]:
                    title = song.find('div', class_='song_name').text.strip() if song.find('div', class_='song_name') else 'Unknown'
                    artist = song.find('div', class_='artist_name').text.strip() if song.find('div', class_='artist_name') else 'Unknown'
                    year = 'Unknown'  # Radio Javan may not have year
                    cover = song.find('img')['src'] if song.find('img') else 'https://example.com/default.jpg'
                    mp3 = song.find('a', class_='download_song')['href'] if song.find('a', class_='download_song') else ''
                    if mp3:
                        results.append({'title': title, 'artist': artist, 'year': year, 'cover': cover, 'mp3': mp3})

            elif 'navahang.com' in site:
                songs = soup.find_all('div', class_='track-item')
                for song in songs[:5]:
                    title = song.find('h3').text.strip() if song.find('h3') else 'Unknown'
                    artist = song.find('p', class_='artist').text.strip() if song.find('p', class_='artist') else 'Unknown'
                    year = 'Unknown'
                    cover = song.find('img')['src'] if song.find('img') else 'https://example.com/default.jpg'
                    mp3 = song.find('a', class_='download')['href'] if song.find('a', class_='download') else ''
                    if mp3:
                        results.append({'title': title, 'artist': artist, 'year': year, 'cover': cover, 'mp3': mp3})

            elif 'music-fa.com' in site:
                songs = soup.find_all('div', class_='post')
                for song in songs[:5]:
                    title = song.find('h2').text.strip() if song.find('h2') else 'Unknown'
                    artist = song.find('span', class_='artist').text.strip() if song.find('span', class_='artist') else 'Unknown'
                    year = 'Unknown'
                    cover = song.find('img')['src'] if song.find('img') else 'https://example.com/default.jpg'
                    mp3 = song.find('a', class_='download')['href'] if song.find('a', class_='download') else ''
                    if mp3:
                        results.append({'title': title, 'artist': artist, 'year': year, 'cover': cover, 'mp3': mp3})

            elif 'genius.com' in site:
                songs = soup.find_all('div', class_='mini-card')
                for song in songs[:5]:
                    title = song.find('span', class_='song_title').text.strip() if song.find('span', class_='song_title') else 'Unknown'
                    artist = song.find('span', class_='artist_name').text.strip() if song.find('span', class_='artist_name') else 'Unknown'
                    year = song.find('span', class_='year').text.strip() if song.find('span', class_='year') else 'Unknown'
                    cover = song.find('img')['src'] if song.find('img') else 'https://example.com/default.jpg'
                    mp3 = ''  # No MP3 on Genius, perhaps skip or use fallback
                    results.append({'title': title, 'artist': artist, 'year': year, 'cover': cover, 'mp3': mp3})

            elif 'soundcloud.com' in site:
                # SoundCloud is JS-heavy, may not parse well with requests. Use API if possible.
                songs = soup.find_all('li', class_='searchList__item')
                for song in songs[:5]:
                    title = song.find('a', class_='soundTitle__title').text.strip() if song.find('a', class_='soundTitle__title') else 'Unknown'
                    artist = song.find('a', class_='soundTitle__username').text.strip() if song.find('a', class_='soundTitle__username') else 'Unknown'
                    year = 'Unknown'
                    cover = song.find('img')['src'] if song.find('img') else 'https://example.com/default.jpg'
                    mp3 = song.find('a')['href']  # Link to track, download with yt_dlp perhaps
                    if mp3:
                        mp3 = f'https://soundcloud.com{mp3}'
                    results.append({'title': title, 'artist': artist, 'year': year, 'cover': cover, 'mp3': mp3})

            elif 'last.fm' in site:
                songs = soup.find_all('td', class_='chartlist-name')
                for song in songs[:5]:
                    title = song.find('a').text.strip() if song.find('a') else 'Unknown'
                    artist = song.find_next_sibling('td', class_='chartlist-artist').find('a').text.strip() if song.find_next_sibling() else 'Unknown'
                    year = 'Unknown'
                    cover = 'https://example.com/default.jpg'  # Parse if available
                    mp3 = ''  # No MP3
                    results.append({'title': title, 'artist': artist, 'year': year, 'cover': cover, 'mp3': mp3})

        except Exception as e:
            print(f"Error scraping {site}: {e}")
    
    # Fallback for MP3 if not found: Search YouTube
    if not any(res['mp3'] for res in results):
        ydl_opts = {'format': 'bestaudio/best', 'outtmpl': '-', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            results.append({
                'title': info['title'],
                'artist': info['uploader'],
                'year': info.get('upload_date', 'Unknown')[:4],
                'cover': info['thumbnail'],
                'mp3': info['url']
            })
    
    return results

# Start command
async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_doc = users.find_one({'user_id': user_id})
    if not user_doc:
        keyboard = [[InlineKeyboardButton(lang, callback_data=lang) for lang in TRANSLATIONS['en']['choose_lang']]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(TRANSLATIONS['en']['welcome'], reply_markup=reply_markup)
    else:
        lang = user_doc['language']
        await update.message.reply_text(TRANSLATIONS[lang]['start_msg'])

# Language selection
async def lang_select(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    lang = 'en' if query.data == 'English' else 'fa'
    users.update_one({'user_id': user_id}, {'$set': {'language': lang}}, upsert=True)
    await query.answer()
    await query.edit_message_text(TRANSLATIONS[lang]['start_msg'])

# Search handler
async def search(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_doc = users.find_one({'user_id': user_id})
    lang = user_doc['language'] if user_doc else 'en'
    query = update.message.text.strip()
    
    is_artist = 'artist' in query.lower() or 'خواننده' in query
    is_album = 'album' in query.lower() or 'آلبوم' in query
    
    results = search_sites(query, is_artist, is_album)
    context.user_data['results'] = results  # Store results for pagination
    
    if not results:
        msg = "No results found." if lang == 'en' else "نتیجه‌ای یافت نشد."
        await update.message.reply_text(msg)
        return
    
    page = 0
    await show_results(update.message, results, page, lang)

async def show_results(message, results, page, lang):
    per_page = 5
    start = page * per_page
    end = start + per_page
    current = results[start:end]
    
    keyboard = []
    for idx, res in enumerate(current):
        button_text = f"{res['title']} - {res['artist']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"song_{start + idx}")])
    
    if end < len(results):
        keyboard.append([InlineKeyboardButton(TRANSLATIONS[lang]['more'], callback_data=f"more_{page + 1}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(TRANSLATIONS[lang]['song_list'], reply_markup=reply_markup)

# Song selection
async def song_select(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    user_doc = users.find_one({'user_id': user_id})
    lang = user_doc['language'] if user_doc else 'en'
    
    results = context.user_data.get('results', [])
    
    if data.startswith('song_'):
        idx = int(data.split('_')[1])
        if idx < len(results):
            res = results[idx]
            caption_photo = TRANSLATIONS[lang]['caption_photo'].format(song=res['title'], artist=res['artist'], year=res['year'])
            await query.message.reply_photo(photo=res['cover'], caption=caption_photo)
            
            caption_audio = TRANSLATIONS[lang]['caption_audio']
            await query.message.reply_audio(audio=res['mp3'], caption=caption_audio, title=res['title'])
    
    elif data.startswith('more_'):
        page = int(data.split('_')[1])
        await show_results(query.message, results, page, lang)
    
    await query.answer()

# Webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.process_update(update)
    return 'OK', 200

if __name__ == '__main__':
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(lang_select, pattern='^(English|فارسی)$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    application.add_handler(CallbackQueryHandler(song_select))
    
    application.bot.set_webhook(WEBHOOK_URL)
    
    threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': PORT}).start()
