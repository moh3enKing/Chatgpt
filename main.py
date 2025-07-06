import requests
import time
from flask import Flask, request
import pymongo
import datetime
import logging

TOKEN = '8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0'
OWNER_ID = 5637609683
CHANNEL_ID = '@netgoris'
DB_PASSWORD = 'RIHPhDJPhd9aNJvC'
API_URL = f'https://api.telegram.org/bot{TOKEN}/'

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = pymongo.MongoClient(f"mongodb+srv://mohsenfeizi1386:{DB_PASSWORD}@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["ai_bot"]
users_col = db["users"]

def send_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    return requests.post(f'{API_URL}sendMessage', json=data)

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode='HTML'):
    data = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': parse_mode
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    return requests.post(f'{API_URL}editMessageText', json=data)

def get_chat_member(user_id):
    res = requests.get(f'{API_URL}getChatMember?chat_id={CHANNEL_ID}&user_id={user_id}')
    if res.status_code == 200:
        return res.json()['result']['status'] in ['member', 'administrator', 'creator']
    return False

def check_spam(user_id):
    user = users_col.find_one({'user_id': user_id})
    now = time.time()
    if user:
        last_messages = user.get('messages', [])
        last_messages = [msg for msg in last_messages if now - msg < 120]
        last_messages.append(now)
        users_col.update_one({'user_id': user_id}, {'$set': {'messages': last_messages}})
        if len(last_messages) > 4:
            return True
    else:
        users_col.insert_one({'user_id': user_id, 'messages': [now]})
    return False

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        user_id = msg["from"]["id"]
        if check_spam(user_id):
            return "OK"
        
        # ثبت کاربر جدید و پیام به مدیر
        if not users_col.find_one({'user_id': user_id}):
            users_col.insert_one({'user_id': user_id, 'messages': []})
            send_message(OWNER_ID, f'🎉 کاربر جدید استارت کرد:\n\n🧑‍💻 <code>{user_id}</code>\n\n🗣️ {msg["from"].get("first_name", "?" )}')
        
        if text == "/start":
            if not get_chat_member(user_id):
                reply_markup = {
                    "inline_keyboard": [
                        [{"text": "📢 عضویت در کانال", "url": f"https://t.me/{CHANNEL_ID.replace('@','')}"}],
                        [{"text": "✅ عضویت انجام شد", "callback_data": "check_join"}]
                    ]
                }
                send_message(chat_id, "🚫 برای استفاده از ربات ابتدا باید در کانال زیر عضو شوید.", reply_markup)
                return "OK"
            welcome = "🎉 خوش آمدی به ربات هوش مصنوعی!\nبرای استفاده از امکانات، از دکمه پایین استفاده کن."
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "📘 راهنما", "callback_data": "help"}]
                ]
            }
            send_message(chat_id, welcome, reply_markup)
    return "OK"

from flask import jsonify

@app.route('/check_join', methods=['GET'])
def check_join():
    data = request.args
    user_id = int(data.get("user_id"))
    message_id = int(data.get("message_id"))
    if get_chat_member(user_id):
        welcome = "🎉 عضویت شما تأیید شد!\n\nاکنون می‌توانید از ربات استفاده کنید."
        reply_markup = {
            "inline_keyboard": [
                [{"text": "📘 راهنما", "callback_data": "help"}]
            ]
        }
        edit_message(user_id, message_id, welcome, reply_markup)
    else:
        send_message(user_id, "⚠️ لطفاً ابتدا در کانال عضو شوید.")
    return jsonify({"ok": True})

@app.route('/callback', methods=["POST"])
def callback():
    update = request.get_json()
    callback = update['callback_query']
    chat_id = callback['message']['chat']['id']
    user_id = callback['from']['id']
    message_id = callback['message']['message_id']
    data = callback['data']

    if data == 'help':
        help_text = "📘 <b>راهنمای استفاده از ربات:</b>\n\n✅ ارسال پیام متنی برای چت با هوش مصنوعی\n🎵 ارسال لینک اسپاتیفای برای دریافت MP3\n📷 ارسال لینک اینستاگرام یا پینترست برای دریافت عکس/ویدیو\n🖼 ارسال کلمه برای ساخت تصویر\n\n🚫 لطفاً از ارسال اسپم، تبلیغات یا لینک‌های غیرمجاز خودداری کنید.\n\n🛡 ربات دارای محدودیت ضداسپم است: بیش از ۴ پیام متوالی = سکوت ۲ دقیقه‌ای"
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🔙 برگشت", "callback_data": "back"}]
            ]
        }
        edit_message(chat_id, message_id, help_text, reply_markup)
    elif data == 'back':
        welcome = "🙌 برگشتید! از امکانات ربات استفاده کن یا دکمه راهنما رو بزن."
        reply_markup = {
            "inline_keyboard": [
                [{"text": "📘 راهنما", "callback_data": "help"}]
            ]
        }
        edit_message(chat_id, message_id, welcome, reply_markup)
    return jsonify({"ok": True})

