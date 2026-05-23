import os
import re
import glob
import shutil
import asyncio
import logging

from flask import Flask
from threading import Thread

from telethon import TelegramClient, events, Button
from telethon.tl.functions.stories import GetStoriesByIDRequest
from dotenv import load_dotenv

import yt_dlp

load_dotenv()
logging.basicConfig(level=logging.INFO)

# =====================================
# CONFIG
# =====================================

api_id   = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =====================================
# FLASK  (alohida thread)
# =====================================

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot ishlayapti!"

def run_flask():
    flask_app.run(host="0.0.0.0", port=10000)

Thread(target=run_flask, daemon=True).start()

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


def download_with_ytdlp(url):
    clean_downloads()
    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title).50s.%(ext)s"),
        "format": "bestvideo[ext=mp4][filesize<45M]+bestaudio[ext=m4a]/best[filesize<45M]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return info

# =====================================
# TELEGRAM CLIENTS
# =====================================

# user client — story va private postlar uchun
user_client = TelegramClient("user_session", api_id, api_hash)

# bot client — foydalanuvchi bilan muloqot uchun
bot_client  = TelegramClient("bot_session", api_id, api_hash)

# =====================================
# /start
# =====================================

@bot_client.on(events.NewMessage(pattern="^/start$"))
async def start(event):
    buttons = [
        [Button.text("▶️ YouTube"),    Button.text("📸 Instagram")],
        [Button.text("📥 Telegram"),   Button.text("🎵 TikTok")],
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

@bot_client.on(events.NewMessage)
async def handler(event):
    text = event.raw_text.strip()

    # ---------- BUTTON REPLIES ----------

    if text == "▶️ YouTube":
        await event.reply("YouTube video yoki Shorts linkini yuboring")
        return
    if text == "📸 Instagram":
        await event.reply("Instagram post, reel yoki story linkini yuboring")
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
            "▶️ youtu.be/...\n\n"
            "📸 instagram.com/p/...\n"
            "📸 instagram.com/reel/...\n"
            "📸 instagram.com/stories/username/\n\n"
            "🎵 tiktok.com/@.../video/...\n\n"
            "📥 t.me/username/123  — post\n"
            "📥 t.me/username/s/123 — story\n"
            "📥 @username — oxirgi post"
            "👨‍💻 developer - t.me/umaarjonov, t.me/farrukhbec"
        )
        return

    # ---------- FILTER ----------

    if "http" not in text and not text.startswith("@"):
        return

    # ====================================================
    # TELEGRAM @USERNAME  →  oxirgi media post
    # ====================================================

    if text.startswith("@"):
        username = text.lstrip("@").strip()
        msg = await event.reply(f"⏳ @{username} dan yuklanmoqda...")

        try:
            entity = await user_client.get_entity(username)
        except Exception as e:
            await msg.edit(f"❌ Username topilmadi:\n{e}")
            return

        try:
            messages = await user_client.get_messages(entity, limit=10)
        except Exception as e:
            await msg.edit(f"❌ Xabarlar olinmadi:\n{e}")
            return

        post = next((m for m in messages if m and m.media), None)

        if not post:
            await msg.edit("❌ Oxirgi postlarda media topilmadi.")
            return

        try:
            file_path = await user_client.download_media(post, file=DOWNLOAD_DIR)
            caption = (post.text or "")[:1000]
            await bot_client.send_file(event.chat_id, file_path, caption=caption)
            await msg.delete()
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            await msg.edit(f"❌ Yuborishda xato:\n{e}")
        return

    # ====================================================
    # TELEGRAM STORY LINK  →  t.me/username/s/123
    # ====================================================

    if "t.me/" in text and "/s/" in text:
        msg = await event.reply("⏳ Telegram story yuklanmoqda...")
        username, story_id = parse_telegram_story(text)

        if not username:
            await msg.edit("❌ Story link noto'g'ri format.")
            return

        try:
            entity = await user_client.get_entity(username)
            result = await user_client(
                GetStoriesByIDRequest(peer=entity, id=[story_id])
            )

            if not result.stories:
                await msg.edit("❌ Story topilmadi yoki muddati o'tgan.")
                return

            story = result.stories[0]
            file_path = await user_client.download_media(story.media, file=DOWNLOAD_DIR)

            if not file_path:
                await msg.edit("❌ Story media yuklanmadi.")
                return

            await bot_client.send_file(event.chat_id, file_path, caption="📖 Telegram Story")
            await msg.delete()
            os.remove(file_path)

        except Exception as e:
            await msg.edit(f"❌ Story yuklab bo'lmadi:\n{e}")
        return

    # ====================================================
    # TELEGRAM POST LINK  →  t.me/username/123
    # ====================================================

    if "t.me/" in text:
        msg = await event.reply("⏳ Telegram post yuklanmoqda...")
        channel, post_id = parse_telegram_post(text)

        if not channel:
            await msg.edit("❌ Link noto'g'ri.")
            return

        try:
            entity = await user_client.get_entity(channel)
            post = await user_client.get_messages(entity, ids=post_id)

            if not post:
                await msg.edit("❌ Post topilmadi yoki kanalga a'zo emassiz.")
                return

            caption = (post.text or "")[:1000]

            if post.media:
                file_path = await user_client.download_media(post, file=DOWNLOAD_DIR)
                await bot_client.send_file(event.chat_id, file_path, caption=caption)
                await msg.delete()
                os.remove(file_path)
            else:
                await msg.edit(caption or "❌ Bu postda media yo'q.")

        except Exception as e:
            await msg.edit(f"❌ Post yuklab bo'lmadi:\n{e}")
        return

    # ====================================================
    # YOUTUBE / INSTAGRAM / TIKTOK  →  yt-dlp
    # ====================================================

    is_yt  = any(x in text for x in ["youtube.com", "youtu.be"])
    is_ig  = "instagram.com" in text
    is_tt  = "tiktok.com" in text

    if is_yt or is_ig or is_tt:
        label = "▶️ YouTube" if is_yt else ("📸 Instagram" if is_ig else "🎵 TikTok")
        msg = await event.reply(f"⏳ {label} yuklanmoqda...")

        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: download_with_ytdlp(text)
            )

            files = get_all_media_files()
            if not files:
                await msg.edit("❌ Yuklab bo'lmadi. Link ochiq (public) ekanligini tekshiring.")
                return

            title = (info.get("title", "") or "")[:200]
            caption = f"🎬 {title}" if title else label

            for i, f in enumerate(files):
                try:
                    await bot_client.send_file(
                        event.chat_id, f,
                        caption=caption if i == 0 else ""
                    )
                except Exception:
                    await event.reply("❌ Fayl 50MB dan katta, yuklab bo'lmaydi.")

            await msg.delete()

        except yt_dlp.utils.DownloadError as e:
            err = str(e).lower()
            if "private" in err:
                await msg.edit("❌ Bu post private. Faqat public kontentni yuklab olish mumkin.")
            elif "unavailable" in err or "removed" in err:
                await msg.edit("❌ Video mavjud emas yoki o'chirilgan.")
            elif "login" in err or "sign in" in err:
                await msg.edit("❌ Bu kontent login talab qiladi (private akkaunt).")
            else:
                await msg.edit(f"❌ Yuklab bo'lmadi:\n{str(e)[:300]}")
        except Exception as e:
            await msg.edit(f"❌ Xato:\n{str(e)[:300]}")
        return

    await event.reply("❌ Link tushunilmadi. /start bosing.")

# ====================================================
# MAIN  —  bir loop da ikki client
# ====================================================

async def main():
    # user_client telefon sessiyasi bilan ishga tushadi
    await user_client.start()
    print("✅ User client ulandi")

    # bot_client token bilan ishga tushadi
    await bot_client.start(bot_token=bot_token)
    print("✅ Bot client ulandi")

    print("🚀 Bot ishlayapti...")

    # Ikkalasi bir vaqtda ishlaydi
    await asyncio.gather(
        user_client.run_until_disconnected(),
        bot_client.run_until_disconnected()
    )


asyncio.run(main())
