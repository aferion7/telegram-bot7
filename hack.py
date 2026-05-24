import os
from threading import Thread
from flask import Flask
import telebot
from dotenv import load_dotenv
from pytube import YouTube
import instaloader

# ================= ENV =================
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

# ================= FLASK =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot ishlayapti!"

# ================= DOWNLOADS PAPKA =================
os.makedirs("downloads", exist_ok=True)

# ================= INSTAGRAM =================
L = instaloader.Instaloader(
    download_pictures=True,
    download_videos=True,
    download_video_thumbnails=False,
    save_metadata=False,
    post_metadata_txt_pattern=""
)

# ================= YOUTUBE =================
def download_youtube(url):
    try:
        yt = YouTube(url)

        stream = yt.streams.filter(
            progressive=True,
            file_extension="mp4"
        ).order_by("resolution").desc().first()

        file_path = stream.download(output_path="downloads")

        return file_path

    except Exception as e:
        return str(e)

# ================= INSTAGRAM =================
def download_instagram(url):
    try:
        shortcode = url.split("/")[-2]

        post = instaloader.Post.from_shortcode(
            L.context,
            shortcode
        )

        L.download_post(post, target="downloads")

        files = os.listdir("downloads")

        for file in files:
            if file.endswith(".mp4") or file.endswith(".jpg"):
                return os.path.join("downloads", file)

        return None

    except Exception as e:
        return str(e)

# ================= START =================
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "Link yuboring 🎬\n\nYouTube yoki Instagram"
    )

# ================= HANDLE =================
@bot.message_handler(func=lambda m: True)
def handle(message):

    url = message.text.strip()

    # ========= YOUTUBE =========
    if "youtube.com" in url or "youtu.be" in url:

        msg = bot.reply_to(message, "YouTube video yuklanmoqda...")

        result = download_youtube(url)

        if os.path.exists(result):

            with open(result, "rb") as video:
                bot.send_video(message.chat.id, video)

            os.remove(result)

        else:
            bot.edit_message_text(
                f"Xato:\n{result}",
                chat_id=message.chat.id,
                message_id=msg.message_id
            )

    # ========= INSTAGRAM =========
    elif "instagram.com" in url:

        msg = bot.reply_to(message, "Instagram post yuklanmoqda...")

        result = download_instagram(url)

        if result and os.path.exists(result):

            if result.endswith(".mp4"):

                with open(result, "rb") as video:
                    bot.send_video(message.chat.id, video)

            else:

                with open(result, "rb") as photo:
                    bot.send_photo(message.chat.id, photo)

            os.remove(result)

        else:

            bot.edit_message_text(
                f"Xato:\n{result}",
                chat_id=message.chat.id,
                message_id=msg.message_id
            )

    else:
        bot.reply_to(
            message,
            "Faqat Instagram yoki YouTube link yuboring."
        )

# ================= BOT =================
def run_bot():
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

# ================= MAIN =================
if __name__ == "__main__":

    Thread(target=run_bot).start()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
