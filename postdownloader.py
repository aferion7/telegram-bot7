import os
import re
from telethon import TelegramClient, events
from dotenv import load_dotenv
load_dotenv()
from flask import Flask
import threading
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot ishlayapti"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()

api_id = int(os.getenv("API_ID"))          # o'zingni API ID
api_hash = os.getenv("API_HASH" )   # o'zingni API HASH
bot_token = os.getenv("BOT_TOKEN")  # BotFather bergan token

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

user = TelegramClient("user_session", api_id, api_hash)
bot = TelegramClient("bot_session", api_id, api_hash)


def parse_link(link):
    link = link.split("?")[0].strip()

    # private link: https://t.me/c/1234567890/45
    m = re.search(r"t\.me/c/(\d+)/(\d+)", link)
    if m:
        channel_id = int("-100" + m.group(1))
        post_id = int(m.group(2))
        return channel_id, post_id

    # public link: https://t.me/channelusername/45
    m = re.search(r"t\.me/([A-Za-z0-9_]+)/(\d+)", link)
    if m:
        channel = m.group(1)
        post_id = int(m.group(2))
        return channel, post_id

    return None, None


@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply("Hello there!✌️
    Post link yubor. Masalan:\nhttps://t.me/c/1234567890/45")


@bot.on(events.NewMessage)
async def handler(event):
    text = event.raw_text.strip()

    if "t.me/" not in text:
        return

    await event.reply("⏳ Yuklayapman...")

    channel, post_id = parse_link(text)

    if not channel:
        await event.reply("❌ Link noto‘g‘ri.")
        return

    try:
        entity = await user.get_entity(channel)
        post = await user.get_messages(entity, ids=post_id)

        if not post:
            await event.reply("❌ Post topilmadi. Kanalga a’zo ekaningni tekshir.")
            return

        caption = post.text or "Media"

        if post.media:
            file_path = await user.download_media(post, file=DOWNLOAD_DIR)
            await bot.send_file(
                event.chat_id,
                file_path,
                caption=caption[:1000]
            )
        else:
            await event.reply(caption)

    except Exception as e:
        await event.reply(f"❌ Xato:\n{e}")


async def main():
    await user.start()
    await bot.start(bot_token=bot_token)
    print("Bot ishlayapti...")
    await bot.run_until_disconnected()


with user:
    user.loop.run_until_complete(main())
