import os
import time
import json
import threading
import random
import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========= تنظیمات اصلی =========
TOKEN = '8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0'
WEBHOOK_URL = 'https://chatgpt-qg71.onrender.com'
CHANNEL_USERNAME = 'netgoris'
PORT = int(os.environ.get('PORT', 5000))

# ========= ساخت بات و اپلیکیشن =========
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_histories = {}
pending_messages = {}

# ========= لیست پروکسی‌ها =========
proxies = [
    "198.23.239.134:6540:ijkhwzwk:ze5ym8dkas73",
    "207.244.217.165:6712:ijkhwzwk:ze5ym8dkas73",
    "107.172.163.27:6543:ijkhwzwk:ze5ym8dkas73",
]

def get_random_proxy():
    proxy = random.choice(proxies).split(":")
    if len(proxy) == 4:
        ip, port, user, pwd = proxy
        proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
    else:
        proxy_url = f"http://{proxy[0]}:{proxy[1]}"
    return {"http": proxy_url, "https": proxy_url}

# ========= توابع GPT =========
def ask_gpt(message, history):
    try:
        api = "https://gpt.lovetoome.com/api/openai/v1/chat/completions"
        history.append({"role": "user", "content": message})
        payload = {
            "messages": [{"role": m["role"], "content": m["content"], "parts": [{"type": "text", "text": m["content"]}]} for m in history[-7:]],
            "stream": True,
            "model": "gpt-4o-mini",
            "temperature": 0.5,
            "top_p": 1,
            "key": "123dfnbjds%!@%123DSasda"
        }
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        r = requests.post(api, headers=headers, json=payload, stream=True, proxies=get_random_proxy(), timeout=30)
        answer = ""
        for line in r.iter_lines():
            if line:
                try:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data: "):
                        data = decoded[6:]
                        if data == "[DONE]": break
                        obj = json.loads(data)
                        delta = obj.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content: answer += content
                except:
                    pass
        history.append({"role": "assistant", "content": answer})
        return answer, history
    except Exception as e:
        print("GPT ERROR:", e)
        return "❌ خطا در پاسخ‌گویی", history

# ========= چک جوین اجباری =========
def is_member(user_id):
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ========= هندلرهای پیام‌ها =========
@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    if not is_member(uid):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📥 ورود به کانال", url=f"https://t.me/{CHANNEL_USERNAME}"))
        markup.add(InlineKeyboardButton("✅ عضویت انجام شد", callback_data="check_join"))
        sent = bot.send_message(uid, "📛 لطفاً ابتدا در کانال عضو شوید و سپس دکمه تأیید را بزنید:", reply_markup=markup)
        pending_messages[uid] = sent.message_id
        return

    send_welcome(uid)

def send_welcome(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📘 راهنما", callback_data="show_help"))
    bot.send_message(chat_id, "🌟 خوش آمدید!\nپیام خود را ارسال کنید تا پاسخ هوش مصنوعی را دریافت کنید.", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(c):
    uid = c.from_user.id
    if is_member(uid):
        try:
            bot.delete_message(c.message.chat.id, pending_messages.get(uid))
        except:
            pass
        send_welcome(uid)
    else:
        bot.answer_callback_query(c.id, "⛔ هنوز در کانال عضو نشدید.", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "show_help")
def show_help(c):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back"))
    bot.edit_message_text(
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        text=(
            "📘 *راهنمای ربات:*\n\n"
            "1️⃣ ابتدا در کانال @netgoris عضو شوید.\n"
            "2️⃣ پیام خود را ارسال کنید.\n"
            "3️⃣ پاسخ از هوش مصنوعی دریافت خواهید کرد.\n\n"
            "✨ توسعه داده‌شده توسط @NetGoris"
        ),
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda c: c.data == "back")
def go_back(c):
    send_welcome(c.message.chat.id)

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_msg(msg):
    uid = msg.from_user.id
    if not is_member(uid):
        start(msg)
        return
    payload = {"user_id": str(uid), "message": msg.text}
    try:
        r = requests.post(WEBHOOK_URL + "/chat", json=payload)
        res = r.json().get("result", "❌ خطا در پاسخ")
    except Exception as e:
        print("REQUEST ERROR:", e)
        res = "❌ خطا در اتصال به سرور"
    bot.send_message(msg.chat.id, res)

# ========= مسیری برای تست در مرورگر =========
@app.route("/", methods=["GET"])
def index():
    return "Bot is running."

# ========= وب‌هوک مخصوص تلگرام =========
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.data.decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

# ========= وب‌سرویس چت هوش مصنوعی =========
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        uid = str(data.get("user_id"))
        message = data.get("message")
        history = user_histories.get(uid, [])
        answer, history = ask_gpt(message, history)
        user_histories[uid] = history
        return {"result": answer}
    except Exception as e:
        print("CHAT API ERROR:", e)
        return {"result": "❌ خطا در پردازش"}

# ========= تایمر پینگ برای بیدار نگه داشتن هاست =========
def keep_alive():
    while True:
        try:
            requests.get(WEBHOOK_URL)
        except Exception as e:
            print("Keep alive error:", e)
        time.sleep(300)  # هر 5 دقیقه

# ========= اجرای اصلی برنامه =========
def run():
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=WEBHOOK_URL + f'/{TOKEN}')
    threading.Thread(target=keep_alive).start()
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    run()
