import logging
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler, ContextTypes
from pymongo import MongoClient
import time

TOKEN = '8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0'
OWNER_ID = 5637609683
CHANNEL_USERNAME = '@netgoris'
MONGO_URI = 'mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
PORT = 10000
WEBHOOK_URL = 'https://chatgpt-qg71.onrender.com'

logging.basicConfig(level=logging.INFO)

client = MongoClient(MONGO_URI)
db = client['telegram_bot']
users_col = db['users']
spam_col = db['spam']

async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if chat_id != user_id:
        return

    if not is_member(user_id, context):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('📢 عضویت در کانال', url=f'https://t.me/{CHANNEL_USERNAME.lstrip("@")}')],
            [InlineKeyboardButton('✅ تایید عضویت', callback_data='check')]
        ])
        msg = await update.message.reply_text('⚠️ لطفاً ابتدا در کانال عضو شوید سپس دکمه تایید را بزنید.', reply_markup=keyboard)
        db.users_col.update_one({"_id": user_id}, {"$set": {"join_msg_id": msg.message_id}}, upsert=True)
        return

    await send_welcome(update, context)

async def send_welcome(update: Update, context: CallbackContext):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton('📖 راهنما', callback_data='help')]
    ])
    msg = await update.message.reply_text(
        '🎉 خوش آمدید به ربات ما!\nبا استفاده از این ربات می‌توانید از امکانات متنوع بهره‌مند شوید.',
        reply_markup=keyboard
    )
    users_col.update_one({"_id": update.effective_user.id}, {"$set": {"joined": True, "start_msg_id": msg.message_id}}, upsert=True)
    if not users_col.find_one({"_id": update.effective_user.id, "notified": True}):
        await context.bot.send_message(chat_id=OWNER_ID, text=f'کاربر جدید استارت کرد: {update.effective_user.mention_html()}', parse_mode='HTML')
        users_col.update_one({"_id": update.effective_user.id}, {"$set": {"notified": True}}, upsert=True)

async def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'check':
        if is_member(user_id, context):
            data = users_col.find_one({"_id": user_id})
            if data and 'join_msg_id' in data:
                try:
                    await context.bot.delete_message(chat_id=user_id, message_id=data['join_msg_id'])
                except:
                    pass
            await send_welcome(update, context)
        else:
            await query.edit_message_text('⛔️ هنوز عضو کانال نیستید. لطفاً عضو شوید و دوباره تایید بزنید.')
    elif query.data == 'help':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('🔙 بازگشت', callback_data='back')]
        ])
        await query.edit_message_text(
            '📖 راهنمای ربات:\n\n'
            '🔹 ارسال لینک‌های اینستاگرام، اسپاتیفای یا پینترست = دانلود محتوا\n'
            '🔹 ارسال دستور "عکس [متن]" برای ساخت عکس انگلیسی\n'
            '🔹 ارسال متن = دریافت پاسخ هوش مصنوعی\n\n'
            '⚠️ قوانین:\n'
            '⛔️ ارسال اسپم بیش از ۴ پیام پشت سر هم باعث سکوت می‌شود.\n'
            '⛔️ رعایت ادب الزامی است.\n\n'
            '⚡️ نسخه فعلی آزمایشی است، ربات بروزرسانی می‌شود.',
            reply_markup=keyboard
        )
    elif query.data == 'back':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('📖 راهنما', callback_data='help')]
        ])
        await query.edit_message_text(
            '✅ ممنون که ربات ما را انتخاب کردید. امیدواریم لذت ببرید.\nبرای سوالات از دکمه راهنما استفاده کنید.',
            reply_markup=keyboard
        )

def is_member(user_id, context):
    try:
        member = context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "creator", "administrator"]
    except:
        return False

async def message_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if chat_id != user_id:
        return

    if spam_check(user_id):
        await update.message.reply_text('⏳ لطفاً کمی صبر کنید، ارسال بیش از حد مجاز است.')
        return

    if text.lower().startswith('عکس '):
        keyword = text[4:]
        img_res = requests.get(f'https://v3.api-free.ir/image/?text={keyword}').json()
        if img_res.get('ok'):
            await update.message.reply_photo(img_res['result'])
        else:
            await update.message.reply_text('⛔️ خطا در ساخت عکس.')
        return

    if 'instagram.com' in text:
        dl_res = requests.get(f'https://pouriam.top/eyephp/instagram?url={text}').json()
        if 'links' in dl_res:
            for link in dl_res['links']:
                await update.message.reply_media_group([{'type': 'photo' if '.jpg' in link else 'video', 'media': link}])
        else:
            await update.message.reply_text('⛔️ خطا در دریافت از اینستاگرام.')
        return

    if 'spotify.com' in text:
        dl_res = requests.get(f'http://api.cactus-dev.ir/spotify.php?url={text}').json()
        if dl_res.get('ok'):
            await update.message.reply_audio(dl_res['data']['download_url'])
        else:
            await update.message.reply_text('⛔️ خطا در دریافت از اسپاتیفای.')
        return

    if 'pin.it' in text or 'pinterest.com' in text:
        dl_res = requests.get(f'https://haji.s2025h.space/pin/?url={text}&client_key=keyvip').json()
        if dl_res.get('status'):
            await update.message.reply_photo(dl_res['download_url'])
        else:
            await update.message.reply_text('⛔️ خطا در دریافت از پینترست.')
        return

    # AI Chat with fallback
    for url in [
        f'https://starsshoptl.ir/Ai/index.php?text={text}',
        f'https://starsshoptl.ir/Ai/index.php?model=gpt&text={text}',
        f'https://starsshoptl.ir/Ai/index.php?model=deepseek&text={text}'
    ]:
        res = requests.get(url)
        if res.ok and res.text.strip():
            await update.message.reply_text(res.text.strip())
            break
    else:
        await update.message.reply_text('⛔️ خطا در دریافت پاسخ.')

    # پشتیبانی
    if text.lower() == 'پشتیبانی':
        kb = ReplyKeyboardMarkup([[KeyboardButton('لغو')]], resize_keyboard=True)
        await update.message.reply_text('✅ لطفاً پیام خود را ارسال کنید یا لغو را بزنید.', reply_markup=kb)
        return

    if text.lower() == 'لغو':
        kb = ReplyKeyboardMarkup([[KeyboardButton('پشتیبانی')]], resize_keyboard=True)
        await update.message.reply_text('❌ پشتیبانی لغو شد.', reply_markup=kb)
        return

    if users_col.find_one({"_id": user_id, "support": True}):
        await context.bot.send_message(chat_id=OWNER_ID, text=f'📩 پیام جدید از {update.effective_user.mention_html()}:\n\n{text}', parse_mode='HTML')
        users_col.update_one({"_id": user_id}, {"$set": {"support": False}})
        kb = ReplyKeyboardMarkup([[KeyboardButton('پشتیبانی')]], resize_keyboard=True)
        await update.message.reply_text('✅ پیام شما ارسال شد.', reply_markup=kb)

def spam_check(user_id):
    now = int(time.time())
    user = spam_col.find_one({"_id": user_id})
    if user:
        msgs = [t for t in user['times'] if now - t < 120]
        msgs.append(now)
        spam_col.update_one({"_id": user_id}, {"$set": {"times": msgs}})
        return len(msgs) > 4
    spam_col.insert_one({"_id": user_id, "times": [now]})
    return False

async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    await app.bot.set_webhook(f'{WEBHOOK_URL}')
    await app.start()
    await app.updater.start_polling()
    await app.idle()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
