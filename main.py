import re
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait

# --- تنظیمات کامل ---
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"
BOT_TOKEN = "8175470749:AAGjaYSVosmfk6AmuqXvcVbSUJAqS200q3c"

# کانال مقصد ثابت
DEST_CHANNEL = "@netgoris"

# کانال مبدا (بعداً با دستور ست میشه)
source_channel = None

# وضعیت ربات (خاموش/روشن)
running = True

# ساخت کلاینت Pyrogram
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- تابع تشخیص کانفیگ ---
def extract_configs(text: str):
    configs = []
    if not text:
        return configs
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith(("vless://", "vmess://", "ss://", "trojan://")):
            # حذف همه تگ‌های @
            clean = re.sub(r'@\w+', '', line).strip()
            configs.append(clean)
    return configs

# --- پردازش پیام ---
def process_message(msg_text):
    configs = extract_configs(msg_text)
    if not configs:
        return None
    result = "\n".join(configs)
    result += "\n@netgoris\n\n@netgoris"
    return result

# --- دستور استارت ---
@app.on_message(filters.command("start"))
async def start(message):
    await message.reply(
        "سلام 👋\nبا این ربات میتونی کانال مبدا رو ست کنی تا هر ۵ دقیقه آخرین کانفیگ‌هاشو بفرستم توی @netgoris ✅\n"
        "دستورات:\n"
        "/stop - خاموش کردن بررسی کانال\n"
        "/startcheck - روشن کردن بررسی کانال"
    )

# --- دستور تنظیم کانال مبدا ---
@app.on_message(filters.text & ~filters.command)
async def set_source(client, message):
    global source_channel
    if message.text.startswith("@") or message.text.startswith("-100"):
        source_channel = message.text.strip()
        await message.reply(f"کانال مبدا تنظیم شد: {source_channel}")

# --- دستور خاموش کردن بررسی ---
@app.on_message(filters.command("stop"))
async def stop_check(client, message):
    global running
    running = False
    await message.reply("بررسی کانال متوقف شد ✅")

# --- دستور روشن کردن بررسی ---
@app.on_message(filters.command("startcheck"))
async def start_check(client, message):
    global running
    running = True
    await message.reply("بررسی کانال روشن شد ✅")

# --- بک‌گراند برای بررسی پیام‌ها ---
async def background_worker():
    global source_channel, running
    last_sent = None
    while True:
        try:
            if running and source_channel:
                async for msg in app.get_chat_history(source_channel, limit=20):
                    if msg.text:
                        processed = process_message(msg.text)
                        if processed and processed != last_sent:
                            await app.send_message(DEST_CHANNEL, processed)
                            last_sent = processed
                            break
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print("Error in background_worker:", e)
        await asyncio.sleep(300)  # هر ۵ دقیقه

# --- ران ---
async def main():
    await app.start()
    asyncio.create_task(background_worker())
    print("Bot is running...")
    await asyncio.get_event_loop().create_future()  # برای زنده نگه داشتن

if __name__ == "__main__":
    asyncio.run(main())
