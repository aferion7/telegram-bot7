import os
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

reply_map = {}
web_app = Flask(__name__)

# App bir marta yaratiladi
tg_app = Application.builder().token(TOKEN).build()

# Global event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


def run_async(coro):
    return loop.run_until_complete(coro)


# ... (barcha handler'lar o'zgarishsiz qoladi)

@web_app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    run_async(process_update(update))  # asyncio.run() o'rniga
    return "ok"


@web_app.route("/set_webhook")
def set_webhook():
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if not render_url:
        return "RENDER_EXTERNAL_URL topilmadi."
    webhook_url = f"{render_url}/webhook/{TOKEN}"
    result = run_async(tg_app.bot.set_webhook(url=webhook_url))
    return f"Webhook o'rnatildi: {result}"


async def process_update(update: Update):
    if not getattr(tg_app, "_initialized", False):
        await tg_app.initialize()
        tg_app._initialized = True
    await tg_app.process_update(update)


# Handler'lar
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(
    MessageHandler(filters.REPLY & filters.User(user_id=OWNER_ID), handle_admin_reply)
)
tg_app.add_handler(
    MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VIDEO | 
         filters.AUDIO | filters.VOICE | filters.Document.ALL)
        & ~filters.User(user_id=OWNER_ID),
        handle_user_message,
    )
)

# App'ni ishga tushirishdan oldin initialize qilamiz
run_async(tg_app.initialize())
tg_app._initialized = True

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)
