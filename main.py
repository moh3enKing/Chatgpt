import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
from urllib.parse import unquote

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

# Configuration

BOT_TOKEN = “7881643365:AAEkvX2FvEBHHKvCLVLwBNiXXIidwNGwAzE”
ADMIN_ID = 5637609683
CHANNEL_USERNAME = “netgoris”
MONGODB_URL = “mongodb+srv://mohsenfeizi1386:p%40ssw0rd%279%27%21@cluster0.ounkvru.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0”
WEBHOOK_URL = “https://chatgpt-qg71.onrender.com”
PORT = 1000

# Database setup

client = AsyncIOMotorClient(MONGODB_URL)
db = client.chatroom_bot
users_collection = db.users
banned_users_collection = db.banned_users

# Global variables

bot_enabled = True
user_spam_tracker = {}
user_last_message_time = {}

# Logging setup

logging.basicConfig(
format=’%(asctime)s - %(name)s - %(levelname)s - %(message)s’,
level=logging.INFO
)
logger = logging.getLogger(**name**)

# User states

WAITING_FOR_NAME = “waiting_for_name”
ACTIVE = “active”

class ChatBot:
def **init**(self):
self.bot = Bot(token=BOT_TOKEN)
self.application = Application.builder().token(BOT_TOKEN).build()
self.setup_handlers()

```
def setup_handlers(self):
    """Setup all command and message handlers"""
    self.application.add_handler(CommandHandler("start", self.start))
    self.application.add_handler(CommandHandler("admin", self.admin_panel))
    self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    self.application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE | filters.DOCUMENT, self.handle_media))
    self.application.add_handler(MessageHandler(filters.ANIMATION, self.handle_gif))

async def check_channel_membership(self, user_id: int) -> bool:
    """Check if user is member of required channel"""
    try:
        member = await self.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except TelegramError:
        return False

async def is_user_banned(self, user_id: int) -> bool:
    """Check if user is banned"""
    result = await banned_users_collection.find_one({"user_id": user_id})
    return result is not None

async def get_user_data(self, user_id: int) -> Optional[Dict]:
    """Get user data from database"""
    return await users_collection.find_one({"user_id": user_id})

async def save_user_data(self, user_id: int, data: Dict):
    """Save user data to database"""
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": data},
        upsert=True
    )

async def is_name_taken(self, name: str, user_id: int) -> bool:
    """Check if name is already taken by another user"""
    result = await users_collection.find_one({"name": name, "user_id": {"$ne": user_id}})
    return result is not None

async def check_spam(self, user_id: int) -> bool:
    """Check if user is spamming (more than 3 messages per second)"""
    current_time = datetime.now()
    
    if user_id not in user_spam_tracker:
        user_spam_tracker[user_id] = []
    
    # Remove old messages (older than 1 second)
    user_spam_tracker[user_id] = [
        msg_time for msg_time in user_spam_tracker[user_id]
        if current_time - msg_time < timedelta(seconds=1)
    ]
    
    # Add current message
    user_spam_tracker[user_id].append(current_time)
    
    # Check if more than 3 messages in 1 second
    if len(user_spam_tracker[user_id]) > 3:
        return True
    
    return False

async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    
    if not bot_enabled and user_id != ADMIN_ID:
        await update.message.reply_text("🔒 ربات در حال حاضر غیرفعال است.")
        return
    
    if await self.is_user_banned(user_id):
        await update.message.reply_text("❌ شما از ربات مسدود شده‌اید.")
        return
    
    # Check channel membership
    if not await self.check_channel_membership(user_id):
        keyboard = [
            [InlineKeyboardButton("🔷 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("✅ تایید عضویت", callback_data="check_membership")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"لطفاً برای استفاده از ربات در کانال @{CHANNEL_USERNAME} عضو شوید:",
            reply_markup=reply_markup
        )
        return
    
    # Check if user already exists and is active
    user_data = await self.get_user_data(user_id)
    if user_data and user_data.get("state") == ACTIVE:
        await update.message.reply_text(
            f"سلام {user_data.get('name')}! 👋\n"
            "شما قبلاً در ربات ثبت‌نام کرده‌اید. می‌توانید پیام‌های خود را ارسال کنید."
        )
        return
    
    # Show rules
    await self.show_rules(update.effective_chat.id, user_id)

async def show_rules(self, chat_id: int, user_id: int):
    """Show rules to user"""
    rules_text = f"""سلام کاربر @{user_id}
```

