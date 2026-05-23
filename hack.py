import os
import re
import glob
import shutil
import instaloader

from flask import Flask
from threading import Thread

from telethon import TelegramClient, events, Button
from telethon.tl.functions.stories import GetStoriesByIDRequest
from telethon.tl.types import InputPeerUser, InputPeerChannel
from dotenv import load_dotenv

load_dotenv()

# =====================================
# CONFIG
# =====================================

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =====================================
# CLIENTS
# =====================================

user = TelegramClient("user_session", api_id, api_hash)
bot = TelegramClient("bot_session", api_id, api_hash)

# =====================================
# INSTAGRAM
# =====================================

L = instaloader.Instaloader(
    dirname_pattern=DOWNLOAD_DIR,
    download_videos=True,
    download_video_thumbnails=False,
    save_metadata=False,
    compress_json=False,
    quiet=True
)

ig_logged_in = False

if IG_USERNAME and IG_PASSWORD:
    try:
        # Avval session faylidan login qilishga urinish
        session_file = f"{IG_USERNAME}.session"
        if os.path.exists(session_file):
            L.load_session_from_file(IG_USERNAME, session_file)
            ig_logged_in = True
            print("Instagram session loaded")
        else:
            L.login(IG_USERNAME, IG_PASSWORD)
            L.save_session_to_file(session_file)
            ig_logged_in = True
            print("Instagram login success")
    except Exception as e:
        print("Instagram login error:", e)

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
    """Barcha media fayllarni qaytaradi"""
    files = glob.glob(f"{DOWNLOAD_DIR}/**/*", recursive=True)
    files = [
        f for f in files
        if os.path.isfile(f)
        and not f.endswith(".json")
        and not f.endswith(".txt")
        and not f.endswith(".xz")
    ]
    return sorted(files, key=os.path.getctime)


def get_latest_file():
    files = get_all_media_files()
    return files[-1] if files else None


def parse_telegram_post(link):
    link = link.split("?")[0].strip()

    # private: t.me/c/123456/789
    m = re.search(r"t\.me/c/(\d+)/(\d+)", link)
    if m:
        channel_id = int("-100" + m.group(1))
        post_id = int(m.group(2))
        return channel_id, post_id

    # public: t.me/username/789
    m = re.search(r"t\.me/([A-Za-z0-9_]+)/(\d+)", link)
    if m:
        channel = m.group(1)
        post_id = int(m.group(2))
        return channel, post_id

    return None, None


def parse_telegram_story(link):
    # t.me/username/s/123
    m = re.search(r"t\.me/([A-Za-z0-9_]+)/s/(\d+)", link)
    if m:
        return m.group(1), int(m.group(2))
    return None, None

# =====================================
# START
# =====================================

