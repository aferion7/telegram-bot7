import os
import re
from telethon import TelegramClient, events
from dotenv import load_dotenv
from telethon.tl.types import PeerChannel

load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

user = TelegramClient("user_session", api_id, api_hash)
bot = TelegramClient("bot_session", api_id, api_hash)


def parse_link(link):
    link = link.split("?")[0].strip()

    # private kanal
    m = re.search(r"t\.me/c/(\d+)/(\d+)", link)
    if m:
        channel_id = int("-100" + m.group(1))
        post_id = int(m.group(2))
        return channel_id, post_id

    # public kanal
    m = re.search(r"t\.me/([A-Za-z0-9_]+)/(\d+)", link)
    if m:
        channel = m.group(1)
        post_id = int(m.group(2))
        return channel, post_id

    return None, None


async def find_private_channel(channel_id):
    async for dialog in user.iter_dialogs():
        if dialog.id == abs(channel_id):
            return dialog.entity
    return None


@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "Link yubor.\n\n"
        "Misol:\n"
        "https://t.me/c/1234567890/45"
    )


@bot.on(events.NewMessage)
async def handler(event):
    text = event.raw_text.strip()

    if "t.me/" not in text or text.startswith("/"):
        return

    await event.reply("⏳ Yuklayapman...")

    channel, post_id = parse_link(text)

    if not channel:
        await event.reply("❌ Link noto'g'ri.")
        return

    try:

        # PUBLIC kanal
        if isinstance(channel, str):
            entity = await user.get_entity(channel)

        # PRIVATE kanal
      else:
            from telethon.tl.types import PeerChannel

               peer = PeerChannel(
                 int(str(channel).replace("-100", "")))

                 post = await user.get_messages(
                   peer,
                   ids=post_id)

    if not post:
        await event.reply("❌ Post topilmadi.")
        return

        if not post:
            await event.reply("❌ Post topilmadi.")
            return

        caption = post.text or ""

        # media bo'lsa
        if post.media:

            await event.reply("📥 Media yuklanmoqda...")

            file_path = await user.download_media(
                post,
                file=DOWNLOAD_DIR
            )

            if not file_path:
                await event.reply("❌ Yuklab bo'lmadi.")
                return

            await bot.send_file(
                event.chat_id,
                file_path,
                caption=caption[:1000]
            )

            try:
                os.remove(file_path)
            except:
                pass

        else:
            await event.reply(caption or "❌ Post bo'sh.")

    except Exception as e:
        await event.reply(f"❌ Xato:\n{str(e)}")


async def main():
    await user.start()
    await bot.start(bot_token=bot_token)

    print("Bot ishlayapti...")

    await bot.run_until_disconnected()


with user:
    user.loop.run_until_complete(main())
