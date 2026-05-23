import os
import re
import glob
import shutil
import asyncio
import logging
import requests

from flask import Flask
from threading import Thread

from telethon import TelegramClient, events, Button
from telethon.tl.functions.stories import GetStoriesByIDRequest
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

# =====================================
# CONFIG
# =====================================

api_id    = int(os.getenv("API_ID"))
api_hash  = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =====================================
# FLASK
# =====================================

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot ishlayapti!"

Thread(target=lambda: flask_app.run(host="0.0.0.0", port=10000), daemon=True).start()

# =====================================
# HELPERS
# =====================================

def clean_downloads():
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def get_all_media_files():
    files = glob.glob(f"{DOWNLOAD_DIR}/**/*", recursive=True)
    return sorted(
        [f for f in files if os.path.isfile(f)
         and not f.endswith((".json", ".txt", ".part", ".ytdl", ".xz"))],
        key=os.path.getctime
    )


def parse_telegram_post(link):
    link = link.split("?")[0].strip()
    m = re.search(r"t\.me/c/(\d+)/(\d+)", link)
    if m:
        return int("-100" + m.group(1)), int(m.group(2))
    m = re.search(r"t\.me/([A-Za-z0-9_]+)/(\d+)", link)
    if m:
        return m.group(1), int(m.group(2))
    return None, None


def parse_telegram_story(link):
    m = re.search(r"t\.me/([A-Za-z0-9_]+)/s/(\d+)", link)
    if m:
        return m.group(1), int(m.group(2))
    return None, None


def download_youtube(url):
    """
    cobalt.tools API orqali YouTube yuklab olish
    Login talab qilmaydi, Shorts ham ishlaydi
    """
    clean_downloads()

    try:
        resp = requests.post(
            "https://api.cobalt.tools/",
            json={
                "url": url,
                "videoQuality": "720",
                "filenameStyle": "basic",
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30
        )
        data = resp.json()
    except Exception as e:
        raise Exception(f"API xatosi: {e}")

    status = data.get("status")

    if status == "error":
        raise Exception(data.get("error", {}).get("code", "Yuklab bo'lmadi"))

    # To'g'ridan to'g'ri URL
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