@bot.on(events.NewMessage(pattern="^/start$"))
async def start(event):
    buttons = [
        [Button.text("📥 Telegram Post")],
        [Button.text("📸 Instagram")],
        [Button.text("ℹ️ Help")]
    ]
    await event.respond("Kerakli bo'limni tanlang:", buttons=buttons)
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

    if text == "📥 Telegram Post":
        await event.reply("Telegram post link yoki @username yuboring")
        return

    elif text == "📸 Instagram":
        await event.reply("Instagram reel/post/story link yuboring")
        return

    elif text == "ℹ️ Help":
        await event.reply(
            "📌 Bot imkoniyatlari:\n\n"
            "• @username → oxirgi postni yuklaydi\n"
            "• t.me/username/123 → telegram post\n"
            "• t.me/username/s/123 → telegram story\n"
            "• instagram.com/p/... → instagram post\n"
            "• instagram.com/reel/... → instagram reel\n"
            "• instagram.com/stories/... → instagram story"
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
        await event.reply(f"⏳ @{username} dan yuklanmoqda...")

        try:
            entity = await user.get_entity(username)
        except Exception as e:
            await event.reply(f"❌ Username topilmadi: {e}")
            return

        try:
            messages = await user.get_messages(entity, limit=5)
        except Exception as e:
            await event.reply(f"❌ Xabarlarni olib bo'lmadi: {e}")
            return

        # Media topish
        post = None
        for msg in messages:
            if msg and msg.media:
                post = msg
                break

        if not post:
            # Media yo'q bo'lsa oxirgi xabarni yubor
            if messages and messages[0]:
                await event.reply(messages[0].text or "❌ Media topilmadi.")
            else:
                await event.reply("❌ Hech narsa topilmadi.")
            return

        try:
            file_path = await user.download_media(post, file=DOWNLOAD_DIR)
            caption = (post.text or "")[:1000]
            await bot.send_file(event.chat_id, file_path, caption=caption)
            os.remove(file_path)
        except Exception as e:
            await event.reply(f"❌ Yuborishda xato: {e}")

        return

    await event.reply("⏳ Yuklayapman...")

    try:

        # =====================================
        # TELEGRAM STORY LINK
        # =====================================

        if "t.me/" in text and "/s/" in text:
            username, story_id = parse_telegram_story(text)

            if not username:
                await event.reply("❌ Story link noto'g'ri.")
                return

            try:
                entity = await user.get_entity(username)

                result = await user(
                    GetStoriesByIDRequest(
                        peer=entity,
                        id=[story_id]
                    )
                )

                if not result.stories:
                    await event.reply("❌ Story topilmadi yoki muddati o'tgan.")
                    return

                story = result.stories[0]
                file_path = await user.download_media(story.media, file=DOWNLOAD_DIR)

                if not file_path:
                    await event.reply("❌ Story media yuklanmadi.")
                    return

                await bot.send_file(event.chat_id, file_path, caption="📖 Telegram Story")
                os.remove(file_path)

            except Exception as e:
                await event.reply(f"❌ Story yuklab bo'lmadi:\n{e}")

            return

        # =====================================
        # TELEGRAM POST LINK
        # =====================================

        elif "t.me/" in text:
            channel, post_id = parse_telegram_post(text)

            if not channel:
                await event.reply("❌ Link noto'g'ri.")
                return

            try:
                entity = await user.get_entity(channel)
                post = await user.get_messages(entity, ids=post_id)

                if not post:
                    await event.reply("❌ Post topilmadi yoki kanalga a'zo emassiz.")
                    return

                caption = (post.text or "")[:1000]

                if post.media:
                    file_path = await user.download_media(post, file=DOWNLOAD_DIR)
                    await bot.send_file(event.chat_id, file_path, caption=caption)
                    os.remove(file_path)
                else:
                    await event.reply(caption or "❌ Bu postda media yo'q.")

            except Exception as e:
                await event.reply(f"❌ Post yuklab bo'lmadi:\n{e}")

            return

        # =====================================
        # INSTAGRAM
        # =====================================

        elif "instagram.com" in text:

            if not ig_logged_in:
                await event.reply("❌ Instagram login sozlanmagan.")
                return

            clean_downloads()

            # --- INSTAGRAM STORY ---
            if "/stories/" in text:
                m = re.search(r"instagram\.com/stories/([^/?]+)", text)

                if not m:
                    await event.reply("❌ Story link noto'g'ri.")
                    return

                ig_user = m.group(1)

                try:
                    profile = instaloader.Profile.from_username(L.context, ig_user)

                    if profile.is_private:
                        await event.reply("❌ Bu akkaunt private, story yuklab bo'lmaydi.")
                        return

                    found = False
                    for story in L.get_stories(userids=[profile.userid]):
                        for item in story.get_items():
                            L.download_storyitem(item, target=DOWNLOAD_DIR)
                            found = True

                    if not found:
                        await event.reply("❌ Hozirda active story yo'q.")
                        return

                    media_files = get_all_media_files()

                    if not media_files:
                        await event.reply("❌ Yuklab bo'lmadi.")
                        return

                    for f in media_files:
                        await bot.send_file(event.chat_id, f, caption="📸 Instagram Story")

                except Exception as e:
                    await event.reply(f"❌ Instagram story xatosi:\n{e}")

                return

            # --- INSTAGRAM REEL / POST ---
            shortcode = None

            m = re.search(r"/reel/([^/?]+)", text)
            if m:
                shortcode = m.group(1)

            if not shortcode:
                m = re.search(r"/p/([^/?]+)", text)
                if m:
                    shortcode = m.group(1)

            if shortcode:
                try:
                    post = instaloader.Post.from_shortcode(L.context, shortcode)
                    L.download_post(post, target=DOWNLOAD_DIR)

                    media_files = get_all_media_files()

                    if not media_files:
                        await event.reply("❌ Media topilmadi.")
                        return

                    caption = (post.caption or "")[:1000]

                    # Ko'p media bo'lsa hammasini yuborish
                    for i, f in enumerate(media_files):
                        cap = caption if i == 0 else ""
                        await bot.send_file(event.chat_id, f, caption=cap)

                except Exception as e:
                    await event.reply(f"❌ Instagram xatosi:\n{e}")

                return

            await event.reply("❌ Instagram link tushunilmadi.")
            return

        else:
            await event.reply("❌ Qo'llab-quvvatlanmaydi.")

    except Exception as e:
        await event.reply(f"❌ Umumiy xato:\n{e}")

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
