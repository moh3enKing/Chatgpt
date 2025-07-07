from flask import Flask, request, Response
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Dispatcher, MessageHandler, Filters, CommandHandler, CallbackQueryHandler
import logging
import requests
import re
import time
from pymongo import MongoClient
from io import BytesIO

# تنظیمات ربات و مدیر
BOT_TOKEN = '8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0'
ADMIN_ID = 5637609683
REQUIRED_CHANNEL = '@netgoris'
WEBHOOK_URL = 'https://chatgpt-qg71.onrender.com/' + BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, use_context=True)

logging.basicConfig(level=logging.INFO)

# اتصال به دیتابیس MongoDB
client = MongoClient("mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['telegram_bot']
users_col = db['users']

# تنظیم Webhook
bot.set_webhook(WEBHOOK_URL)

# ساختارهای in-memory برای شمارش پیام‌ها و وضعیت پشتیبانی
user_message_count = {}
user_blocked_until = {}
support_state = {}
pending_broadcast = None

def is_user_banned(user_id):
    user = users_col.find_one({'user_id': user_id})
    return user and user.get('banned', False)

def set_user_joined(user_id):
    users_col.update_one({'user_id': user_id}, {'$set': {'joined': True}}, upsert=True)

def add_user_if_not_exists(user_id):
    if not users_col.find_one({'user_id': user_id}):
        users_col.insert_one({'user_id': user_id, 'banned': False, 'joined': False})

def set_user_banned(user_id, banned=True):
    users_col.update_one({'user_id': user_id}, {'$set': {'banned': banned}}, upsert=True)

def start(update, context):
    user_id = update.message.from_user.id
    add_user_if_not_exists(user_id)
    bot.send_message(ADMIN_ID, f"کاربر {user_id} ربات را استارت کرد.")
    if is_user_banned(user_id):
        context.bot.send_message(user_id, "شما مسدود هستید و نمی‌توانید از ربات استفاده کنید.")
        return
    join_btn = InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{REQUIRED_CHANNEL.strip('@')}")
    confirm_btn = InlineKeyboardButton("تایید عضویت", callback_data="confirm_join")
    markup = InlineKeyboardMarkup([[join_btn, confirm_btn]])
    context.bot.send_message(user_id, "برای استفاده از ربات لطفاً ابتدا در کانال ما عضو شوید:", reply_markup=markup)

def confirm_join_callback(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    query.answer()
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
    except Exception as e:
        logging.error(f"Error checking membership: {e}")
        query.edit_message_text("خطا در بررسی عضویت. لطفا دوباره تلاش کنید.")
        return
    if member.status in ['member', 'creator', 'administrator']:
        set_user_joined(user_id)
        bot.delete_message(chat_id=user_id, message_id=query.message.message_id)
        guide_btn = InlineKeyboardButton("📖 راهنما", callback_data="show_guide")
        guide_markup = InlineKeyboardMarkup([[guide_btn]])
        support_keyboard = ReplyKeyboardMarkup([["پشتیبانی"]], resize_keyboard=True)
        welcome_text = "👋 به ربات خوش آمدید!\nلطفاً روی دکمه زیر کلیک کنید یا از ربات استفاده کنید."
        context.bot.send_message(user_id, welcome_text, reply_markup=guide_markup)
        context.bot.send_message(user_id, "برای ارتباط با پشتیبانی روی دکمه زیر کلیک کنید:", reply_markup=support_keyboard)
    else:
        query.answer("لطفاً ابتدا عضو کانال شوید و سپس دوباره تایید را بزنید.", show_alert=True)

def show_guide_callback(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    query.answer()
    guide_text = (
        "📜 راهنمای ربات:\n"
        "- لطفاً قوانین کانال را رعایت کنید و از ارسال مطالب نامناسب خودداری کنید.\n"
        "- هشدار: ارسال اسپم یا سوءاستفاده منجر به مسدود شدن می‌شود.\n"
        "- **چت هوش مصنوعی**: هر متنی ارسال کنید تا پاسخ دریافت کنید.\n"
        "- **دانلودر لینک‌ها**: لینک‌های اینستاگرام، اسپاتیفای یا پینترست را ارسال کنید تا دانلود شود.\n"
        "- **ساخت عکس**: بنویسید `عکس <متن انگلیسی>` تا تصویر تولید شود.\n"
    )
    back_btn = InlineKeyboardButton("⬅️ بازگشت", callback_data="go_back")
    context.bot.edit_message_text(chat_id=user_id, message_id=query.message.message_id,
                                  text=guide_text, reply_markup=InlineKeyboardMarkup([[back_btn]]))

def go_back_callback(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    query.answer()
    thanks_text = "🎉 متشکریم که ربات ما را انتخاب کردید!"
    context.bot.edit_message_text(chat_id=user_id, message_id=query.message.message_id,
                                  text=thanks_text)

def handle_support_request(update, context):
    user_id = update.message.from_user.id
    if is_user_banned(user_id):
        return
    context.bot.send_message(user_id, "لطفاً پیام خود را ارسال کنید (یک پیام).", reply_markup=ReplyKeyboardRemove())
    support_state[user_id] = True

def forward_support_message(update, context):
    user_id = update.message.from_user.id
    try:
        context.bot.forward_message(ADMIN_ID, chat_id=user_id, message_id=update.message.message_id)
        context.bot.send_message(user_id, "✅ پیام شما ارسال شد، منتظر پاسخ باشید.")
    except Exception as e:
        logging.error(f"Error forwarding support message: {e}")
        context.bot.send_message(user_id, "❌ خطا در ارسال پیام.")
    support_state.pop(user_id, None)

def handle_admin_reply(update, context):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID or not update.message.reply_to_message:
        return
    replied = update.message.reply_to_message
    if replied.forward_from:
        target_id = replied.forward_from.id
        text = update.message.text
        context.bot.send_message(target_id, f"📣 پاسخ پشتیبانی:\n{text}")

def ai_chat(update, context):
    user_id = update.message.from_user.id
    text = update.message.text
    if is_user_banned(user_id) or text == "پشتیبانی":
        return
    user_doc = users_col.find_one({'user_id': user_id})
    if not user_doc or not user_doc.get('joined', False):
        join_btn = InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{REQUIRED_CHANNEL.strip('@')}")
        confirm_btn = InlineKeyboardButton("تایید عضویت", callback_data="confirm_join")
        markup = InlineKeyboardMarkup([[join_btn, confirm_btn]])
        context.bot.send_message(user_id, "⚠️ لطفاً ابتدا در کانال ما عضو شوید:", reply_markup=markup)
        return
    now = time.time()
    if user_id in user_blocked_until and now < user_blocked_until[user_id]:
        return
    user_message_count[user_id] = user_message_count.get(user_id, 0) + 1
    if user_message_count[user_id] >= 4:
        user_blocked_until[user_id] = now + 120
        user_message_count[user_id] = 0
        context.bot.send_message(user_id, "⚠️ شما به دلیل ارسال سریع پیام‌ها برای ۲ دقیقه مسدود شدید.")
        return
    if support_state.get(user_id):
        forward_support_message(update, context)
        return
    if text.startswith("عکس "):
        prompt = text.split(" ", 1)[1]
        if re.search(r'[\u0600-\u06FF]', prompt):
            context.bot.send_message(user_id, "⚠️ لطفاً برای ساخت عکس متن را به انگلیسی وارد کنید.")
        else:
            image_resp = requests.get("https://v3.api-free.ir/image/?text=" + requests.utils.quote(prompt))
            if image_resp.status_code == 200:
                image_bytes = BytesIO(image_resp.content)
                context.bot.send_photo(user_id, image_bytes)
            else:
                context.bot.send_message(user_id, "❌ خطا در دریافت تصویر.")
        return
    if "instagram.com" in text or "instagr.am" in text:
        api_url = f"https://pouriam.top/eyephp/instagram?url={requests.utils.quote(text)}"
        prefix = "اینستاگرام"
    elif "spotify.com" in text:
        api_url = f"http://api.cactus-dev.ir/spotify.php?url={requests.utils.quote(text)}"
        prefix = "اسپاتیفای"
    elif "pinterest.com" in text:
        api_url = f"https://haji.s2025h.space/pin/?url={requests.utils.quote(text)}&client_key=keyvip"
        prefix = "پینترست"
    else:
        api_url = None
    if api_url:
        try:
            resp = requests.get(api_url)
            data = resp.json()
        except Exception as e:
            logging.error(f"Error calling {prefix} API: {e}")
            context.bot.send_message(user_id, f"❌ خطا در دریافت اطلاعات از {prefix}.")
            return
        media_url = data.get('url') or data.get('file') or data.get('video') or data.get('image')
        if not media_url:
            context.bot.send_message(user_id, "❌ محتوا یافت نشد یا لینک نامعتبر است.")
            return
        try:
            media_resp = requests.get(media_url)
        except Exception as e:
            logging.error(f"Error downloading media: {e}")
            context.bot.send_message(user_id, "❌ خطا در دانلود محتوا.")
            return
        content_type = media_resp.headers.get('Content-Type', '')
        if 'video' in content_type:
            context.bot.send_video(user_id, media_resp.content)
        elif 'image' in content_type:
            context.bot.send_photo(user_id, media_resp.content)
        elif 'audio' in content_type or 'mpeg' in content_type:
            context.bot.send_audio(user_id, media_resp.content)
        else:
            context.bot.send_message(user_id, "❌ نوع فایل پشتیبانی نمی‌شود.")
        return
    endpoints = [
        f"https://starsshoptl.ir/Ai/index.php?text={requests.utils.quote(text)}",
        f"https://starsshoptl.ir/Ai/index.php?model=gpt&text={requests.utils.quote(text)}",
        f"https://starsshoptl.ir/Ai/index.php?model=deepseek&text={requests.utils.quote(text)}"
    ]
    response_text = None
    for url in endpoints:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200 and res.text:
                response_text = res.text
                break
        except:
            continue
    if response_text:
        context.bot.send_message(user_id, response_text)
    else:
        context.bot.send_message(user_id, "❌ متاسفانه در حال حاضر قادر به پاسخگویی نیستم.")
    user_message_count[user_id] = 0

def ban_command(update, context):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID: return
    args = context.args
    if not args:
        context.bot.send_message(user_id, "لطفاً آیدی کاربر را بعد از /ban وارد کنید.")
        return
    try:
        target = int(args[0])
    except:
        context.bot.send_message(user_id, "آیدی نامعتبر است.")
        return
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("بله", callback_data=f"ban_{target}"), InlineKeyboardButton("خیر", callback_data="cancel_ban")]
    ])
    context.bot.send_message(user_id, f"آیا از بن کردن کاربر {target} مطمئن هستید؟", reply_markup=keyboard)

def ban_confirm_callback(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != ADMIN_ID: return
    data = query.data
    if data.startswith("ban_"):
        target = int(data.split("_")[1])
        set_user_banned(target, True)
        context.bot.send_message(target, "⚠️ شما توسط ادمین مسدود شدید.")
        query.edit_message_text(f"کاربر {target} بن شد.")
    elif data == "cancel_ban":
        query.edit_message_text("❌ عملیات لغو شد.")

def unban_command(update, context):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID: return
    args = context.args
    if not args:
        context.bot.send_message(user_id, "لطفاً آیدی کاربر را بعد از /unban وارد کنید.")
        return
    try:
        target = int(args[0])
    except:
        context.bot.send_message(user_id, "آیدی نامعتبر است.")
        return
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("بله", callback_data=f"unban_{target}"), InlineKeyboardButton("خیر", callback_data="cancel_unban")]
    ])
    context.bot.send_message(user_id, f"آیا از آزاد کردن کاربر {target} مطمئن هستید؟", reply_markup=keyboard)

