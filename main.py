import logging
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import quote

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError

import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# تنظیمات

TOKEN = “7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE”
ADMIN_ID = 5637609683
CHANNEL_USERNAME = “netgoris”
WEBHOOK_URL = “https://chatgpt-qg71.onrender.com”
MONGODB_URI = “mongodb+srv://mohsenfeizi1386:p%40s+sw0+rd%279%27%21@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0”

# تنظیمات MongoDB

client = AsyncIOMotorClient(MONGODB_URI)
db = client.chatbot_db
users_collection = db.users
messages_collection = db.messages
settings_collection = db.settings

# متغیرهای سراسری

bot_active = True
user_last_message = {}
banned_users = set()
forbidden_names = {‘admin’, ‘administrator’, ‘moderator’, ‘mod’, ‘support’, ‘bot’, ‘chatbot’, ‘owner’, ‘root’, ‘staff’}

# متن قوانین

RULES_TEXT = “”“سلام کاربر @{username}
به ربات chat room خوش آمدین

اینجا شما آزاد هستید که به صورت ناشناس با دیگر اعضای گروه در ارتباط باشید و چت کنید و با هم آشنا بشید

اما قوانینی وجود دارد که باید رعایت کنید تا از ربات مسدود نشید

1» این ربات صرفاً برای سرگرمی و چت کردن هست و دوست یابی
پس از ربات برای تبلیغات و درخواست پول و غیره استفاده نکنید

2» ارسال گیف در ربات به علت شلوغ نشدن ربات ممنوعه
اما ارسال عکس و موسیقی و غیره آزاده اما محتوای غیر اخلاقی ارسال نکنید

3» ربات دارای ضد اسپم است پس ربات رو اسپم نکنید که سکوت میخورید به مدت 2 دقیقه

4» به یکدیگر احترام بذارید اگه فحاشی یا محتوای غیر اخلاقی دیدید با ریپلای روی پیام و ارسال دستور (گزارش) به ادمین اطلاع بدید

ربات در نسخه اولیه هست اپدیت های جدید تو راهه
دوستان خودتون رو به ربات معرفی کنید تا تجربه بهتری در چت کردن داشته باشید
موفق باشید”””

# لاگینگ

logging.basicConfig(
format=’%(asctime)s - %(name)s - %(levelname)s - %(message)s’,
level=logging.INFO
)
logger = logging.getLogger(**name**)

# توابع کمکی

async def is_user_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
“”“بررسی عضویت کاربر در کانال”””
try:
member = await context.bot.get_chat_member(f”@{CHANNEL_USERNAME}”, user_id)
return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
except:
return False

async def get_user_data(user_id: int) -> Optional[Dict]:
“”“دریافت اطلاعات کاربر از دیتابیس”””
return await users_collection.find_one({“user_id”: user_id})

async def save_user_data(user_data: Dict):
“”“ذخیره اطلاعات کاربر در دیتابیس”””
await users_collection.replace_one(
{“user_id”: user_data[“user_id”]},
user_data,
upsert=True
)

async def get_all_users() -> List[Dict]:
“”“دریافت همه کاربران”””
return await users_collection.find({}).to_list(None)

async def is_banned(user_id: int) -> bool:
“”“بررسی مسدود بودن کاربر”””
user_data = await get_user_data(user_id)
return user_data and user_data.get(“banned”, False)

async def ban_user(user_id: int):
“”“مسدود کردن کاربر”””
await users_collection.update_one(
{“user_id”: user_id},
{”$set”: {“banned”: True}},
upsert=True
)

async def unban_user(user_id: int):
“”“رفع مسدودیت کاربر”””
await users_collection.update_one(
{“user_id”: user_id},
{”$set”: {“banned”: False}},
upsert=True
)

async def get_bot_status() -> bool:
“”“دریافت وضعیت ربات”””
settings = await settings_collection.find_one({“key”: “bot_active”})
return settings.get(“value”, True) if settings else True

async def set_bot_status(status: bool):
“”“تنظیم وضعیت ربات”””
await settings_collection.replace_one(
{“key”: “bot_active”},
{“key”: “bot_active”, “value”: status},
upsert=True
)

def is_english_only(text: str) -> bool:
“”“بررسی انگلیسی بودن متن”””
return bool(re.match(r’^[a-zA-Z0-9_]+$’, text))

