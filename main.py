from flask import Flask, request, jsonify
import requests as req
import random
import json
import time
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

app = Flask(__name__)

# توکن ربات تلگرام
BOT_TOKEN = "8175470749:AAGjaYSVosmfk6AmuqXvcVbSUJAqS200q3c"
# دامنه هاست
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com/webhook"

user_histories = {}

# لیست پراکسی‌های آپدیت‌شده (نمونه - لطفاً جایگزین کنید)
proxies = [
    # Format 1: ip:port:username:password
    "192.168.1.1:8080:user1:pass1",
    "172.16.254.1:3128:user2:pass2",
    "10.0.0.1:8000:user3:pass3",
    "45.76.123.45:8888:user4:pass4",
    "198.50.163.192:9999:user5:pass5",
    # Format 3: ip:port
    "203.0.113.10:8080",
    "198.51.100.20:3128",
]

def get_random_proxy():
    proxy = random.choice(proxies)
    parts = proxy.split(':')
    
    if len(parts) == 2:
        # Format 3: ip:port
        ip, port = parts
        proxy_url = f"http://{ip}:{port}"
    elif len(parts) == 4:
        # Format 1: ip:port:username:password
        ip, port, username, password = parts
        proxy_url = f"http://{username}:{password}@{ip}:{port}"
    else:
        raise ValueError("فرمت پروکسی نامعتبر است")
        
    return {'http': proxy_url, 'https': proxy_url}

def ask_gpt(message, history):
    try:
        api = "https://gpt.lovetoome.com/api/openai/v1/chat/completions"
        
        history.append({"role": "user", "content": message})
        trimmed_history = history[-7:]
        payload = {
            "messages": [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "parts": [
                        {"type": "text", "text": msg["content"]}
                    ]
                }
                for msg in history
            ],
            "stream": True,
            "model": "gpt-4o-mini",
            "temperature": 0.5,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "top_p": 1,
            "key": "123dfnbjds%!@%123DSasda"
        }

        headers = {
            "Accept": "application/json, text/event-stream",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
            "Origin": "https://gpt.lovetoome.com",
            "Referer": "https://gpt.lovetoome.com/",
            "Cookie": '_ga=GA1.1.1956560479.1747133170; FCCDCF=%5Bnull%2Cnull%2Cnull%2C%5B%22CQRWXMAQRWXMAEsACBENBqFoAP_gAEPgAARoINJD7C7FbSFCyD5zaLsAMAhHRsAAQoQAAASBAmABQAKQIAQCgkAYFASgBAACAAAAICRBIQIECAAAAUAAQAAAAAAEAAAAAAAIIAAAgAEAAAAIAAACAIAAEAAIAAAAEAAAmAgAAIIACAAAgAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAAAAAAQNVSD2F2K2kKFkHCmwXYAYBCujYAAhQgAAAkCBMACgAUgQAgFJIAgCIFAAAAAAAAAQEiCQAAQABAAAIACgAAAAAAIAAAAAAAQQAABAAIAAAAAAAAEAQAAIAAQAAAAIAABEhAAAQQAEAAAAAAAQAAA%22%2C%222~70.89.93.108.122.149.184.196.236.259.311.313.314.323.358.415.442.486.494.495.540.574.609.864.981.1029.1048.1051.1095.1097.1126.1205.1276.1301.1365.1415.1449.1514.1570.1577.1598.1651.1716.1735.1753.1765.1870.1878.1889.1958.1960.2072.2253.2299.2373.2415.2506.2526.2531.2568.2571.2575.2624.2677.2778~dv.%22%2C%22D3F47E04-C383-4F59-BA10-E3B5162C6A3C%22%5D%5D; _clck=yk8zp5%7C2%7Cfvw%7C0%7C1959; _ga_TT172QJHGK=GS2.1.s1747393668$o10$g1$t1747393669$j0$l0$h0; _ga_89WN60ZK2E=GS2.1.s1747393668$o10$g1$t1747393669$j0$l0$h0; FCNEC=%5B%5B%22AKsRol-WtXraDX2-rxoAZrfhhu5kdKzR1_9JtfjwL-plCWbVieTeo_zrt_ATw2QrJtDXWl0-s0IXv0jyre3LctpnveeSq4b0DuPzZyql4I3bqoap0DbjoS1cv1btqs0lqEDt8m06BgWt7BvSa-tidQD560mp4LyPMg%3D%3D%22%5D%5D; __gads=ID=4902d0b371c02e51:T=1747133174:RT=1747393672:S=ALNI_MYOOIjJ3qGn564UVeNWS2Bi5C4c6A; __gpi=UID=000010abf2094f44:T=1747133174:RT=1747393672:S=ALNI_MZX2J4CZ8DMWBbP472aH5uFgEo31g; __eoi=ID=92dfc2f19ef6bf55:T=1747133174:RT=1747393672:S=AA-AfjaKj2zZmjFjQyhL5CI2gWCy'
        }

        proxy = get_random_proxy()
        print(f"Using proxy: {proxy['http']}")

        try:
            response = req.post(api, headers=headers, json=payload, stream=True, proxies=proxy, timeout=30)
            answer = ""
            for line in response.iter_lines():
                if line:
                    try:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            data = decoded_line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                obj = json.loads(data)
                                delta = obj.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    answer += content
                            except Exception:
                                pass
                        else:
                            answer += decoded_line
                    except Exception:
                        pass
            trimmed_history.append({"role": "assistant", "content": answer})
            return answer, trimmed_history
        except Exception as e:
            print(f"Error in API request: {str(e)}")
            return "Sorry, there was a problem connecting to the server", history

    except Exception as e:
        print(f"Error in ask_gpt: {str(e)}")
        return "Sorry, there was a problem processing your request", history