به ربات chat room خوش آمدین

اینجا شما آزاد هستید که به صورت ناشناس با دیگر اعضای گروه در ارتباط باشید و چت کنید و با هم آشنا بشید

اما قوانینی وجود دارد که باید رعایت کنید تا از ربات مسدود نشوید

1» این ربات صرفاً برای سرگرمی و چت کردن هست و دوست یابی
پس از ربات برای تبلیغات و درخواست پول و غیره استفاده نکنید

2» ارسال گیف در ربات به علت شلوغ نشدن ربات ممنوعه
اما ارسال عکس و موسیقی و غیره آزاده اما محتوای غیر اخلاقی ارسال نکنید

3» ربات دارای ضد اسپم است پس ربات رو اسپم نکنید که سکوت میخورید به مدت 2 دقیقه

4» به یکدیگر احترام بذارید اگه فحاشی یا محتوای غیر اخلاقی دیدید با ریپلای روی پیام و ارسال دستور ( گزارش) به ادمین اطلاع بدید

ربات در نسخه اولیه هست اپدیت های جدید تو راهه
دوستان خودتون رو به ربات معرفی کنید تا تجربه بهتری در چت کردن داشته باشید
موفق باشید”””

```
    keyboard = [
        [InlineKeyboardButton("🔷 قوانین", callback_data="show_rules")],
        [InlineKeyboardButton("✅ تایید قوانین", callback_data="accept_rules")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await self.bot.send_message(
        chat_id=chat_id,
        text="آیا قوانین و مقررات را تایید می‌کنید؟",
        reply_markup=reply_markup
    )

async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if query.data == "check_membership":
        if await self.check_channel_membership(user_id):
            await query.edit_message_text("✅ عضویت شما تایید شد!")
            await asyncio.sleep(1)
            await self.show_rules(query.message.chat.id, user_id)
        else:
            await query.answer("❌ لطفاً ابتدا در کانال عضو شوید!", show_alert=True)
    
    elif query.data == "show_rules":
        rules_text = f"""سلام کاربر @{user_id}
```

به ربات chat room خوش آمدین

اینجا شما آزاد هستید که به صورت ناشناس با دیگر اعضای گروه در ارتباط باشید و چت کنید و با هم آشنا بشید

اما قوانینی وجود دارد که باید رعایت کنید تا از ربات مسدود نشوید

1» این ربات صرفاً برای سرگرمی و چت کردن هست و دوست یابی
پس از ربات برای تبلیغات و درخواست پول و غیره استفاده نکنید

2» ارسال گیف در ربات به علت شلوغ نشدن ربات ممنوعه
اما ارسال عکس و موسیقی و غیره آزاده اما محتوای غیر اخلاقی ارسال نکنید

3» ربات دارای ضد اسپم است پس ربات رو اسپم نکنید که سکوت میخورید به مدت 2 دقیقه

4» به یکدیگر احترام بذارید اگه فحاشی یا محتوای غیر اخلاقی دیدید با ریپلای روی پیام و ارسال دستور ( گزارش) به ادمین اطلاع بدید

ربات در نسخه اولیه هست اپدیت های جدید تو راهه
دوستان خودتون رو به ربات معرفی کنید تا تجربه بهتری در چت کردن داشته باشید
موفق باشید”””

