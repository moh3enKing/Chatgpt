import os
import time
import requests
import pymongo
from flask import Flask, request, jsonify

TOKEN = '8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0'
OWNER_ID = 5637609683
CHANNEL_ID = '@netgoris'
DB_PASSWORD = 'RIHPhDJPhd9aNJvC'
API_URL = f'https://api.telegram.org/bot{TOKEN}/'

app = Flask(__name__)
client = pymongo.MongoClient(f"mongodb+srv://mohsenfeizi1386:{DB_PASSWORD}@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["ai_bot"]
users_col = db["users"]
supporting_users = {}

def send_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    return requests.post(API_URL + 'sendMessage', json=payload)

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode='HTML'):
    payload = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': parse_mode}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    return requests.post(API_URL + 'editMessageText', json=payload)

def get_chat_member(user_id):
    res = requests.get(API_URL + f"getChatMember?chat_id={CHANNEL_ID}&user_id={user_id}")
    if res.status_code == 200:
        status = res.json()['result']['status']
        return status in ['member', 'administrator', 'creator']
    return False

def check_spam(user_id):
    now = time.time()
    user = users_col.find_one({'user_id': user_id})
    if user:
        history = [t for t in user.get('messages', []) if now - t < 120]
        history.append(now)
        users_col.update_one({'user_id': user_id}, {'$set': {'messages': history}})
        return len(history) > 4
    else:
        users_col.insert_one({'user_id': user_id, 'messages': [now]})
        return False

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()

    if "message" in update:
        msg = update["message"]
        user_id = msg["from"]["id"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if check_spam(user_id):
            return "OK"

        if not users_col.find_one({'user_id': user_id}):
            users_col.insert_one({'user_id': user_id, 'messages': []})
            send_message(OWNER_ID, f"📥 کاربر جدید:\n<code>{user_id}</code>")

        if text == '/start':
            if not get_chat_member(user_id):
                join_buttons = {
                    "inline_keyboard": [
                        [{"text": "📢 عضویت در کانال", "url": f"https://t.me/{CHANNEL_ID.replace('@','')}"}],
                        [{"text": "✅ عضویت انجام شد", "callback_data": "check_join"}]
                    ]
                }
                send_message(chat_id, "🔒 برای استفاده از ربات ابتدا در کانال عضو شوید.", join_buttons)
            else:
                welcome = "🌟 خوش آمدی!\nاز گزینه‌های زیر استفاده کن."
                reply_markup = {
                    "inline_keyboard": [
                        [{"text": "📘 راهنما", "callback_data": "help"}]
                    ]
                }
                send_message(chat_id, welcome, reply_markup)
            return "OK"

        # پشتیبانی
        if text == "💬 پشتیبانی":
            supporting_users[user_id] = True
            send_message(chat_id, "✍️ لطفاً پیام‌تان را ارسال کنید. برای خروج /cancel را بفرستید.")
            return "OK"

        if text == "/cancel" and supporting_users.get(user_id):
            supporting_users.pop(user_id)
            send_message(chat_id, "✅ از حالت پشتیبانی خارج شدید.", {
                "keyboard": [[{"text": "💬 پشتیبانی"}]],
                "resize_keyboard": True
            })
            return "OK"

        if supporting_users.get(user_id):
            send_message(OWNER_ID, f"📬 پیام از <code>{user_id}</code>:\n{text}")
            return "OK"

    return "OK"

@app.route('/callback', methods=["POST"])
def callback():
    update = request.get_json()
    callback = update['callback_query']
    chat_id = callback['message']['chat']['id']
    user_id = callback['from']['id']
    msg_id = callback['message']['message_id']
    data = callback['data']

    if data == "help":
        help_text = (
            "📘 <b>راهنمای استفاده از ربات:</b>\n"
            "✅ ارسال پیام متنی = چت هوش مصنوعی\n"
            "📷 اینستاگرام، پینترست = دریافت عکس/ویدیو\n"
            "🎧 اسپاتیفای = دریافت MP3 آهنگ\n"
            "🖼 نوشتن کلمه همراه با 'عکس' = ساخت تصویر\n\n"
            "⚠️ از ارسال لینک‌های نامعتبر، فحاشی یا اسپم خودداری کنید.\n"
            "📵 بیش از ۴ پیام متوالی = سکوت ۲ دقیقه‌ای\n\n"
            "❤️ ما همیشه خدمت‌گزار شما هستیم."
        )
        reply_markup = {
            "inline_keyboard": [[{"text": "🔙 برگشت", "callback_data": "back"}]]
        }
        edit_message(chat_id, msg_id, help_text, reply_markup)
    
    elif data == "back":
        text = "🌟 به منوی اصلی برگشتی!\nاز دکمه‌های زیر استفاده کن:"
        reply_markup = {
            "inline_keyboard": [[{"text": "📘 راهنما", "callback_data": "help"}]]
        }
        edit_message(chat_id, msg_id, text, reply_markup)
    
    elif data == "check_join":
        if get_chat_member(user_id):
            reply = "✅ شما در کانال عضو هستید. از ربات استفاده کنید!"
            markup = {
                "inline_keyboard": [[{"text": "📘 راهنما", "callback_data": "help"}]]
            }
            edit_message(chat_id, msg_id, reply, markup)
        else:
            send_message(chat_id, "🚫 هنوز عضو کانال نشدی!")

    return jsonify({"ok": True})

def ask_ai(text):
    urls = [
        f"https://starsshoptl.ir/Ai/index.php?text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=6)
            if res.ok and res.text.strip():
                return res.text.strip()
        except:
            continue
    return "❌ مشکلی در پاسخ هوش مصنوعی پیش آمد."

def handle_links(text):
    if "instagram.com" in text:
        r = requests.get(f"https://pouriam.top/eyephp/instagram?url={text}")
        try:
            return "\n".join(r.json()["links"])
        except:
            return "⚠️ خطا در دریافت از اینستاگرام"
    
    elif "spotify.com" in text:
        r = requests.get(f"http://api.cactus-dev.ir/spotify.php?url={text}")
        try:
            d = r.json()["data"]["track"]
            return f"🎶 {d['name']} - {d['artists']}\n⬇️ {d['download_url']}"
        except:
            return "⚠️ لینک اسپاتیفای معتبر نیست"

    elif "pin.it" in text or "pinterest" in text:
        r = requests.get(f"https://haji.s2025h.space/pin/?url={text}&client_key=keyvip")
        try:
            return r.json()["download_url"]
        except:
            return "⚠️ خطا در دریافت از پینترست"

    elif text.lower().startswith("عکس ") or text.lower().startswith("/img "):
        q = text.replace("عکس ","").replace("/img ","").strip()
        try:
            return requests.get(f"https://v3.api-free.ir/image/?text={q}").json()["result"]
        except:
            return "⚠️ خطا در ساخت عکس"

    elif "http" in text:
        return "🚫 این لینک توسط ربات پشتیبانی نمی‌شود."
    
    return None

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook_final():
    update = request.get_json()
    
    if "message" in update:
        msg = update["message"]
        user_id = msg["from"]["id"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if check_spam(user_id):
            return "OK"

        # پشتیبانی
        if text == "💬 پشتیبانی":
            supporting_users[user_id] = True
            send_message(chat_id, "📝 لطفاً پیام‌تان را ارسال کنید. برای خروج /cancel را بفرستید.")
            return "OK"

        if text == "/cancel" and supporting_users.get(user_id):
            supporting_users.pop(user_id)
            send_message(chat_id, "✅ از پشتیبانی خارج شدید.", {
                "keyboard": [[{"text": "💬 پشتیبانی"}]],
                "resize_keyboard": True
            })
            return "OK"

        if supporting_users.get(user_id):
            forward = f"📨 <b>درخواست پشتیبانی:</b>\n\n👤 <code>{user_id}</code>\n{text}"
            send_message(OWNER_ID, forward)
            return "OK"

        # پردازش لینک یا چت
        response = handle_links(text)
        if response:
            send_message(chat_id, response)
        else:
            ai_reply = ask_ai(text)
            send_message(chat_id, ai_reply, {
                "keyboard": [[{"text": "💬 پشتیبانی"}]],
                "resize_keyboard": True
            })

    elif "callback_query" in update:
        # ری‌دایرکت callback برای راحتی دیباگ
        requests.post("https://your-domain.com/callback", json=update)

    return "OK"

@app.route('/')
def index():
    return '🤖 ربات در حال اجراست.'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