def has_special_fonts(text: str) -> bool:
“”“بررسی استفاده از فونت های خاص”””
# بررسی کاراکترهای یونیکد خاص
special_chars = [’\u200d’, ‘\u200c’, ‘\u200b’, ‘\u2060’, ‘\u180e’]
for char in special_chars:
if char in text:
return True

```
# بررسی کاراکترهای فرمت خاص
if any(ord(c) > 127 and not (0x0600 <= ord(c) <= 0x06FF) for c in text):
    return True

return False
```

# هندلرها

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“شروع ربات”””
user_id = update.effective_user.id
username = update.effective_user.username or “کاربر”

```
if await is_banned(user_id):
    await update.message.reply_text("شما از ربات مسدود شده اید.")
    return

if not await get_bot_status():
    await update.message.reply_text("ربات در حال حاضر غیرفعال است.")
    return

# بررسی کاربر قبلی
user_data = await get_user_data(user_id)
if user_data and user_data.get("registered", False):
    await update.message.reply_text(f"سلام {user_data.get('display_name', username)}! قبلاً ثبت نام کرده‌اید. خوش آمدید!")
    return

# بررسی عضویت در کانال
if not await is_user_member(user_id, context):
    keyboard = [[InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    join_message = await update.message.reply_text(
        f"برای استفاده از ربات ابتدا باید در کانال @{CHANNEL_USERNAME} عضو شوید:",
        reply_markup=reply_markup
    )
    
    # ذخیره شناسه پیام برای حذف بعدی
    user_temp_data = {
        "user_id": user_id,
        "join_message_id": join_message.message_id,
        "step": "waiting_join"
    }
    await save_user_data(user_temp_data)
    
    # اضافه کردن دکمه تایید
    keyboard.append([InlineKeyboardButton("✅ تایید عضویت", callback_data="check_membership")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await join_message.edit_reply_markup(reply_markup=reply_markup)
else:
    await show_rules(update, context)
```

async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“بررسی عضویت پس از کلیک دکمه”””
query = update.callback_query
await query.answer()

```
user_id = query.from_user.id

if await is_user_member(user_id, context):
    # حذف پیام جوین اجباری
    try:
        await query.message.delete()
    except:
        pass
    
    # نمایش قوانین
    await show_rules_for_user(user_id, context)
else:
    await query.answer("هنوز در کانال عضو نشده‌اید!", show_alert=True)
```

async def show_rules_for_user(user_id: int, context: ContextTypes.DEFAULT_TYPE):
“”“نمایش قوانین برای کاربر خاص”””
user_data = await get_user_data(user_id)
username = user_data.get(“username”, “کاربر”) if user_data else “کاربر”

```
rules_text = RULES_TEXT.format(username=username)

# دکمه تایید قوانین
keyboard = [[InlineKeyboardButton("✅ تایید قوانین", callback_data="accept_rules")]]
reply_markup = InlineKeyboardMarkup(keyboard)

await context.bot.send_message(
    chat_id=user_id,
    text="قوانین و مقررات را تایید می‌کنید؟",
    reply_markup=reply_markup
)
```

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“نمایش قوانین”””
user_id = update.effective_user.id
username = update.effective_user.username or “کاربر”

```
rules_text = RULES_TEXT.format(username=username)

# دکمه‌های قوانین
keyboard = [
    [InlineKeyboardButton("📋 قوانین", callback_data="show_rules")],
    [InlineKeyboardButton("✅ تایید قوانین", callback_data="accept_rules")]
]
reply_markup = InlineKeyboardMarkup(keyboard)

await update.message.reply_text(
    "قوانین و مقررات را تایید می‌کنید؟",
    reply_markup=reply_markup
)
```

async def rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“نمایش قوانین با callback”””
query = update.callback_query
await query.answer()

```
user_id = query.from_user.id
username = query.from_user.username or "کاربر"

rules_text = RULES_TEXT.format(username=username)

# فقط متن قوانین بدون دکمه
await query.message.edit_text(rules_text)
```

async def accept_rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“تایید قوانین”””
query = update.callback_query
await query.answer()

```
user_id = query.from_user.id

# درخواست نام
await query.message.edit_text(
    "لطفاً نام نمایشی خود را به انگلیسی وارد کنید:\n\n"
    "⚠️ نام باید به انگلیسی باشد و از کاراکترهای خاص استفاده نکنید"
)

# به‌روزرسانی وضعیت کاربر
user_data = await get_user_data(user_id) or {"user_id": user_id}
user_data["step"] = "waiting_name"
await save_user_data(user_data)
```

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“مدیریت پیام‌ها”””
user_id = update.effective_user.id

