import os
import re
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from dotenv import load_dotenv

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
    m = re.search(r"t\.me/c/(\d+)/(\d+)", link)
    if m:
        channel_id = int("-100" + m.group(1))
        post_id = int(m.group(2))
        return channel_id, post_id
    m = re.search(r"t\.me/([A-Za-z0-9_]+)/(\d+)", link)
    if m:
        channel = m.group(1)
        post_id = int(m.group(2))
        return channel, post_id
    return None, None


@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "Post link yubor. Masalan:\n"
        "https://t.me/c/1234567890/45\n\n"
        "Maxfiy kanal uchun avval /join buyrug'ini ishlating:\n"
        "/join https://t.me/+invitelink"
    )


# ✅ YANGI: Kanalga qo'shilish buyrug'i
@bot.on(events.NewMessage(pattern=r"/join (.+)"))
async def join_channel(event):
    invite_link = event.pattern_match.group(1).strip()
    try:
        await event.reply("⏳ Kanalga qo'shilmoqdaman...")
        await user(JoinChannelRequest(invite_link))
        await event.reply("✅ Kanalga muvaffaqiyatli qo'shildim!")
    except Exception as e:
        await event.reply(f"❌ Qo'shila olmadim:\n{e}")


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
        # ✅ Avval entity olishga harakat
        try:
            entity = await user.get_entity(channel)
        except Exception as e:
            await event.reply(
                f"❌ Kanal topilmadi: {e}\n\n"
                f"Agar maxfiy kanal bo'lsa, avval qo'shiling:\n"
                f"/join https://t.me/+invitelink"
            )
            return

        post = await user.get_messages(entity, ids=post_id)

        if not post:
            await event.reply("❌ Post topilmadi.")
            return

        caption = post.text or ""

        if post.media:
            await event.reply("📥 Media yuklanmoqda...")
            file_path = await user.download_media(post, file=DOWNLOAD_DIR)

            if file_path:
                await bot.send_file(
                    event.chat_id,
                    file_path,
                    caption=caption[:1000]
                )
                # ✅ Faylni o'chirib yuborish (joy tejash)
                os.remove(file_path)
            else:
                await event.reply("❌ Media yuklab bo'lmadi.")
        else:
            await event.reply(caption or "❌ Post bo'sh.")

    except Exception as e:
        await event.reply(f"❌ Xato:\n{e}")


async def main():
    await user.start()
    await bot.start(bot_token=bot_token)
    print("Bot ishlayapti...")
    await bot.run_until_disconnected()


with user:
    user.loop.run_until_complete(main())
