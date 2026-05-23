import os
import re
import glob
import shutil
import asyncio

from flask import Flask
from threading import Thread

from telethon import TelegramClient, events, Button
from telethon.tl.functions.stories import GetStoriesByIDRequest
from dotenv import load_dotenv

import yt_dlp

load_dotenv()

# =====================================
# CONFIG
# =====================================

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =====================================
# CLIENTS
# =====================================

user = TelegramClient("user_session", api_id, api_hash)
bot = TelegramClient("bot_session", api_id, api_hash)

# =====================================
# FLASK
# =====================================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot ishlayapti!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

# =====================================
# HELPERS
# =====================================

def clean_downloads():
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def get_all_media_files():
    files = glob.glob(f"{DOWNLOAD_DIR}/**/*", recursive=True)
    files = [
        f for f in files
        if os.path.isfile(f)
        and not f.endswith(".json")
        and not f.endswith(".txt")
        and not f.endswith(".part")
        and not f.endswith(".ytdl")
    ]
    return sorted(files, key=os.path.getctime)


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


def is_youtube(url):
    return any(x in url for x in [
        "youtube.com", "youtu.be", "youtube-nocookie.com"
    ])


def is_instagram(url):
    return "instagram.com" in url


def is_tiktok(url):
    return "tiktok.com" in url