def unban_confirm_callback(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != ADMIN_ID: return
    data = query.data
    if data.startswith("unban_"):
        target = int(data.split("_")[1])
        set_user_banned(target, False)
        query.edit_message_text(f"کاربر {target} آزاد شد.")
        context.bot.send_message(target, "✅ حساب شما آزاد شد.")
    elif data == "cancel_unban":
        query.edit_message_text("❌ عملیات لغو شد.")

def broadcast_command(update, context):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID: return
    global pending_broadcast
    message_text = ' '.join(context.args)
    if not message_text:
        context.bot.send_message(user_id, "لطفاً متن پیام را بعد از /broadcast وارد کنید.")
        return
    pending_broadcast = message_text
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("ارسال", callback_data="send_broadcast"), InlineKeyboardButton("لغو", callback_data="cancel_bc")]
    ])
    context.bot.send_message(user_id, "آیا مایل به ارسال پیام به تمام کاربران هستید؟", reply_markup=keyboard)

def send_broadcast_callback(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != ADMIN_ID: return
    global pending_broadcast
    if pending_broadcast:
        all_users = users_col.find({'banned': False})
        for usr in all_users:
            try:
                context.bot.send_message(usr['user_id'], pending_broadcast)
            except Exception as e:
                logging.warning(f"Broadcast to {usr['user_id']} failed: {e}")
        query.edit_message_text("✅ پیام به همه کاربران ارسال شد.")
    pending_broadcast = None

def cancel_callback(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text("❌ عملیات لغو شد.")

def list_command(update, context):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID: return
    banned_users = [u['user_id'] for u in users_col.find({'banned': True})]
    active_users = [u['user_id'] for u in users_col.find({'banned': False})]
    text = f"🔹 تعداد کل کاربران: {users_col.count_documents({})}\n"
    text += f"🔸 کاربران فعال: {len(active_users)}\n"
    text += f"🔸 کاربران مسدود: {len(banned_users)}\n"
    text += f"🛑 لیست کاربران مسدود:\n{', '.join(map(str, banned_users))}\n"
    context.bot.send_message(user_id, text)

dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('ban', ban_command))
dispatcher.add_handler(CommandHandler('unban', unban_command))
dispatcher.add_handler(CommandHandler('broadcast', broadcast_command))
dispatcher.add_handler(CommandHandler('list', list_command))

dispatcher.add_handler(CallbackQueryHandler(confirm_join_callback, pattern='^confirm_join$'))
dispatcher.add_handler(CallbackQueryHandler(show_guide_callback, pattern='^show_guide$'))
dispatcher.add_handler(CallbackQueryHandler(go_back_callback, pattern='^go_back$'))
dispatcher.add_handler(CallbackQueryHandler(ban_confirm_callback, pattern='^ban_'))
dispatcher.add_handler(CallbackQueryHandler(ban_confirm_callback, pattern='^cancel_ban$'))
dispatcher.add_handler(CallbackQueryHandler(unban_confirm_callback, pattern='^unban_'))
dispatcher.add_handler(CallbackQueryHandler(unban_confirm_callback, pattern='^cancel_unban$'))
dispatcher.add_handler(CallbackQueryHandler(send_broadcast_callback, pattern='^send_broadcast$'))
dispatcher.add_handler(CallbackQueryHandler(cancel_callback, pattern='^cancel_bc$'))

dispatcher.add_handler(MessageHandler(Filters.regex('^پشتیبانی$'), handle_support_request))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, ai_chat))
dispatcher.add_handler(MessageHandler(Filters.text & Filters.user(ADMIN_ID) & Filters.reply, handle_admin_reply))

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'OK'

@app.route('/')
def index():
    return 'Bot is running.'

if __name__ == '__main__':
    app.run()
