import asyncio
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler

# تنظیمات
API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
BOT_TOKEN = '8175470749:AAGjaYSVosmfk6AmuqXvcVbSUJAqS200q3c'
TAG = '@netgoris'

# متغیرهای جهانی
SOURCE_CHANNEL = None
DESTINATION_CHANNEL = None
client = None

async def init_telethon():
    global client
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start()
    print("Telethon client started.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("تنظیم کانال مبدا")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("سلام! برای تنظیم کانال مبدا، دکمه زیر رو بزنید.", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SOURCE_CHANNEL
    text = update.message.text
    if text == "تنظیم کانال مبدا":
        await update.message.reply_text("لطفاً آیدی کانال مبدا رو بفرستید (مثل @channelusername)")
    elif text.startswith('@'):
        SOURCE_CHANNEL = text
        await update.message.reply_text(f"کانال مبدا تنظیم شد: {SOURCE_CHANNEL}")
        # شروع job برای چک هر 5 دقیقه
        context.job_queue.run_repeating(check_and_post_config, interval=300, first=10, data=update.message.chat_id)

async def track_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global DESTINATION_CHANNEL
    my_chat_member = update.my_chat_member
    if my_chat_member.new_chat_member.user.is_self and my_chat_member.new_chat_member.status in ['member', 'administrator']:
        DESTINATION_CHANNEL = my_chat_member.chat.id
        print(f"کانال مقصد تنظیم شد: {DESTINATION_CHANNEL}")

async def check_and_post_config(context: ContextTypes.DEFAULT_TYPE):
    if SOURCE_CHANNEL is None or DESTINATION_CHANNEL is None or client is None:
        return
    try:
        entity = await client.get_entity(SOURCE_CHANNEL)
        async for message in client.iter_messages(entity, limit=50):  # چک تا 50 پیام آخر
            if message.text and is_v2ray_config(message.text):
                config = extract_config(message.text)
                cleaned_config = clean_and_replace_tags(config)
                final_message = f"{cleaned_config}\n\n{DESTINATION_CHANNEL}\n{TAG}"
                await context.bot.send_message(chat_id=DESTINATION_CHANNEL, text=final_message)
                break  # فقط آخرین کانفیگ معتبر رو پست کن
    except Exception as e:
        print(f"خطا: {e}")

def is_v2ray_config(text: str) -> bool:
    # تشخیص اگر شامل vmess:// یا vless:// یا ss:// باشه
    return bool(re.search(r'(vmess|vless|ss)://', text, re.IGNORECASE))

def extract_config(text: str) -> str:
    # استخراج فقط قسمت‌های کانفیگ (لینک‌ها)
    configs = re.findall(r'(vmess|vless|ss)://[^\s]+', text, re.IGNORECASE)
    return '\n'.join(configs) if configs else ''

def clean_and_replace_tags(config: str) -> str:
    # جایگزینی همه تگ‌های @username با @netgoris
    return re.sub(r'@\w+', TAG, config)

def main():
    # شروع Telethon در background
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_telethon())

    # شروع Bot
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(ChatMemberHandler(track_channels, ChatMemberHandler.MY_CHAT_MEMBER))
    app.run_polling()

if __name__ == '__main__':
    main()
