import os
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import threading
import random
import json

API_TOKEN = '8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0'
CHANNEL_USERNAME = 'netgoris'
WEBHOOK_URL = 'https://chatgpt-qg71.onrender.com/'  # بدون اسلش آخر
PORT = int(os.environ.get('PORT', 5000))

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)
user_histories = {}
bot_data = {}

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
        response = requests.post(api, headers=headers, json=payload, stream=True, proxies=get_random_proxy(), timeout=30)
        answer = ""
        for line in response.iter_lines():
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
        print(f"Error ask_gpt: {e}")
        return "❌ خطا در پاسخ‌گویی", history

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_id = str(data.get("user_id"))
        message = data.get("message")
        history = user_histories.get(user_id, [])
        answer, new_history = ask_gpt(message, history)
        user_histories[user_id] = new_history
        return {"result": answer}, 200
    except Exception as e:
        print(f"Error chat endpoint: {e}")
        return {"result": "خطا"}, 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running."

@app.route(f'/{API_TOKEN}', methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

def is_member(user_id):
    try:
        status = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id).status
        return status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Error checking membership: {e}")
        return False

@bot.message_handler(commands=["start"])
def handle_start(msg):
    if not is_member(msg.from_user.id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📥 ورود به کانال", url=f"https://t.me/{CHANNEL_USERNAME}"))
        markup.add(InlineKeyboardButton("✅ عضویت انجام شد", callback_data="check_join"))
        sent = bot.send_message(msg.chat.id, "📛 لطفاً ابتدا عضو کانال شوید و سپس دکمه تأیید را بزنید:", reply_markup=markup)
        bot_data[msg.from_user.id] = sent.message_id
        return
    send_welcome(msg.chat.id)

def send_welcome(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📘 راهنما", callback_data="show_help"))
    bot.send_message(chat_id, "🌟 خوش آمدید!\nبرای استفاده از ربات، پیام خود را ارسال کنید.\nبرای مشاهده امکانات، روی دکمه راهنما بزنید.", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(c):
    if is_member(c.from_user.id):
        try:
            bot.delete_message(c.message.chat.id, c.message.message_id)
        except:
            pass
        send_welcome(c.message.chat.id)
    else:
        bot.answer_callback_query(c.id, "⛔ هنوز در کانال عضو نشدید.", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "show_help")
def show_help(c):
    text = (
        "📘 *راهنما:*\n"
        "- در کانال @netgoris عضو شوید\n"
        "- پیام خود را ارسال کنید\n"
        "- بات با هوش مصنوعی پاسخ می‌دهد\n\n"
        "👨‍💻 توسعه داده‌شده توسط @NetGoris"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back"))
    bot.edit_message_text(text, c.message.chat.id, c.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "back")
def back_home(c):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📘 راهنما", callback_data="show_help"))
    bot.edit_message_text("🌟 خوش آمدید!\nبرای استفاده از ربات، پیام خود را ارسال کنید.\nبرای مشاهده امکانات، روی دکمه راهنما بزنید.", c.message.chat.id, c.message.message_id, reply_markup=markup)

@bot.message_handler(func=lambda m: True, content_types=["text"])
def ai_chat(msg):
    if not is_member(msg.from_user.id):
        return handle_start(msg)
    payload = {"user_id": str(msg.from_user.id), "message": msg.text}
    try:
        r = requests.post(WEBHOOK_URL + "chat", json=payload)
        answer = r.json().get("result", "❌ خطا")
    except Exception as e:
        print(f"Error sending message to GPT: {e}")
        answer = "❌ مشکل در ارتباط با سرور"
    bot.send_message(msg.chat.id, answer)

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

def setup_webhook():
    print("Deleting previous webhook...")
    bot.remove_webhook()
    print("Setting webhook...")
    bot.set_webhook(url=WEBHOOK_URL + API_TOKEN)

if __name__ == "__main__":
    setup_webhook()
    threading.Thread(target=run_flask).start()
    print("Bot is running...")