```
if await is_banned(user_id):
    await update.message.reply_text("شما از ربات مسدود شده اید.")
    return

if not await get_bot_status():
    return

# بررسی اسپم
now = datetime.now()
if user_id in user_last_message:
    time_diff = now - user_last_message[user_id]
    if time_diff < timedelta(seconds=2):
        await update.message.reply_text("لطفاً 2 دقیقه صبر کنید. (ضد اسپم)")
        return

user_last_message[user_id] = now

user_data = await get_user_data(user_id)

if not user_data:
    await update.message.reply_text("لطفاً ابتدا ربات را استارت کنید: /start")
    return

# مراحل ثبت نام
if user_data.get("step") == "waiting_name":
    await handle_name_registration(update, context, user_data)
    return

# بررسی ثبت نام کامل
if not user_data.get("registered", False):
    await update.message.reply_text("لطفاً ابتدا فرآیند ثبت نام را تکمیل کنید.")
    return

# مدیریت دستورات ادمین
if user_id == ADMIN_ID:
    await handle_admin_commands(update, context)
    return

# بررسی گیف
if update.message.animation:
    await update.message.reply_text("ارسال گیف در ربات ممنوع است.")
    return

# ارسال پیام به همه کاربران
await broadcast_message(update, context)
```

async def handle_name_registration(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: Dict):
“”“مدیریت ثبت نام”””
name = update.message.text.strip()

```
# بررسی فونت خاص
if has_special_fonts(name):
    await update.message.reply_text(
        "⚠️ از فونت‌های خاص یا کاراکترهای غیرمعمول استفاده نکنید.\n"
        "لطفاً نام خود را با حروف انگلیسی ساده وارد کنید."
    )
    return

# بررسی انگلیسی بودن
if not is_english_only(name):
    await update.message.reply_text(
        "⚠️ نام باید فقط به انگلیسی باشد.\n"
        "لطفاً نام خود را با حروف انگلیسی وارد کنید."
    )
    return

# بررسی نام‌های ممنوع
if name.lower() in forbidden_names:
    await update.message.reply_text(
        "⚠️ این نام مجاز نیست.\n"
        "لطفاً نام دیگری انتخاب کنید."
    )
    return

# بررسی طول نام
if len(name) < 2 or len(name) > 20:
    await update.message.reply_text(
        "⚠️ نام باید بین 2 تا 20 کاراکتر باشد.\n"
        "لطفاً نام مناسب انتخاب کنید."
    )
    return

# ثبت نام موفق
user_data["display_name"] = name
user_data["registered"] = True
user_data["step"] = "completed"
user_data["username"] = update.effective_user.username
user_data["join_date"] = datetime.now()

await save_user_data(user_data)

await update.message.reply_text(
    f"✅ ثبت نام شما با موفقیت انجام شد!\n"
    f"نام نمایشی: {name}\n\n"
    f"حالا می‌توانید در چت گروهی شرکت کنید."
)
```

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“ارسال پیام به همه کاربران”””
user_id = update.effective_user.id
user_data = await get_user_data(user_id)

