import os
import asyncio
from threading import Thread
from flask import Flask
import telebot
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import instaloader
from pytube import YouTube
from dotenv import load_dotenv

# -------------------- ENV --------------------
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

# -------------------- Flask va Bot --------------------
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
client = TelegramClient('session_name', API_ID, API_HASH)
L = instaloader.Instaloader()

# -------------------- Helper functions --------------------
# YouTube yuklash
def download_youtube(url):
    try:
        yt = YouTube(url)
        stream = yt.streams.get_highest_resolution()
        os.makedirs('downloads', exist_ok=True)
        filename = stream.download('downloads')
        return filename
    except Exception as e:
        return f"Xatolik YouTube: {str(e)}"

# Instagram yuklash
def download_instagram_post(url):
    try:
        os.makedirs('downloads', exist_ok=True)
        shortcode = url.split("/")[-2]
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target='downloads')
        return 'Instagram post yuklandi!'
    except Exception as e:
        return f"Xatolik Instagram: {str(e)}"

# Telegram postlarni olish
async def get_telegram_post(channel_username, limit=1):
    try:
        await client.start()
        channel = await client.get_entity(channel_username)
        posts = await client(GetHistoryRequest(
            peer=channel,
            limit=limit,
            offset_date=None,
            offset_id=0,
            max_id=0,
            min_id=0,
            add_offset=0,
            hash=0
        ))
        result = []
        for msg in posts.messages:
            if msg.media:
                result.append(msg)
        return result
    except Exception as e:
        return f"Xatolik Telegram: {str(e)}"

# Telegram postlarni yuklash va yuborish
async def handle_telegram_download(message, url):
    username = url.split('/')[-1]
    posts = await get_telegram_post(username)
    if isinstance(posts, str):
        bot.reply_to(message, posts)
    elif len(posts) == 0:
        bot.reply_to(message, "Post topilmadi yoki media yo‘q.")
    else:
        bot.reply_to(message, "Post topildi! Lekin media yuborish hali qo‘shimcha qilinadi.") 

# -------------------- Bot handler --------------------
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Salom! Link yuboring, men uni yuklab beraman 🎬📸")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    if "youtube.com" in url or "youtu.be" in url:
        bot.reply_to(message, "YouTube videoni yuklab olaman...")
        filename = download_youtube(url)
        if os.path.exists(filename):
            bot.send_video(message.chat.id, open(filename, 'rb'))
        else:
            bot.reply_to(message, filename)
    elif "instagram.com" in url:
        bot.reply_to(message, "Instagram postini yuklab olaman...")
        result = download_instagram_post(url)
        bot.reply_to(message, result)
    elif "t.me/" in url:
        bot.reply_to(message, "Telegram postini yuklab olaman...")
        asyncio.run(handle_telegram_download(message, url))
    else:
        bot.reply_to(message, "Faqat YouTube, Instagram yoki Telegram linklarini yuboring!")

# -------------------- Flask route --------------------
@app.route('/')
def index():
    return "Bot server ishlayapti!"

# -------------------- Botni Threadda ishga tushirish --------------------
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=5000)    
    if status in ("redirect", "tunnel"):
        video_url = data.get("url")
        if not video_url:
            raise Exception("Video URL topilmadi")

        video_resp = requests.get(video_url, stream=True, timeout=60)
        file_path  = os.path.join(DOWNLOAD_DIR, "video.mp4")

        with open(file_path, "wb") as f:
            for chunk in video_resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

def download_video():
    file_path = "downloads/video.mp4"
    data = {"filename": "video.mp4"}

    return file_path, data.get("filename", "video.mp4")

    # Picker (ko'p media)
    if status == "picker":
        items = data.get("picker", [])
        if not items:
            raise Exception("Media topilmadi")

        file_path = os.path.join(DOWNLOAD_DIR, "video.mp4")
        video_resp = requests.get(items[0]["url"], stream=True, timeout=60)

        with open(file_path, "wb") as f:
            for chunk in video_resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        return file_path, "video.mp4"

    raise Exception(f"Noma'lum status: {status}")


