import os
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Admin user ID
ADMIN_ID = 7304157931  # o'zingizning ID

# Kanal username yoki ID (bot admin bo'lishi kerak)
SECRET_CHANNEL_ID = -1005433716096181076810  # yoki -1001234567890

# Botni ishga tushiramiz
updater = Updater(token=BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Oxirgi N postlarni kanaladan olish
def get_latest_posts(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("Faqat admin ishlata oladi.")
        return

    try:
        num_posts = int(context.args[0]) if context.args else 5  # default 5 post
    except ValueError:
        update.message.reply_text("Iltimos, son kiriting: /getlatest 5")
        return

    # Postlarni olish
    channel = context.bot.get_chat(SECRET_CHANNEL_ID)
    messages = channel.get_history(limit=num_posts)  # Bot API bilan cheklangan

    if not messages:
        update.message.reply_text("Hech qanday post topilmadi.")
        return

    for msg in messages:
        if msg.text:
            context.bot.send_message(chat_id=ADMIN_ID, text=msg.text)
        if msg.photo:
            file_id = msg.photo[-1].file_id
            context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id)
        if msg.video:
            file_id = msg.video.file_id
            context.bot.send_video(chat_id=ADMIN_ID, video=file_id)

    update.message.reply_text(f"{len(messages)} post yuklandi ✅")

# /start buyrug'i
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Salom! Bot kanal postlarini yuklashga tayyor.")

# Handlerlar
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("getlatest", get_latest_posts, pass_args=True))

# Botni ishga tushiramiz
updater.start_polling()
updater.idle()
