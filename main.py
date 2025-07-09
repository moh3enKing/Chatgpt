from flask import Flask, request, jsonify, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests as req
import random
import json
import os

app = Flask(__name__)

# تنظیمات ربات
TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
CHANNEL_ID = "@netgoris"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com/webhook"

# ذخیره تاریخچه چت کاربران
user_histories = {}

# لیست پروکسی‌ها
proxies = [
    "198.23.239.134:6540:ijkhwzwk:ze5ym8dkas73",
    "207.244.217.165:6712:ijkhwzwk:ze5ym8dkas73",
    "107.172.163.27:6543:ijkhwzwk:ze5ym8dkas73",
    "64.137.42.112:5157:ijkhwzwk:ze5ym8dkas73",
    "173.211.0.148:6641:ijkhwzwk:ze5ym8dkas73",
    "216.10.27.159:6837:ijkhwzwk:ze5ym8dkas73",
    "154.36.110.199:6853:ijkhwzwk:ze5ym8dkas73",
    "45.151.162.198:6600:ijkhwzwk:ze5ym8dkas73",
    "188.74.210.21:6100:ijkhwzwk:ze5ym8dkas73",
]

# صفحه وب شیشه‌ای
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ورود به ربات</title>
    <style>
        body { 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            height: 100vh; 
            margin: 0; 
            background: linear-gradient(135deg, #667eea, #764ba2); 
            font-family: Arial, sans-serif;
        }
        .glass-container { 
            background: rgba(255, 255, 255, 0.1); 
            backdrop-filter: blur(10px); 
            border-radius: 15px; 
            padding: 40px; 
            text-align: center; 
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37); 
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        h1 { 
            color: white; 
            font-size: 2.5em; 
            margin-bottom: 20px; 
        }
        a { 
            display: inline-block; 
            padding: 15px 30px; 
            background-color: #1e90ff; 
            color: white; 
            text-decoration: none; 
            border-radius: 10px; 
            font-size: 1.2em; 
            transition: background-color 0.3s; 
        }
        a:hover { 
            background-color: #4682b4; 
        }
    </style>
</head>
<body>
    <div class="glass-container">
        <h1>ورود</h1>
        <a href="https://t.me/{}?start=verify">تأیید</a>
    </div>
</body>
</html>
""".format(CHANNEL_ID[1:])

# انتخاب پروکسی تصادفی
def get_random_proxy():
    proxy = random.choice(proxies)
    parts = proxy.split(':')
    
    if len(parts) == 2:
        ip, port = parts
        proxy_url = f"http://{ip}:{port}"
    elif len(parts) == 4:
        ip, port, username, password = parts
        proxy_url = f"http://{username}:{password}@{ip}:{port}"
    else:
        raise ValueError("فرمت پروکسی نامعتبر است")
        
    return {'http': proxy_url, 'https': proxy_url}

# تابع ارتباط با GPT
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
            "Origin": "https://gpt.lovetoome.lovetoome.com",
            "Referer": "https://gpt.lovetoome.com/",
            "Cookie": '_ga=GA1.1.1956560479.1747133170; FCCDCF=%5Bnull%2Cnull%2Cnull%2C%5B%22CQRWXMAQRWXMAEsACBENBqFoAP_gAEPgAARoINJD7C7FbSFCyD5zaLsAMAhHRsAAQoQAAASBAmABQAKQIAQCgkAYFASgBAACAAAAICRBIQIECAAAAUAAQAAAAAAEAAAAAAAIIAAAgAEAAAAIAAACAIAAEAAIAAAAEAAAmAgAAIIACAAAgAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAAAAAAQNVSD2F2K2kKFkHCmwXYAYBCujYAAhQgAAAkCBMACgAUgQAgFJIAgCIFAAAAAAAAAQEiCQAAQABAAAIACgAAAAAAIAAAAAAAQQAABAAIAAAAAAAAEAQAAIAAQAAAAIAABEhAAAQQAEAAAAAAAQAAA%22%2C%222~70.89.93.108.122.149.184.196.236.259.311.313.314.323.358.415.442.486.494.495.540.574.609.864.981.1029.1048.1051.1095.1097.1126.1205.1276.1301.1365.1415.1449.1514.1570.1577.1598.1651.1716.1735.1753.1765.1870.1878.1889.1958.1960.2072.2253.2299.2373.2415.2506.2526.2531.2568.2571.2575.2624.2677.2778~dv.%22%2C%22D3F47E04-C383-4F59-BA10-E3B5162C6A3C%22%5D%5D; _clck=yk8zp5%7C2%7Cfvw%7C0%7C1959; _ga_TT172QJHGK=GS2.1.s1747393668$o10$g1$t1747393669$j0$l0$h0; _ga_89WN60ZK2E=GS2.1.s1747393668$o10$g1$t1747393669$j0$l0$h0; FCNEC=%5B%5B%22AKsRol-WtXraDX2-rxoAZrfhhu5kdKzR1_9JtfjwL-plCWbVieTeo_zrt_ATw2QrJtDXWl0-s0IXv0jyre3LctpnveeSq4b0DuPzZyql4I3bqoap0DbjoS1cv1btqs0lqEDt8m06BgWt7BvSa-tidQD560mp4LyPMg%3D%3D%22%5D%5D; __gads=ID=4902d0b371c02e51:T=1747133174:RT=1747393672:S=ALNI_MYOOIjJ3qGn564UVeNWS2Bi5C4c6A; __gpi=UID=000010abf2094f44:T=1747133174:RT=1747393672:S=ALNI_MZX2J4CZ8DMWBbP472aH5uFgEo31g; __eoi=ID=92dfc2f19ef6bf55:T=1747133174:RT=1747393672:S=AA-AfjaKj2zZmjFjQyhL5CI2gWCy'
        }

        proxy = get_random_proxy()
        print(f"Using proxy: {proxy['http']}")

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
        print(f"Error in ask_gpt: {str(e)}")
        return "متأسفیم، مشکلی در پردازش درخواست شما رخ داد.", history

# بررسی عضویت در کانال
async def check_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# متن خوش‌آمدگویی مودبانه
WELCOME_MESSAGE = (
    "🌟 کاربر گرامی، به ربات هوشمند ما خوش آمدید! 🌟\n\n"
    "از اینکه به جمع ما پیوستید، بسیار خرسندیم. این ربات با بهره‌گیری از هوش مصنوعی پیشرفته، آماده‌ی پاسخگویی به سؤالات شما و ارائه خدمات متنوع است. "
    "برای آشنایی بیشتر با امکانات ربات، لطفاً از دکمه‌ی «راهنما» استفاده کنید. ما در کنار شما هستیم تا تجربه‌ای بی‌نظیر داشته باشید!"
)

# متن راهنمای مفصل و مودبانه
HELP_MESSAGE = (
    "📚 **راهنمای استفاده از ربات هوشمند** 📚\n\n"
    "کاربر عزیز، از شما برای انتخاب ربات ما سپاسگزاریم! این ربات با هدف ارائه خدمات هوشمند و پاسخگویی به نیازهای شما طراحی شده است. در ادامه، راهنمای جامعی برای استفاده از امکانات ربات ارائه شده است:\n\n"
    "🔹 **دستورات اصلی**:\n"
    "  - /start: شروع کار با ربات و بررسی عضویت در کانال\n"
    "  - /help: نمایش این راهنما\n"
    "  - ارسال پیام متنی: برای پرسیدن سؤال یا دریافت پاسخ از هوش مصنوعی\n\n"
    "🔹 **قابلیت‌ها**:\n"
    "  - پاسخگویی هوشمند به سؤالات شما با استفاده از فناوری GPT\n"
    "  - امکان گفت‌وگو با تاریخچه‌ی محدود برای حفظ حریم خصوصی\n"
    "  - عضویت در کانال {} برای دسترسی کامل به خدمات\n\n"
    "🔹 **نکات مهم**:\n"
    "  - لطفاً برای استفاده از ربات، در کانال {} عضو باشید.\n"
    "  - در صورت بروز هرگونه سؤال یا مشکل، می‌توانید با پشتیبانی ما در کانال {} تماس بگیرید.\n"
    "  - ما متعهد به ارائه بهترین خدمات به شما هستیم!\n\n"
    "🙏 اگر سؤالی دارید یا نیاز به راهنمایی بیشتری دارید، خوشحال می‌شویم که به شما کمک کنیم!"
).format(CHANNEL_ID, CHANNEL_ID, CHANNEL_ID)

# دستور شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await check_membership(context, user_id):
        # ارسال پیام خوش‌آمدگویی با دکمه راهنما
        keyboard = [[InlineKeyboardButton("راهنما", callback_data="help")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(WELCOME_MESSAGE, reply_markup=reply_markup)
    else:
        # ارسال پیام جین اجباری
        keyboard = [[InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_ID[1:]}")],
                    [InlineKeyboardButton("تأیید عضویت", callback_data="verify")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"لطفاً ابتدا در کانال {CHANNEL_ID} عضو شوید و سپس دکمه‌ی تأیید را بزنید.",
            reply_markup=reply_markup
        )

# مدیریت پیام‌های متنی (برای چت با GPT)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_membership(context, user_id):
        await update.message.reply_text(f"لطفاً ابتدا در کانal {CHANNEL_ID} عضو شوید و سپس /start را بزنید.")
        return

    message = update.message.text
    history = user_histories.get(user_id, [])
    answer, new_history = ask_gpt(message, history)
    user_histories[user_id] = new_history
    await update.message.reply_text(answer)

# مدیریت دکمه‌ها
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    message = query.message

    if query.data == "verify":
        if await check_membership(context, user_id):
            # حذف پیام جین اجباری
            await message.delete()
            # ارسال پیام خوش‌آمدگویی
            keyboard = [[InlineKeyboardButton("راهنما", callback_data="help")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=user_id, text=WELCOME_MESSAGE, reply_markup=reply_markup)
        else:
            await query.message.edit_text(f"شما هنوز در {CHANNEL_ID} عضو نشده‌اید. لطفاً عضو شوید.")
    
    elif query.data == "help":
        # ویرایش پیام خوش‌آمدگویی به راهنما
        await query.message.edit_text(HELP_MESSAGE)

# روت وب برای صفحه شیشه‌ای
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

# روت وب‌هوک
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    app.dispatcher.process_update(update)
    return "OK", 200

# روت چت (برای API اصلی سورس)
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_id = data.get('user_id')
        message = data.get('message')
        if not user_id or not message:
            return jsonify({'error': 'user_id and message required'}), 400

        history = user_histories.get(user_id, [])
        answer, new_history = ask_gpt(message, history)
        user_histories[user_id] = new_history
        return jsonify({'result': answer}), 200
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({'result': "متأسفیم، مشکلی رخ داد."}), 200

# تنظیم ربات و وب‌هوک
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تنظیم وب‌هوک
    application.bot.set_webhook(url=WEBHOOK_URL)
    
    # اجرای Flask
    port = int(os.environ.get("PORT", 443))  # پورت پیش‌فرض رندر
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
