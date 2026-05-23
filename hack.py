import os
import re
import glob
import shutil
import instaloader
from flask import Flask
from threading import Thread

from telethon import TelegramClient, events, Button
from telethon.tl.functions.stories import GetStoriesByIDRequest
from dotenv import load_dotenv

load_dotenv()

# =====================================
# CONFIG
# =====================================

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

# Instagram login (optional)
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")

DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =====================================
# CLIENTS
# =====================================

user = TelegramClient(
    "user_session",
    api_id,
    api_hash
)

bot = TelegramClient(
    "bot_session",
    api_id,
    api_hash
)

# =====================================
# INSTAGRAM
# =====================================

L = instaloader.Instaloader(
    dirname_pattern=DOWNLOAD_DIR,
    download_videos=True,
    download_video_thumbnails=False,
    save_metadata=False,
    compress_json=False
)

if IG_USERNAME and IG_PASSWORD:
    try:
        L.login(IG_USERNAME, IG_PASSWORD)
        print("Instagram login success")
    except Exception as e:
        print("Instagram login error:", e)

# =====================================
# HELPERS
# =====================================

def clean_downloads():

    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def get_latest_file():

    files = glob.glob(
        f"{DOWNLOAD_DIR}/**/*",
        recursive=True
    )

    files = [
        f for f in files
        if os.path.isfile(f)
        and not f.endswith(".json")
        and not f.endswith(".txt")
    ]

    if not files:
        return None

    return max(files, key=os.path.getctime)


def parse_telegram_post(link):

    link = link.split("?")[0].strip()

    # private link
    m = re.search(
        r"t\.me/c/(\d+)/(\d+)",
        link
    )

    if m:
        channel_id = int("-100" + m.group(1))
        post_id = int(m.group(2))
        return channel_id, post_id

    # public link
    m = re.search(
        r"t\.me/([A-Za-z0-9_]+)/(\d+)",
        link
    )

    if m:
        channel = m.group(1)
        post_id = int(m.group(2))
        return channel, post_id

    return None, None


def parse_telegram_story(link):

    # https://t.me/username/s/12

    m = re.search(
        r"t\.me/([A-Za-z0-9_]+)/s/(\d+)",
        link
    )

    if m:
        username = m.group(1)
        story_id = int(m.group(2))

        return username, story_id

    return None, None


# =====================================
# START
# =====================================

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):

    buttons = [
        [Button.text("📥 Telegram Post")],
        [Button.text("📸 Instagram")],
        [Button.text("ℹ️ Help")]
    ]

    await event.respond(
        "Kerakli bo‘limni tanlang:",
        buttons=buttons
    )
# =====================================
# FLASK
# =====================================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot ishlayapti!"


def run_web():
    app.run(
        host="0.0.0.0",
        port=10000
    )

# =====================================
# MAIN HANDLER
# =====================================

@bot.on(events.NewMessage)
async def handler(event):

    text = event.raw_text.strip()
    if text == "📥 Telegram Post":
      await event.reply(
        "Telegram post link yoki @username yuboring"
    )
    return

elif text == "📸 Instagram":
    await event.reply(
        "Instagram reel/post/story link yuboring"
    )
    return