def ask_ai(text):
    urls = [
        f'https://starsshoptl.ir/Ai/index.php?text={text}',
        f'https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}',
        f'https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}'
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=5)
            if res.ok:
                reply = res.text.strip()
                if reply:
                    return reply
        except:
            continue
    return "⚠️ مشکلی در پاسخ‌دهی هوش مصنوعی پیش آمد."

def handle_media(text):
    if "instagram.com" in text:
        r = requests.get(f"https://pouriam.top/eyephp/instagram?url={text}")
        try:
            j = r.json()
            return "\n".join(j["links"])
        except:
            return "⚠️ مشکلی در دریافت از اینستاگرام پیش آمد."
    elif "spotify.com" in text:
        r = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={text}")
        try:
            d = r.json()["data"]["track"]
            return f"🎵 {d['name']} - {d['artists']}\n🔗 {d['download_url']}"
        except:
            return "⚠️ لینک اسپاتیفای معتبر نیست."
    elif "pin.it" in text or "pinterest" in text:
        r = requests.get(f"https://haji.s2025h.space/pin/?url={text}&client_key=keyvip")
        try:
            j = r.json()
            return j["download_url"]
        except:
            return "⚠️ مشکلی در دریافت از پینترست پیش آمد."
    elif text.startswith("عکس ") or text.startswith("تصویر ") or text.startswith("!img ") or text.startswith("/img "):
        word = text.replace("عکس ","").replace("تصویر ","").replace("!img ","").replace("/img ","")
        try:
            res = requests.get(f"https://v3.api-free.ir/image/?text={word}").json()
            return res["result"]
        except:
            return "⚠️ در ساخت تصویر مشکلی رخ داد."
    elif "http" in text:
        return "⚠️ این لینک پشتیبانی نمی‌شود!"
    else:
        return None

supporting_users = {}

def send_support_message(chat_id, user_id, message):
    send_message(user_id, f"📩 پیام از پشتیبانی:\n\n{message}")
    send_message(chat_id, "✅ پیام به کاربر ارسال شد.")

@app.route('/support', methods=['GET'])
def support():
    data = request.args
    admin_id = int(data.get("admin_id"))
    user_id = int(data.get("user_id"))
    message = data.get("message")

    if admin_id == OWNER_ID:
        send_support_message(admin_id, user_id, message)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Unauthorized"})

def keyboard_private(user_id):
    if user_id == OWNER_ID:
        return
    return {
        "keyboard": [
            [{"text": "💬 پشتیبانی"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook_final():
    update = request.get_json()

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")

        if check_spam(user_id):
            return "OK"

        # پشتیبانی
        if text == "💬 پشتیبانی":
            supporting_users[user_id] = True
            send_message(chat_id, "✉️ لطفاً پیام خود را ارسال کنید. برای خروج از حالت پشتیبانی /cancel را بفرستید.")
            return "OK"
        
        if text == "/cancel" and supporting_users.get(user_id):
            supporting_users.pop(user_id)
            send_message(chat_id, "❎ از پشتیبانی خارج شدید.", keyboard_private(user_id))
            return "OK"

        if supporting_users.get(user_id):
            forward_msg = f"📨 <b>درخواست پشتیبانی:</b>\n\n🧑‍💻 <code>{user_id}</code>\n\n💬 {text}"
            send_message(OWNER_ID, forward_msg)
            return "OK"

        # چت با هوش مصنوعی یا بررسی لینک
        result = handle_media(text)
        if result:
            send_message(chat_id, result)
        else:
            reply = ask_ai(text)
            send_message(chat_id, reply, keyboard_private(user_id))

    elif "callback_query" in update:
        # ری‌دایرکت به route callback
        requests.post("https://your-domain.com/callback", json=update)

    return "OK"

@app.route('/')
def index():
    return "Bot is running."

if __name__ == '__main__':
    app.run()
