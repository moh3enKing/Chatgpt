from telegram.ext import ApplicationBuilder, CommandHandler
from flask import Flask, request
import threading
import requests
import os

# مشخصات
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
DOMAIN = "https://chatgpt-qg71.onrender.com"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{DOMAIN}{WEBHOOK_PATH}"
PORT = 10000

# ساخت اپلیکیشن تلگرام
application = ApplicationBuilder().token(BOT_TOKEN).build()

# تعریف دستور استارت
async def start(update, context):
    await update.message.reply_text("✅ ربات فعال است و به درستی کار می‌کند.")

application.add_handler(CommandHandler("start", start))

# ساخت سرور Flask
app = Flask(__name__)

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    application.update_queue.put_nowait(update)
    return "ok", 200

# تابع اجرا سرور
def run_flask():
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    # ست کردن وبهوک
    print("✅ تنظیم وبهوک...")
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}")

    # اجرا سرور و ربات
    threading.Thread(target=run_flask).start()
    application.run_polling()