```
        await query.edit_message_text(rules_text)
    
    elif query.data == "accept_rules":
        await query.edit_message_text(
            "لطفاً نام خود را در ربات ارسال کنید:\n\n"
            "⚠️ توجه: از فونت‌های ساده استفاده کنید و از فونت‌های گرافیکی خودداری کنید."
        )
        await self.save_user_data(user_id, {"state": WAITING_FOR_NAME})
    
    # Admin panel callbacks
    elif query.data == "toggle_bot":
        if user_id == ADMIN_ID:
            global bot_enabled
            bot_enabled = not bot_enabled
            status = "فعال" if bot_enabled else "غیرفعال"
            await query.edit_message_text(
                f"🔧 پنل مدیریت\n\n"
                f"وضعیت ربات: {status}\n\n"
                f"برای بن کردن کاربر روی پیام او ریپلای کنید و 'بن' بنویسید\n"
                f"برای آن‌بن کردن کاربر روی پیام او ریپلای کنید و 'آن‌بن' بنویسید",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"🔴 {'غیرفعال' if bot_enabled else 'فعال'} کردن ربات", callback_data="toggle_bot")]
                ])
            )
        else:
            await query.answer("❌ شما اجازه دسترسی ندارید!", show_alert=True)

async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    if not bot_enabled and user_id != ADMIN_ID:
        return
    
    if await self.is_user_banned(user_id):
        await update.message.reply_text("❌ شما از ربات مسدود شده‌اید.")
        return
    
    # Check spam
    if await self.check_spam(user_id):
        await update.message.reply_text("⚠️ شما به دلیل ارسال پیام‌های زیاد، برای 2 دقیقه سکوت شدید.")
        return
    
    # Admin commands
    if user_id == ADMIN_ID:
        if update.message.reply_to_message:
            replied_user_id = update.message.reply_to_message.from_user.id
            
            if message_text.lower() == "بن":
                await banned_users_collection.insert_one({"user_id": replied_user_id})
                await update.message.reply_text("✅ کاربر با موفقیت بن شد.")
                return
            
            elif message_text.lower() == "آن‌بن":
                await banned_users_collection.delete_one({"user_id": replied_user_id})
                await update.message.reply_text("✅ کاربر با موفقیت آن‌بن شد.")
                return
    
    # Get user data
    user_data = await self.get_user_data(user_id)
    
    # Handle name input
    if user_data and user_data.get("state") == WAITING_FOR_NAME:
        # Check for fancy fonts
        if self.has_fancy_fonts(message_text):
            await update.message.reply_text(
                "⚠️ لطفاً از فونت‌های ساده استفاده کنید و از فونت‌های گرافیکی خودداری کنید.\n"
                "نام خود را مجدداً ارسال کنید:"
            )
            return
        
        # Check if name is taken
        if await self.is_name_taken(message_text, user_id):
            await update.message.reply_text(
                "❌ این نام قبلاً انتخاب شده است. لطفاً نام دیگری انتخاب کنید:"
            )
            return
        
        # Save user name and activate
        await self.save_user_data(user_id, {
            "name": message_text,
            "state": ACTIVE,
            "joined_at": datetime.now()
        })
        
        await update.message.reply_text(
            f"✅ خوش آمدید {message_text}!\n"
            "حالا می‌توانید با دیگر اعضای گروه چت کنید. پیام‌های شما به صورت ناشناس برای همه ارسال می‌شود."
        )
        return
    
    # Handle regular chat messages
    if user_data and user_data.get("state") == ACTIVE:
        # Handle report
        if message_text.lower() == "گزارش" and update.message.reply_to_message:
            await self.handle_report(update, context)
            return
        
        # Broadcast message to all active users
        await self.broadcast_message(update, user_data)

async def handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle media messages (photo, video, audio, etc.)"""
    user_id = update.effective_user.id
    
    if not bot_enabled and user_id != ADMIN_ID:
        return
    
    if await self.is_user_banned(user_id):
        return
    
    # Check spam
    if await self.check_spam(user_id):
        await update.message.reply_text("⚠️ شما به دلیل ارسال پیام‌های زیاد، برای 2 دقیقه سکوت شدید.")
        return
    
    user_data = await self.get_user_data(user_id)
    
    if user_data and user_data.get("state") == ACTIVE:
        await self.broadcast_media(update, user_data)

async def handle_gif(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle GIF messages (blocked)"""
    await update.message.reply_text("❌ ارسال گیف در ربات ممنوع است.")

async def handle_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle report messages"""
    if update.message.reply_to_message:
        reported_message = update.message.reply_to_message
        reporter_id = update.effective_user.id
        
        # Forward the reported message to admin
        await self.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🚨 گزارش جدید از کاربر {reporter_id}:\n\n"
                 f"پیام گزارش شده:",
            reply_to_message_id=reported_message.message_id if reported_message else None
        )
        
        # If there's a replied message, forward it
        if reported_message:
            await self.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=update.effective_chat.id,
                message_id=reported_message.message_id
            )
        
        await update.message.reply_text("✅ گزارش شما ارسال شد.")

def has_fancy_fonts(self, text: str) -> bool:
    """Check if text contains fancy fonts"""
    # Check for non-standard Unicode characters that might be fancy fonts
    fancy_ranges = [
        (0x1D400, 0x1D7FF),  # Mathematical symbols
        (0x1F100, 0x1F1FF),  # Enclosed characters
        (0x2100, 0x214F),    # Letterlike symbols
        (0x1D00, 0x1D7F),    # Phonetic extensions
    ]
    
    for char in text:
        char_code = ord(char)
        for start, end in fancy_ranges:
            if start <= char_code <= end:
                return True
    return False

async def broadcast_message(self, update: Update, sender_data: Dict):
    """Broadcast text message to all active users"""
    message_text = update.message.text
    sender_name = sender_data.get("name", "ناشناس")
    
    # Get all active users
    async for user in users_collection.find({"state": ACTIVE}):
        if user["user_id"] != update.effective_user.id:
            try:
                await self.bot.send_message(
                    chat_id=user["user_id"],
                    text=f"👤 {sender_name}:\n{message_text}"
                )
            except TelegramError:
                # User might have blocked the bot
                pass

async def broadcast_media(self, update: Update, sender_data: Dict):
    """Broadcast media message to all active users"""
    sender_name = sender_data.get("name", "ناشناس")
    caption = f"👤 {sender_name}"
    
    if update.message.caption:
        caption += f":\n{update.message.caption}"
    
    # Get all active users
    async for user in users_collection.find({"state": ACTIVE}):
        if user["user_id"] != update.effective_user.id:
            try:
                if update.message.photo:
                    await self.bot.send_photo(
                        chat_id=user["user_id"],
                        photo=update.message.photo[-1].file_id,
                        caption=caption
                    )
                elif update.message.video:
                    await self.bot.send_video(
                        chat_id=user["user_id"],
                        video=update.message.video.file_id,
                        caption=caption
                    )
                elif update.message.audio:
                    await self.bot.send_audio(
                        chat_id=user["user_id"],
                        audio=update.message.audio.file_id,
                        caption=caption
                    )
                elif update.message.voice:
                    await self.bot.send_voice(
                        chat_id=user["user_id"],
                        voice=update.message.voice.file_id,
                        caption=caption
                    )
                elif update.message.document:
                    await self.bot.send_document(
                        chat_id=user["user_id"],
                        document=update.message.document.file_id,
                        caption=caption
                    )
            except TelegramError:
                # User might have blocked the bot
                pass

async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel command"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ شما اجازه دسترسی ندارید!")
        return
    
    status = "فعال" if bot_enabled else "غیرفعال"
    keyboard = [
        [InlineKeyboardButton(f"🔴 {'غیرفعال' if bot_enabled else 'فعال'} کردن ربات", callback_data="toggle_bot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔧 پنل مدیریت\n\n"
        f"وضعیت ربات: {status}\n\n"
        f"برای بن کردن کاربر روی پیام او ریپلای کنید و 'بن' بنویسید\n"
        f"برای آن‌بن کردن کاربر روی پیام او ریپلای کنید و 'آن‌بن' بنویسید",
        reply_markup=reply_markup
    )

async def run_webhook(self):
    """Run bot with webhook"""
    await self.application.initialize()
    await self.application.start()
    
    # Set webhook
    webhook_url = f"{WEBHOOK_URL}/webhook"
    await self.application.bot.set_webhook(webhook_url)
    
    # Start webhook
    await self.application.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="/webhook",
        webhook_url=webhook_url
    )
    
    logger.info(f"Bot started with webhook: {webhook_url}")
    
    # Keep the application running
    await asyncio.Event().wait()
```

def main():
“”“Main function”””
bot = ChatBot()
asyncio.run(bot.run_webhook())

if **name** == “**main**”:
main()