def create_glass_image():
    # ایجاد تصویر با پس‌زمینه شیشه‌ای (نیمه‌شفاف)
    img = Image.new('RGBA', (512, 512), (0, 0, 0, 100))  # پس‌زمینه نیمه‌شفاف
    draw = ImageDraw.Draw(img)
    
    # فونت (پیش‌فرض - می‌تونی فونت دلخواه رو جایگزین کنی)
    try:
        font = ImageFont.truetype("arial.ttf", 40)  # فونت و سایز
    except:
        font = ImageFont.load_default()
    
    # اضافه کردن متن @netgoris
    draw.text((100, 200), "@netgoris", fill=(255, 255, 255, 255), font=font)
    
    # اضافه کردن دکمه تأیید (مستطیل سبز)
    draw.rectangle((200, 300, 300, 350), fill=(0, 255, 0, 200), outline=(255, 255, 255, 255))
    draw.text((220, 320), "تأیید", fill=(255, 255, 255, 255), font=font)
    
    # ذخیره تصویر
    img.save("glass_image.png", "PNG")
    return "glass_image.png"

# تولید تصویر شیشه‌ای هنگام شروع برنامه
create_glass_image()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ارسال تصویر شیشه‌ای با دکمه تأیید
    keyboard = [[InlineKeyboardButton("تأیید", callback_data="confirm")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_photo(
        photo=open("glass_image.png", "rb"),
        caption="@netgoris",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    message = update.message.text
    
    # ارسال پیام اولیه
    sent_message = await update.message.reply_text("…")
    
    # گرفتن تاریخچه کاربر
    history = user_histories.get(user_id, [])
    
    # دریافت پاسخ از API
    answer, new_history = ask_gpt(message, history)
    user_histories[user_id] = new_history
    
    # تأخیر ۲ ثانیه‌ای
    time.sleep(2)
    
    # ادیت پیام اولیه با پاسخ نهایی
    await sent_message.edit_text(answer)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm":
        await query.message.reply_text("تأیید شد! حالا می‌تونی پیام بفرستی.")

@app.route('/webhook', methods=['POST'])
async def webhook():
    update = Update.de_json(request.json, bot=app.bot)
    await app.bot_application.process_update(update)
    return jsonify({"status": "ok"}), 200

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_id = data.get('user_id')
        message = data.get('message')
        if not user_id or not message:
            return jsonify({'result': 'user_id and message required'}), 400

        # ارسال پیام اولیه
        initial_response = {'result': '…'}
        time.sleep(2)  # تأخیر ۲ ثانیه‌ای

        history = user_histories.get(user_id, [])
        answer, new_history = ask_gpt(message, history)
        user_histories[user_id] = new_history

        return jsonify({'result': answer}), 200
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({'result': "Sorry, something went wrong"}), 200

@app.route('/')
def index():
    return jsonify({"result": "Flask is working!"}), 200

if __name__ == '__main__':
    # تنظیم ربات تلگرام
    app.bot_application = Application.builder().token(BOT_TOKEN).build()
    
    # اضافه کردن هندلرها
    app.bot_application.add_handler(CommandHandler("start", start))
    app.bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.bot_application.add_handler(CallbackQueryHandler(handle_button))
    
    # تنظیم وب‌هوک
    app.bot_application.run_webhook(
        listen="0.0.0.0",
        port=10000,
        url_path="/webhook",
        webhook_url=WEBHOOK_URL
    )
    
    # اجرای اپلیکیشن Flask
    app.run(host="0.0.0.0", port=5000, debug=True)