def download_with_ytdlp(url, output_dir):
    """yt-dlp orqali video yuklab olish"""
    ydl_opts = {
        "outtmpl": os.path.join(output_dir, "%(title).50s.%(ext)s"),
        "format": "best[filesize<50M]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info


# =====================================
# START
# =====================================

@bot.on(events.NewMessage(pattern="^/start$"))
async def start(event):
    buttons = [
        [Button.text("▶️ YouTube"), Button.text("📸 Instagram")],
        [Button.text("📥 Telegram Post"), Button.text("🎵 TikTok")],
        [Button.text("ℹ️ Help")]
    ]
    await event.respond(
        "👋 Salom! Link yuboring, yuklab beraman.\n\n"
        "✅ YouTube • Instagram • TikTok • Telegram",
        buttons=buttons
    )
    raise events.StopPropagation


# =====================================
# MAIN HANDLER
# =====================================

@bot.on(events.NewMessage)
async def handler(event):
    text = event.raw_text.strip()

    # =========================
    # BUTTONS
    # =========================

    if text == "▶️ YouTube":
        await event.reply("YouTube video yoki shorts linkini yuboring")
        return

    elif text == "📸 Instagram":
        await event.reply("Instagram post, reel yoki story linkini yuboring")
        return

    elif text == "📥 Telegram Post":
        await event.reply("Telegram post linki yoki @username yuboring")
        return

    elif text == "🎵 TikTok":
        await event.reply("TikTok video linkini yuboring")
        return

    elif text == "ℹ️ Help":
        await event.reply(
            "📌 Qo'llab-quvvatlanadigan linklar:\n\n"
            "▶️ YouTube:\nyoutube.com/watch?v=...\nyoutu.be/...\n\n"
            "📸 Instagram:\ninstagram.com/p/...\ninstagram.com/reel/...\ninstagram.com/stories/...\n\n"
            "🎵 TikTok:\ntiktok.com/@.../video/...\n\n"
            "📥 Telegram:\nt.me/username/123\nt.me/username/s/123 (story)\n@username (oxirgi post)"
        )
        return

    # =========================
    # FILTER
    # =========================

    if "http" not in text and not text.startswith("@"):
        return

    # =========================
    # TELEGRAM @USERNAME
    # =========================

    if text.startswith("@"):
        username = text.lstrip("@").strip()
        msg = await event.reply(f"⏳ @{username} dan yuklanmoqda...")

        try:
            entity = await user.get_entity(username)
            messages = await user.get_messages(entity, limit=10)
        except Exception as e:
            await msg.edit(f"❌ Topilmadi: {e}")
            return

        post = None
        for m in messages:
            if m and m.media:
                post = m
                break

        if not post:
            await msg.edit("❌ Media topilmadi.")
            return

        try:
            file_path = await user.download_media(post, file=DOWNLOAD_DIR)
            caption = (post.text or "")[:1000]
            await bot.send_file(event.chat_id, file_path, caption=caption)
            await msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            await msg.edit(f"❌ Yuborishda xato: {e}")
        return

    # =========================
    # TELEGRAM STORY LINK
    # =========================

    if "t.me/" in text and "/s/" in text:
        msg = await event.reply("⏳ Telegram story yuklanmoqda...")
        username, story_id = parse_telegram_story(text)

        if not username:
            await msg.edit("❌ Story link noto'g'ri.")
            return

        try:
            entity = await user.get_entity(username)
            result = await user(GetStoriesByIDRequest(peer=entity, id=[story_id]))

            if not result.stories:
                await msg.edit("❌ Story topilmadi yoki muddati o'tgan.")
                return

            story = result.stories[0]
            file_path = await user.download_media(story.media, file=DOWNLOAD_DIR)

            if not file_path:
                await msg.edit("❌ Story media yuklanmadi.")
                return

            await bot.send_file(event.chat_id, file_path, caption="📖 Telegram Story")
            await msg.delete()
            os.remove(file_path)

        except Exception as e:
            await msg.edit(f"❌ Story yuklab bo'lmadi:\n{e}")
        return

    # =========================
    # TELEGRAM POST LINK
    # =========================

    if "t.me/" in text and "/s/" not in text:
        msg = await event.reply("⏳ Telegram post yuklanmoqda...")
        channel, post_id = parse_telegram_post(text)

        if not channel:
            await msg.edit("❌ Link noto'g'ri.")
            return

        try:
            entity = await user.get_entity(channel)
            post = await user.get_messages(entity, ids=post_id)

            if not post:
                await msg.edit("❌ Post topilmadi.")
                return

            caption = (post.text or "")[:1000]

            if post.media:
                file_path = await user.download_media(post, file=DOWNLOAD_DIR)
                await bot.send_file(event.chat_id, file_path, caption=caption)
                await msg.delete()
                os.remove(file_path)
            else:
                await msg.edit(caption or "❌ Bu postda media yo'q.")

        except Exception as e:
            await msg.edit(f"❌ Post yuklab bo'lmadi:\n{e}")
        return

    # =========================
    # YOUTUBE / INSTAGRAM / TIKTOK
    # =========================

    if is_youtube(text) or is_instagram(text) or is_tiktok(text):
        clean_downloads()

        if is_youtube(text):
            platform = "▶️ YouTube"
        elif is_instagram(text):
            platform = "📸 Instagram"
        else:
            platform = "🎵 TikTok"

        msg = await event.reply(f"⏳ {platform} yuklanmoqda...")

        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: download_with_ytdlp(text, DOWNLOAD_DIR)
            )

            files = get_all_media_files()

            if not files:
                await msg.edit("❌ Yuklab bo'lmadi. Link ochiq ekanligini tekshiring.")
                return

            title = info.get("title", "") if info else ""
            caption = f"🎬 {title}"[:1000] if title else platform

            for i, f in enumerate(files):
                cap = caption if i == 0 else ""
                try:
                    await bot.send_file(event.chat_id, f, caption=cap)
                except Exception:
                    # Fayl katta bo'lsa
                    await event.reply("❌ Fayl hajmi juda katta (50MB dan oshadi).")

            await msg.delete()

        except yt_dlp.utils.DownloadError as e:
            err = str(e)
            if "Private" in err or "private" in err:
                await msg.edit("❌ Bu post private. Ochiq postlarni yuklab olish mumkin.")
            elif "unavailable" in err:
                await msg.edit("❌ Video mavjud emas yoki o'chirilgan.")
            else:
                await msg.edit(f"❌ Yuklab bo'lmadi:\n{err[:300]}")
        except Exception as e:
            await msg.edit(f"❌ Xato:\n{str(e)[:300]}")

        return

    await event.reply("❌ Link tushunilmadi. /start bosing.")


# =====================================
# MAIN
# =====================================

async def main():
    await user.start()
    await bot.start(bot_token=bot_token)
    print("Bot ishlayapti...")
    await bot.run_until_disconnected()


Thread(target=run_web).start()

with user:
    user.loop.run_until_complete(main())