def download_instagram(url):
    """cobalt.tools orqali Instagram yuklab olish"""
    return download_youtube(url)  # bir xil API


def download_tiktok(url):
    """cobalt.tools orqali TikTok yuklab olish"""
    return download_youtube(url)  # bir xil API


# =====================================
# CLIENTS
# =====================================

# MUHIM: user_client faqat yuklab olish uchun, event listen qilmaydi
user_client = TelegramClient("user_session", api_id, api_hash)

# bot_client barcha eventlarni ushlaydi
bot_client  = TelegramClient("bot_session",  api_id, api_hash)

# =====================================
# /start
# =====================================

@bot_client.on(events.NewMessage(pattern="^/start$"))
async def start(event):
    buttons = [
        [Button.text("▶️ YouTube"),  Button.text("📸 Instagram")],
        [Button.text("📥 Telegram"), Button.text("🎵 TikTok")],
        [Button.text("ℹ️ Help")]
    ]
    await event.respond(
        "👋 Salom! Link yuboring, yuklab beraman.\n\n"
        "✅ YouTube • Instagram • TikTok • Telegram",
        buttons=buttons
    )
    raise events.StopPropagation


# =====================================
# MAIN HANDLER  (faqat bot_client da)
# =====================================

@bot_client.on(events.NewMessage)
async def handler(event):
    text = event.raw_text.strip()

    # ---------- BUTTONS ----------
    if text == "▶️ YouTube":
        await event.reply("YouTube video yoki Shorts linkini yuboring")
        return
    if text == "📸 Instagram":
        await event.reply("Instagram post yoki reel linkini yuboring")
        return
    if text == "📥 Telegram":
        await event.reply(
            "Telegram post linki yoki @username yuboring\n\n"
            "Story uchun: t.me/username/s/123"
        )
        return
    if text == "🎵 TikTok":
        await event.reply("TikTok video linkini yuboring")
        return
    if text == "ℹ️ Help":
        await event.reply(
            "📌 Qo'llab-quvvatlanadigan:\n\n"
            "▶️ youtube.com/watch?v=...\n"
            "▶️ youtu.be/...\n"
            "▶️ youtube.com/shorts/...\n\n"
            "📸 instagram.com/p/...\n"
            "📸 instagram.com/reel/...\n\n"
            "🎵 tiktok.com/@.../video/...\n\n"
            "📥 t.me/username/123   — post\n"
            "📥 t.me/username/s/123 — story\n"
            "📥 @username           — oxirgi post"
        )
        return

    # ---------- FILTER ----------
    if "http" not in text and not text.startswith("@"):
        return

    # ====================================================
    # @USERNAME → oxirgi media post
    # ====================================================
    if text.startswith("@"):
        username = text.lstrip("@").strip()
        msg = await event.reply(f"⏳ @{username} dan yuklanmoqda...")

        try:
            entity = await user_client.get_entity(username)
            messages = await user_client.get_messages(entity, limit=10)
        except Exception as e:
            await msg.edit(f"❌ Topilmadi:\n{e}")
            return

        post = next((m for m in messages if m and m.media), None)
        if not post:
            await msg.edit("❌ Oxirgi postlarda media topilmadi.")
            return

        try:
            file_path = await user_client.download_media(post, file=DOWNLOAD_DIR)
            caption   = (post.text or "")[:1000]
            await bot_client.send_file(event.chat_id, file_path, caption=caption)
            await msg.delete()
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            await msg.edit(f"❌ Yuborishda xato:\n{e}")
        return

    # ====================================================
    # TELEGRAM STORY → t.me/username/s/123
    # ====================================================
    if "t.me/" in text and "/s/" in text:
        msg = await event.reply("⏳ Telegram story yuklanmoqda...")
        username, story_id = parse_telegram_story(text)

        if not username:
            await msg.edit("❌ Story link noto'g'ri.")
            return

        try:
            entity = await user_client.get_entity(username)

            # MUHIM: user_client orqali (bot emas!)
            result = await user_client(
                GetStoriesByIDRequest(peer=entity, id=[story_id])
            )

            if not result.stories:
                await msg.edit("❌ Story topilmadi yoki muddati o'tgan.")
                return

            story     = result.stories[0]
            file_path = await user_client.download_media(story.media, file=DOWNLOAD_DIR)

            if not file_path:
                await msg.edit("❌ Story media yuklanmadi.")
                return

            await bot_client.send_file(event.chat_id, file_path, caption="📖 Telegram Story")
            await msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception as e:
            await msg.edit(f"❌ Story yuklab bo'lmadi:\n{e}")
        return

    # ====================================================
    # TELEGRAM POST → t.me/username/123
    # ====================================================
    if "t.me/" in text:
        msg = await event.reply("⏳ Telegram post yuklanmoqda...")
        channel, post_id = parse_telegram_post(text)

        if not channel:
            await msg.edit("❌ Link noto'g'ri.")
            return

        try:
            entity = await user_client.get_entity(channel)
            post   = await user_client.get_messages(entity, ids=post_id)

            if not post:
                await msg.edit("❌ Post topilmadi yoki kanalga a'zo emassiz.")
                return

            caption = (post.text or "")[:1000]

            if post.media:
                file_path = await user_client.download_media(post, file=DOWNLOAD_DIR)
                await bot_client.send_file(event.chat_id, file_path, caption=caption)
                await msg.delete()
                if os.path.exists(file_path):
                    os.remove(file_path)
            else:
                await msg.edit(caption or "❌ Bu postda media yo'q.")

        except Exception as e:
            await msg.edit(f"❌ Post yuklab bo'lmadi:\n{e}")
        return

    # ====================================================
    # YOUTUBE
    # ====================================================
    if any(x in text for x in ["youtube.com", "youtu.be"]):
        msg = await event.reply("⏳ YouTube yuklanmoqda...")
        try:
            loop = asyncio.get_event_loop()
            file_path, filename = await loop.run_in_executor(
                None, lambda: download_youtube(text)
            )
            await bot_client.send_file(event.chat_id, file_path, caption="▶️ YouTube")
            await msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            await msg.edit(f"❌ YouTube yuklab bo'lmadi:\n{e}")
        return

    # ====================================================
    # INSTAGRAM
    # ====================================================
    if "instagram.com" in text:
        msg = await event.reply("⏳ Instagram yuklanmoqda...")
        try:
            loop = asyncio.get_event_loop()
            file_path, filename = await loop.run_in_executor(
                None, lambda: download_instagram(text)
            )
            await bot_client.send_file(event.chat_id, file_path, caption="📸 Instagram")
            await msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            await msg.edit(f"❌ Instagram yuklab bo'lmadi:\n{e}")
        return

    # ====================================================
    # TIKTOK
    # ====================================================
    if "tiktok.com" in text:
        msg = await event.reply("⏳ TikTok yuklanmoqda...")
        try:
            loop = asyncio.get_event_loop()
            file_path, filename = await loop.run_in_executor(
                None, lambda: download_tiktok(text)
            )
            await bot_client.send_file(event.chat_id, file_path, caption="🎵 TikTok")
            await msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            await msg.edit(f"❌ TikTok yuklab bo'lmadi:\n{e}")
        return

    await event.reply("❌ Link tushunilmadi. /start bosing.")


# =====================================
# MAIN
# =====================================

async def main():
    # user_client — faqat yuklab olish, event yo'q
    await user_client.start()
    print("✅ User client ulandi")

    # bot_client — barcha eventlar
    await bot_client.start(bot_token=bot_token)
    print("✅ Bot client ulandi")

    print("🚀 Bot ishlayapti...")

    await asyncio.gather(
        user_client.run_until_disconnected(),
        bot_client.run_until_disconnected()
    )


asyncio.run(main())