elif text == "ℹ️ Help":
    await event.reply(
        "Bot:\n"
        "- Telegram post yuklaydi\n"
        "- Telegram story yuklaydi\n"
        "- Instagram reel/post/story yuklaydi"
    )
    return

    if (
        "http" not in text
        and not text.startswith("@")
    ):
        return

    await event.reply("⏳ Yuklayapman...")

    try:

        # =====================================
        # TELEGRAM USERNAME
        # =====================================

        if text.startswith("@"):

            username = text.replace("@", "").strip()

            entity = await user.get_entity(username)

            posts = await user.get_messages(
                entity,
                limit=1
            )

            if not posts:
                await event.reply("❌ Post topilmadi.")
                return

            post = posts[0]

            caption = post.text or ""

            if post.media:

                file_path = await user.download_media(
                    post,
                    file=DOWNLOAD_DIR
                )

                await bot.send_file(
                    event.chat_id,
                    file_path,
                    caption=caption[:1000]
                )

            else:
                await event.reply(caption)

            return

        # =====================================
        # TELEGRAM STORY
        # =====================================

        elif "t.me/" in text and "/s/" in text:

            username, story_id = parse_telegram_story(text)

            if not username:
                await event.reply(
                    "❌ Story link noto‘g‘ri."
                )
                return

            entity = await user.get_entity(username)

            result = await user(
                GetStoriesByIDRequest(
                    peer=entity,
                    id=[story_id]
                )
            )

            if not result.stories:
                await event.reply(
                    "❌ Story topilmadi."
                )
                return

            story = result.stories[0]

            file_path = await user.download_media(
                story.media,
                file=DOWNLOAD_DIR
            )

            await bot.send_file(
                event.chat_id,
                file_path,
                caption="Telegram Story"
            )

            return

        # =====================================
        # TELEGRAM POST LINK
        # =====================================

        elif "t.me/" in text:

            channel, post_id = parse_telegram_post(text)

            if not channel:
                await event.reply(
                    "❌ Link noto‘g‘ri."
                )
                return

            entity = await user.get_entity(channel)

            post = await user.get_messages(
                entity,
                ids=post_id
            )

            if not post:
                await event.reply(
                    "❌ Post topilmadi yoki kanalga a’zo emassiz."
                )
                return

            caption = post.text or ""

            if post.media:

                file_path = await user.download_media(
                    post,
                    file=DOWNLOAD_DIR
                )

                await bot.send_file(
                    event.chat_id,
                    file_path,
                    caption=caption[:1000]
                )

            else:
                await event.reply(caption)

            return

        # =====================================
        # INSTAGRAM
        # =====================================

        elif "instagram.com" in text:

            clean_downloads()

            shortcode = None

            # reel
            m = re.search(
                r"/reel/([^/?]+)",
                text
            )

            if m:
                shortcode = m.group(1)

            # post
            if not shortcode:

                m = re.search(
                    r"/p/([^/?]+)",
                    text
                )

                if m:
                    shortcode = m.group(1)

            # story
            if "/stories/" in text:

                m = re.search(
                    r"instagram\.com/stories/([^/]+)/(\d+)",
                    text
                )

                if not m:
                    await event.reply(
                        "❌ Story link noto‘g‘ri."
                    )
                    return

                username = m.group(1)

                profile = (
                    instaloader.Profile.from_username(
                        L.context,
                        username
                    )
                )

                found = False

                for story in L.get_stories(
                    userids=[profile.userid]
                ):

                    for item in story.get_items():

                        L.download_storyitem(
                            item,
                            target=DOWNLOAD_DIR
                        )

                        found = True

                if not found:
                    await event.reply(
                        "❌ Story topilmadi."
                    )
                    return

                file_path = get_latest_file()

                if not file_path:
                    await event.reply(
                        "❌ Yuklab bo‘lmadi."
                    )
                    return

                await bot.send_file(
                    event.chat_id,
                    file_path,
                    caption="Instagram Story"
                )

                return

            # reel/post
            if shortcode:

                post = instaloader.Post.from_shortcode(
                    L.context,
                    shortcode
                )

                L.download_post(
                    post,
                    target=DOWNLOAD_DIR
                )

                file_path = get_latest_file()

                if not file_path:
                    await event.reply(
                        "❌ Media topilmadi."
                    )
                    return

                caption = post.caption or ""

                await bot.send_file(
                    event.chat_id,
                    file_path,
                    caption=caption[:1000]
                )

                return

            await event.reply(
                "❌ Instagram link tushunilmadi."
            )

            return

        else:

            await event.reply(
                "❌ Qo‘llab-quvvatlanmaydi."
            )

    except Exception as e:

        await event.reply(
            f"❌ Xato:\n{e}"
        )


# =====================================
# MAIN
# =====================================

async def main():

    await user.start()

    await bot.start(
        bot_token=bot_token
    )

    print("Bot ishlayapti...")

    await bot.run_until_disconnected()


Thread(target=run_web).start()

with user:
    user.loop.run_until_complete(main())