```
if not user_data or not user_data.get("registered", False):
    return

display_name = user_data.get("display_name", "کاربر")

# ذخیره پیام در دیتابیس
message_data = {
    "user_id": user_id,
    "display_name": display_name,
    "message_id": update.message.message_id,
    "timestamp": datetime.now(),
    "message_type": "text",
    "forwarded": False
}

if update.message.reply_to_message:
    message_data["reply_to"] = update.message.reply_to_message.message_id

await messages_collection.insert_one(message_data)

# ارسال به همه کاربران
users = await get_all_users()
message_text = f"👤 {display_name}:\n{update.message.text}"

for user in users:
    if user["user_id"] != user_id and user.get("registered", False) and not user.get("banned", False):
        try:
            if update.message.reply_to_message:
                # پیام ریپلای
                await context.bot.send_message(
                    chat_id=user["user_id"],
                    text=f"↩️ پاسخ به پیام:\n{message_text}",
                    reply_to_message_id=update.message.reply_to_message.message_id
                )
            else:
                # پیام عادی
                if update.message.photo:
                    await context.bot.send_photo(
                        chat_id=user["user_id"],
                        photo=update.message.photo[-1].file_id,
                        caption=f"👤 {display_name}:\n{update.message.caption or ''}"
                    )
                elif update.message.voice:
                    await context.bot.send_voice(
                        chat_id=user["user_id"],
                        voice=update.message.voice.file_id,
                        caption=f"👤 {display_name}"
                    )
                elif update.message.audio:
                    await context.bot.send_audio(
                        chat_id=user["user_id"],
                        audio=update.message.audio.file_id,
                        caption=f"👤 {display_name}"
                    )
                elif update.message.video:
                    await context.bot.send_video(
                        chat_id=user["user_id"],
                        video=update.message.video.file_id,
                        caption=f"👤 {display_name}:\n{update.message.caption or ''}"
                    )
                elif update.message.document:
                    await context.bot.send_document(
                        chat_id=user["user_id"],
                        document=update.message.document.file_id,
                        caption=f"👤 {display_name}:\n{update.message.caption or ''}"
                    )
                else:
                    await context.bot.send_message(
                        chat_id=user["user_id"],
                        text=message_text
                    )
        except Exception as e:
            logger.error(f"Error sending message to user {user['user_id']}: {e}")
```

async def handle_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“مدیریت دستورات ادمین”””
text = update.message.text.lower()

```
if text == "/panel":
    keyboard = [
        [InlineKeyboardButton("🚫 مسدود کردن", callback_data="ban_user")],
        [InlineKeyboardButton("✅ رفع مسدودیت", callback_data="unban_user")],
        [InlineKeyboardButton("🔴 خاموش کردن ربات", callback_data="bot_off")],
        [InlineKeyboardButton("🟢 روشن کردن ربات", callback_data="bot_on")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("پنل مدیریت:", reply_markup=reply_markup)
    return

if text == "بن" and update.message.reply_to_message:
    # بن کردن کاربر
    target_user_id = update.message.reply_to_message.from_user.id
    await ban_user(target_user_id)
    await update.message.reply_text(f"کاربر {target_user_id} مسدود شد.")
    
    # اطلاع به کاربر
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text="شما توسط ادمین از ربات مسدود شدید."
        )
    except:
        pass
    return

# ارسال پیام ادمین
await broadcast_admin_message(update, context)
```

async def broadcast_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“ارسال پیام ادمین به همه”””
users = await get_all_users()
message_text = f”👑 ادمین:\n{update.message.text}”

```
for user in users:
    if user["user_id"] != ADMIN_ID and user.get("registered", False) and not user.get("banned", False):
        try:
            await context.bot.send_message(
                chat_id=user["user_id"],
                text=message_text
            )
        except Exception as e:
            logger.error(f"Error sending admin message to user {user['user_id']}: {e}")
```

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“مدیریت پنل ادمین”””
query = update.callback_query
await query.answer()

```
if query.from_user.id != ADMIN_ID:
    await query.answer("شما ادمین نیستید!", show_alert=True)
    return

if query.data == "bot_off":
    await set_bot_status(False)
    await query.message.edit_text("ربات خاموش شد.")
elif query.data == "bot_on":
    await set_bot_status(True)
    await query.message.edit_text("ربات روشن شد.")
```

async def report_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“گزارش پیام”””
if update.message.text.lower() == “گزارش” and update.message.reply_to_message:
user_id = update.effective_user.id
user_data = await get_user_data(user_id)

```
    if not user_data:
        return
    
    reporter_name = user_data.get("display_name", "کاربر")
    
    # ارسال گزارش به ادمین
    try:
        await context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.reply_to_message.message_id
        )
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"گزارش جدید از {reporter_name}"
        )
        await update.message.reply_text("گزارش شما ارسال شد.")
    except Exception as e:
        logger.error(f"Error sending report: {e}")
```

def main():
“”“اجرای ربات”””
application = Application.builder().token(TOKEN).build()

```
# هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("panel", handle_admin_commands))
application.add_handler(CallbackQueryHandler(check_membership_callback, pattern="check_membership"))
application.add_handler(CallbackQueryHandler(rules_callback, pattern="show_rules"))
application.add_handler(CallbackQueryHandler(accept_rules_callback, pattern="accept_rules"))
application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="bot_"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE | filters.DOCUMENT, handle_message))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'گزارش'), report_message))

# اجرای ربات
application.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 8443)),
    url_path=TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
)
```

if **name** == ‘**main**’:
import os
main()
