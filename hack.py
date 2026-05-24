import os
import asyncio
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

reply_map = {}

web_app = Flask(__name__)
tg_app = Application.builder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    ref = None
    if context.args:
        ref = context.args[0]

    if ref and str(user.id) != ref:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                f"📊 Yangi user referral orqali kirdi!\n\n"
                f"👤 {user.full_name}\n"
                f"🆔 {user.id}\n"
                f"🔗 Taklif qilgan ID: {ref}"
            ),
        )

    user_link = f"https://t.me/{context.bot.username}?start={user.id}"

    await update.message.reply_text(
        f"👋 Salom!\n\n"
        f"📩 Anonim xabar yuborishingiz mumkin.\n\n"
        f"🔗 Sizning shaxsiy linkingiz:\n{user_link}"
    )


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID:
        return

    user = update.effective_user
    msg = update.message

    info = (
        f"Kim yubordi:\n"
        f"Ism: {user.full_name}\n"
        f"Username: @{user.username if user.username else 'yoq'}\n"
        f"ID: {user.id}\n\n"
        f"Javob berish uchun shu xabarga reply qiling."
    )

    sent = None

    if msg.text:
        sent = await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"Yangi anonim xabar:\n{msg.text}\n\n{info}",
        )
    elif msg.photo:
        caption = msg.caption or ""
        sent = await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=msg.photo[-1].file_id,
            caption=f"Yangi anonim rasm\n\n{caption}\n\n{info}",
        )
    elif msg.video:
        caption = msg.caption or ""
        sent = await context.bot.send_video(
            chat_id=OWNER_ID,
            video=msg.video.file_id,
            caption=f"Yangi anonim video\n\n{caption}\n\n{info}",
        )
    elif msg.audio:
        caption = msg.caption or ""
        sent = await context.bot.send_audio(
            chat_id=OWNER_ID,
            audio=msg.audio.file_id,
            caption=f"Yangi anonim audio\n\n{caption}\n\n{info}",
        )
    elif msg.voice:
        sent = await context.bot.send_voice(
            chat_id=OWNER_ID,
            voice=msg.voice.file_id,
            caption=f"Yangi anonim voice\n\n{info}",
        )
    elif msg.document:
        caption = msg.caption or ""
        sent = await context.bot.send_document(
            chat_id=OWNER_ID,
            document=msg.document.file_id,
            caption=f"Yangi anonim fayl\n\n{caption}\n\n{info}",
        )
    else:
        sent = await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"Qo‘llab-quvvatlanmaydigan xabar turi.\n\n{info}",
        )

    if sent:
        reply_map[sent.message_id] = user.id

    await update.message.reply_text("Xabaringiz yuborildi.")


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not update.message.reply_to_message:
        return

    replied_message_id = update.message.reply_to_message.message_id
    target_user_id = reply_map.get(replied_message_id)

    if not target_user_id:
        await update.message.reply_text("Bu xabarga anonim reply qilib bo'lmaydi.")
        return

    note = "\n\nAgar javob bermoqchi bo'lsangiz, shunchaki shu yerga yozing."
    admin_msg = update.message

    if admin_msg.text:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"📩 Admin javobi:\n{admin_msg.text}{note}",
        )
    elif admin_msg.photo:
        caption = admin_msg.caption or ""
        await context.bot.send_photo(
            chat_id=target_user_id,
            photo=admin_msg.photo[-1].file_id,
            caption=f"📩 Admin javobi:\n{caption}{note}",
        )
    elif admin_msg.video:
        caption = admin_msg.caption or ""
        await context.bot.send_video(
            chat_id=target_user_id,
            video=admin_msg.video.file_id,
            caption=f"📩 Admin javobi:\n{caption}{note}",
        )
    elif admin_msg.audio:
        caption = admin_msg.caption or ""
        await context.bot.send_audio(
            chat_id=target_user_id,
            audio=admin_msg.audio.file_id,
            caption=f"📩 Admin javobi:\n{caption}{note}",
        )
    elif admin_msg.voice:
        await context.bot.send_voice(
            chat_id=target_user_id,
            voice=admin_msg.voice.file_id,
        )
        await context.bot.send_message(
            chat_id=target_user_id,
            text="Agar javob bermoqchi bo'lsangiz, shunchaki shu yerga yozing.",
        )
    elif admin_msg.document:
        caption = admin_msg.caption or ""
        await context.bot.send_document(
            chat_id=target_user_id,
            document=admin_msg.document.file_id,
            caption=f"📩 Admin javobi:\n{caption}{note}",
        )
    else:
        await update.message.reply_text("Faqat matn, rasm, video, audio, voice yoki fayl yuboring.")
        return

    await update.message.reply_text("Javob yuborildi.")


@web_app.route("/")
def home():
    return "Bot ishlayapti."


@web_app.route("/set_webhook")
def set_webhook():
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if not render_url:
        return "RENDER_EXTERNAL_URL topilmadi."

    webhook_url = f"{render_url}/webhook/{TOKEN}"
    result = asyncio.run(tg_app.bot.set_webhook(url=webhook_url))
    return f"Webhook o‘rnatildi: {result}"


@web_app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    asyncio.run(process_update(update))
    return "ok"


async def process_update(update: Update):
    if not getattr(tg_app, "_initialized", False):
        await tg_app.initialize()
        tg_app._initialized = True
    await tg_app.process_update(update)


tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(
    MessageHandler(filters.REPLY & filters.User(user_id=OWNER_ID), handle_admin_reply)
)
tg_app.add_handler(
    MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE | filters.Document.ALL)
        & ~filters.User(user_id=OWNER_ID),
        handle_user_message,
    )
)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)
