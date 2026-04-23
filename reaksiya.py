import asyncio
import random
from flask import Flask, request

from aiogram import Bot, Dispatcher
from aiogram.types import Update, ReactionTypeEmoji
from aiogram.methods import SetMessageReaction

BOT_TOKEN = "8799005350:AAFHmFzLKMOrKg5qoRnUN-hsrFY_wBQtTtw"
WEBHOOK_URL = "https://your-app-name.onrender.com/webhook"

app = Flask(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

REACTIONS = ["❤️‍🔥", "🔥", "❤️", "⚡", "😍"]


@dp.message()
async def auto_react(message):
    try:
        emoji = random.choice(REACTIONS)

        await bot(SetMessageReaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji=emoji)]
        ))

        print("Reaction qo‘yildi:", emoji)

    except Exception as e:
        print("Xatolik:", e)


@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.model_validate(request.json)
    asyncio.run(dp.feed_update(bot, update))
    return "ok"


@app.route('/')
def home():
    return "Bot ishlayapti!"


async def set_webhook():
    await bot.set_webhook(WEBHOOK_URL)


if __name__ == "__main__":
    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=10000)
