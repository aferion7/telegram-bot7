import os
import re
import asyncio
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel
from dotenv import load_dotenv

load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))  # Sizning Telegram ID

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

loop = asyncio.new_event_loop()

user = TelegramClient("user_session", api_id, api_hash, loop=loop)
bot = TelegramClient("bot_session", api_id, api_hash, loop=loop)

def parse_link(link):
    link = link.split("?")[0].strip()
    m = re.search(r"t\.me/c/(\d+)/(\d+)", link)
    if m:
        channel_id = int("-100" + m.group(1))
        post_id = int(m.group(2))
        return channel_id, post_id
    m = re.search(r"t\.me/([A-Za-z0-9_]+)/(\d+)", link)
    if m:
        return m.group(1), int(m.group(2))
    return None, None

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "📥 Telegram post link yubor.\n\n"
        "Misol:\nhttps://t.me/c/1234567890/45"
    )

@bot.on(events.NewMessage)
async def handler(event):
    text = event.raw_text.strip()
    if text.startswith("/"):
        return
    if "t.me/" not in text:
        return

    sender_id = event.sender_id
    is_owner = (sender_id == OWNER_ID)

    await event.reply("⏳ Yuklayapman...")
    channel, post_id = parse_link(text)
    if not channel:
        await event.reply("❌ Link noto'g'ri.")
        return

    try:
        if isinstance(channel, str):
            entity = await user.get_entity(channel)
            post = await user.get_messages(entity, ids=post_id)
        else:
            peer = PeerChannel(int(str(channel).replace("-100", "")))
            post = await user.get_messages(peer, ids=post_id)

        if not post:
            await event.reply("❌ Post topilmadi.")
            return

        caption = post.text or ""

        if post.media:
            await event.reply("📥 Media yuklanmoqda...")
            file_path = await user.download_media(post, file=DOWNLOAD_DIR)
            if not file_path:
                await event.reply("❌ Media yuklab bo'lmadi.")
                return

            # Faylni so'ragan odamga yubor
            await bot.send_file(event.chat_id, file_path, caption=caption[:1000])

            # Agar so'ragan owner bo'lmasa — ownerga ham yuvor
            if not is_owner:
                user_info = await bot.get_entity(sender_id)
                username = getattr(user_info, 'username', None)
                first_name = getattr(user_info, 'first_name', '') or ''

                if username:
                    user_label = f"@{username} (ID: {sender_id})"
                else:
                    user_label = f"{first_name} (ID: {sender_id})"

                await bot.send_file(
                    OWNER_ID,
                    file_path,
                    caption=f"👤 {user_label} so'radi:\n{caption[:900]}"
                )

            try:
                os.remove(file_path)
            except:
                pass

        else:
            await event.reply(caption or "❌ Post bo'sh.")

            # Matnli post bo'lsa ham ownerga xabar ber
            if not is_owner:
                user_info = await bot.get_entity(sender_id)
                username = getattr(user_info, 'username', None)
                first_name = getattr(user_info, 'first_name', '') or ''

                if username:
                    user_label = f"@{username} (ID: {sender_id})"
                else:
                    user_label = f"{first_name} (ID: {sender_id})"

                await bot.send_message(
                    OWNER_ID,
                    f"👤 {user_label} so'radi (matn post):\n{caption[:1000]}"
                )

    except Exception as e:
        await event.reply(f"❌ Xato:\n{str(e)}")

async def start_bot():
    print("User login...")
    await user.start()
    print("Bot login...")
    await bot.start(bot_token=bot_token)
    print("✅ Bot ishlayapti...")
    await bot.run_until_disconnected()

def run_bot_loop():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot())

if __name__ == '__main__':
    t = threading.Thread(target=run_bot_loop, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
