from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import os

TOKEN = os.getenv("TOKEN", "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0")

async def start(update: Update, context):
    await update.message.reply_text("✅ ربات با موفقیت فعال شد!")

async def echo(update: Update, context):
    await update.message.reply_text(f"شما نوشتید: {update.message.text}")

def main():
    # ساخت اپلیکیشن
    app = Application.builder().token(TOKEN).build()
    
    # اضافه کردن handlerها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # تنظیمات وب‌هوک
    PORT = 1000  # استفاده از پورت 1000
    WEBHOOK_URL = "https://your-render-app.onrender.com"  # آدرس خود را جایگزین کنید
    
    # اجرای ربات
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
