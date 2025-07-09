from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading
import requests
import random
import json

# ========== اطلاعات شما ==========
API_TOKEN = '8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0'
CHANNEL_USERNAME = 'netgoris'
WEBHOOK_URL = 'https://chatgpt-qg71.onrender.com/'  # دامنه شما
PORT = 10000  # پورت مجاز Render رایگان

bot = telebot.TeleBot(API_TOKEN, threaded=True)
app = Flask(__name__)

user_histories = {}

# ========== پروکسی‌ها برای API GPT ==========
proxies = [
    "198.23.239.134:6540:ijkhwzwk:ze5ym8dkas73",
    "207.244.217.165:6712:ijkhwzwk:ze5ym8dkas73",
    "107.172.163.27:6543:ijkhwzwk:ze5ym8dkas73",
    "64.137.42.112:5157:ijkhwzwk:ze5ym8dkas73",
    "173.211.0.148:6641:ijkhwzwk:ze5ym8dkas73",
    "216.10.27.159:6837:ijkhwzwk:ze5ym8dkas73",
]

def get_random_proxy():
    proxy = random.choice(proxies)
    parts = proxy.split(':')
    if len(parts) == 4:
        ip, port, user, pwd = parts
        proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
    else:
        proxy_url = f"http://{parts[0]}:{parts[1]}"
    return {'http': proxy_url, 'https': proxy_url}

# ========== API Flask هوش مصنوعی ==========
def ask_gpt(message, history):
    try:
        api = "https://gpt.lovetoome.com/api/openai/v1/chat/completions"
        history.append({"role": "user", "content": message})
        trimmed_history = history[-7:]
        payload = {
            "messages": [{"role": msg["role"], "content": msg["content"], "parts": [{"type": "text", "text": msg["content"]}]} for msg in trimmed_history],
            "stream": True,
            "model": "gpt-4o-mini",
            "temperature": 0.5,
            "top_p": 1,
            "key": "123dfnbjds%!@%123DSasda"
        }
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json"
        }
        proxy = get_random_proxy()
        response = requests.post(api, headers=headers, json=payload, stream=True, proxies=proxy, timeout=30)
        answer = ""
        for line in response.iter_lines():
            if line:
                try:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: "):
                        data = decoded[6:]
                        if data == "[DONE]":
                            break
                        obj = json.loads(data)
                        delta = obj.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            answer += content
                except:
                    pass
        trimmed_history.append({"role": "assistant", "content": answer})
        return answer, trimmed_history
    except Exception as e:
        return "❌ خطایی در ارتباط با GPT رخ داد", history

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_id = str(data.get('user_id'))
        message = data.get('message')
        history = user_histories.get(user_id, [])
        answer, new_history = ask_gpt(message, history)
        user_histories[user_id] = new_history
        return jsonify({'result': answer}), 200
    except:
        return jsonify({'result': "❌ خطا در پردازش پیام"}), 200

@app.route('/')
def index():
    return 'Bot is running.'

# ========== چک عضویت در کانال ==========
def is_user_member(user_id):
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ['member', 'creator', 'administrator']
    except:
        return False

# ========== هندلر استارت ==========
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    if not is_user_member(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📥 ورود به کانال", url=f"https://t.me/{CHANNEL_USERNAME}"))
        markup.add(InlineKeyboardButton("✅ عضویت انجام شد", callback_data='check_join'))
        bot.send_message(user_id, "📛 لطفاً ابتدا در کانال زیر عضو شوید سپس دکمه تأیید را بزنید:", reply_markup=markup)
        return
    send_welcome(user_id)

# ========== ارسال پیام خوش‌آمد با دکمه راهنما ==========
def send_welcome(user_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📘 راهنما", callback_data="show_help"))
    bot.send_message(user_id,
        "🌟 به ربات خوش آمدید!\n\nبا استفاده از این ربات می‌توانید از هوش مصنوعی برای پاسخ به سوالات خود استفاده کنید. لطفاً از دکمه راهنما برای مشاهده امکانات استفاده کنید.",
        reply_markup=markup)

# ========== چک عضویت دوباره بعد از تایید ==========
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    user_id = call.from_user.id
    if is_user_member(user_id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        send_welcome(user_id)
    else:
        bot.answer_callback_query(call.id, "⛔ هنوز عضو نشدی!", show_alert=True)

# ========== نمایش راهنما ==========
@bot.callback_query_handler(func=lambda call: call.data == "show_help")
def show_help(call):
    help_text = (
        "📘 *راهنمای ربات:*\n\n"
        "✅ ابتدا در کانال @netgoris عضو شوید\n"
        "✉️ سپس پیام خود را ارسال کنید\n"
        "🧠 ربات با هوش مصنوعی به سوالات شما پاسخ می‌دهد\n"
        "💬 از دکمه‌ها برای استفاده راحت‌تر بهره ببرید\n\n"
        "🤖 این ربات توسط تیم @NetGoris توسعه داده شده است."
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🏠 بازگشت", callback_data="back_home"))
    bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

# ========== بازگشت به پیام خوش آمد ==========
@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def back_home(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📘 راهنما", callback_data="show_help"))
    bot.edit_message_text(
        "🌟 به ربات خوش آمدید!\n\nبا استفاده از این ربات می‌توانید از هوش مصنوعی برای پاسخ به سوالات خود استفاده کنید. لطفاً از دکمه راهنما برای مشاهده امکانات استفاده کنید.",
        call.message.chat.id, call.message.message_id, reply_markup=markup
    )

# ========== اجرای همزمان Flask و Bot ==========
def run_flask():
    app.run(host="0.0.0.0", port=PORT)

def run_bot():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    
threading.Thread(target=run_flask).start()
threading.Thread(target=run_bot).start()
