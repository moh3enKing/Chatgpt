import telebot
from flask import Flask, request
import requests
from pymongo import MongoClient

# ---------------------- تنظیمات ----------------------
BOT_TOKEN = "8089258024:AAFx2ieX_ii_TrI60wNRRY7VaLHEdD3-BP0"
CHANNEL_USERNAME = "@netgoris"
ADMIN_ID = 5637609683
MONGO_URL = "mongodb+srv://mohsenfeizi1386:RIHPhDJPhd9aNJvC@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
WEBHOOK_URL = "https://chatgpt-qg71.onrender.com"

# ---------------------- اتصال ----------------------
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
client = MongoClient(MONGO_URL)
db = client["TellGPT"]
users = db["users"]

# ---------------------- وب‌هوک ----------------------
@app.route('/', methods=["POST"])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 403

def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

# ---------------------- جین اجباری ----------------------
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ---------------------- استارت ----------------------
@bot.message_handler(commands=['start'])
def start_handler(message):
    user = users.find_one({"user_id": message.chat.id})
    if not user:
        users.insert_one({"user_id": message.chat.id})
        bot.send_message(ADMIN_ID, f"🔔 کاربر جدید: [{message.chat.first_name}](tg://user?id={message.chat.id})", parse_mode="Markdown")

    if not is_user_joined(message.chat.id):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
        markup.add(telebot.types.InlineKeyboardButton("✅ عضویت انجام شد", callback_data="check_join"))
        bot.send_message(message.chat.id, "👋 برای استفاده از ربات ابتدا در کانال عضو شوید:", reply_markup=markup)
    else:
        show_main_menu(message.chat.id)

# ---------------------- بررسی عضویت ----------------------
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    if is_user_joined(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.from_user.id, "✅ خوش آمدید! از ربات لذت ببرید.")
        show_main_menu(call.from_user.id)
    else:
        bot.answer_callback_query(call.id, "⚠️ ابتدا عضو کانال شوید.")

# ---------------------- منو اصلی ----------------------
def show_main_menu(chat_id):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📚 راهنما", "💬 پشتیبانی")
    bot.send_message(chat_id, "💡 خوش آمدید! لطفا یکی از گزینه‌ها را انتخاب کنید:", reply_markup=markup)

# ---------------------- دکمه راهنما ----------------------
@bot.message_handler(func=lambda msg: msg.text == "📚 راهنما")
def guide_handler(message):
    guide_text = (
        "📖 راهنمای ربات TellGPT\n"
        "✅ برای چت با هوش مصنوعی فقط متن ارسال کنید.\n"
        "🎥 ارسال لینک اینستاگرام: دانلود مستقیم\n"
        "🎧 ارسال لینک اسپاتیفای: دریافت آهنگ MP3\n"
        "📌 ارسال لینک پینترست: دریافت تصویر\n"
        "🖼 ارسال متن انگلیسی برای ساخت عکس\n"
        "⚠️ قوانین:\n"
        "- اسپم نکنید\n"
        "- رعایت ادب الزامیست\n"
    )
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💡 بازگشت")
    bot.send_message(message.chat.id, guide_text, reply_markup=markup)

# ---------------------- بازگشت از راهنما ----------------------
@bot.message_handler(func=lambda msg: msg.text == "💡 بازگشت")
def back_to_menu(message):
    show_main_menu(message.chat.id)

# ---------------------- پشتیبانی ----------------------
@bot.message_handler(func=lambda msg: msg.text == "💬 پشتیبانی")
def support_handler(message):
    bot.send_message(message.chat.id, "✍️ لطفاً پیام خود را ارسال کنید. برای لغو، بنویسید لغو.")
    bot.register_next_step_handler(message, forward_to_admin)

def forward_to_admin(message):
    if message.text.lower() == "لغو":
        bot.send_message(message.chat.id, "❌ پشتیبانی لغو شد.")
        show_main_menu(message.chat.id)
    else:
        bot.send_message(ADMIN_ID, f"📩 پیام جدید از [{message.from_user.first_name}](tg://user?id={message.chat.id}):\n{message.text}", parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ پیام شما ارسال شد. منتظر پاسخ بمانید.")
        show_main_menu(message.chat.id)

# ---------------------- پاسخ مدیر ----------------------
@bot.message_handler(func=lambda msg: msg.chat.id == ADMIN_ID and msg.reply_to_message)
def reply_handler(message):
    lines = message.reply_to_message.text.split("tg://user?id=")
    if len(lines) > 1:
        target_id = int(lines[1].split(")")[0])
        bot.send_message(target_id, f"💬 پاسخ مدیر:\n{message.text}")

# ---------------------- اجرای اصلی ----------------------
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=5000)
