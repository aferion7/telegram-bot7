import os
import json
import asyncio
import random
from pathlib import Path

from flask import Flask, request
from aiogram import Bot, Dispatcher
from aiogram.types import (
    Update,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReactionTypeEmoji,
)
from aiogram.filters import CommandStart, Command

BOT_TOKEN = "8799005350:AAFHmFzLKMOrKg5qoRnUN-hsrFY_wBQtTtw"
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}" if RENDER_EXTERNAL_URL else None

DATA_FILE = Path("users.json")

DEFAULT_REACTIONS = ["👍", "🔥", "❤️", "⚡", "😍"]

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def load_data():
    if not DATA_FILE.exists():
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user_settings(user_id: int):
    data = load_data()
    uid = str(user_id)

    if uid not in data:
        data[uid] = {
            "enabled": True,
            "reactions": DEFAULT_REACTIONS
        }
        save_data(data)

    return data[uid]


def set_user_enabled(user_id: int, value: bool):
    data = load_data()
    uid = str(user_id)

    if uid not in data:
        data[uid] = {
            "enabled": value,
            "reactions": DEFAULT_REACTIONS
        }
    else:
        data[uid]["enabled"] = value

    save_data(data)


def set_user_reactions(user_id: int, reactions: list):
    data = load_data()
    uid = str(user_id)

    if uid not in data:
        data[uid] = {
            "enabled": True,
            "reactions": reactions
        }
    else:
        data[uid]["reactions"] = reactions

    save_data(data)


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Status"), KeyboardButton(text="ℹ️ Yordam")],
            [KeyboardButton(text="🟢 Reaction ON"), KeyboardButton(text="🔴 Reaction OFF")],
            [KeyboardButton(text="😀 Emojilar"), KeyboardButton(text="♻️ Reset")]
        ],
        resize_keyboard=True
    )


@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    settings = get_user_settings(user_id)

    status_text = "YONIQ ✅" if settings["enabled"] else "O‘CHIQ ❌"
    emojis = " ".join(settings["reactions"])

    text = (
        "Bot ishga tushdi ✅\n\n"
        f"Status: {status_text}\n"
        f"Reaksiyalar: {emojis}\n\n"
        "Menyu tugmalaridan foydalaning."
    )

    await message.answer(text, reply_markup=main_menu())


@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "Buyruqlar:\n"
        "/start - botni ishga tushirish\n"
        "/help - yordam\n"
        "/status - holatni ko‘rish\n"
        "/on - reaction yoqish\n"
        "/off - reaction o‘chirish\n"
        "/setemoji 👍 🔥 ❤️ - reactionlarni almashtirish\n\n"
        "Tugmalar orqali ham ishlatishingiz mumkin.",
        reply_markup=main_menu()
    )


@dp.message(Command("status"))
async def status_handler(message: Message):
    settings = get_user_settings(message.from_user.id)
    status_text = "YONIQ ✅" if settings["enabled"] else "O‘CHIQ ❌"
    emojis = " ".join(settings["reactions"])

    await message.answer(
        f"Status: {status_text}\n"
        f"Reaksiyalar: {emojis}",
        reply_markup=main_menu()
    )


@dp.message(Command("on"))
async def on_handler(message: Message):
    set_user_enabled(message.from_user.id, True)
    await message.answer("Reaction yoqildi ✅", reply_markup=main_menu())


@dp.message(Command("off"))
async def off_handler(message: Message):
    set_user_enabled(message.from_user.id, False)
    await message.answer("Reaction o‘chirildi ❌", reply_markup=main_menu())


@dp.message(Command("setemoji"))
async def setemoji_handler(message: Message):
    parts = message.text.split()[1:]

    if not parts:
        await message.answer(
            "Masalan:\n/setemoji 👍 🔥 ❤️",
            reply_markup=main_menu()
        )
        return

    set_user_reactions(message.from_user.id, parts)
    await message.answer(
        f"Yangi reaksiyalar saqlandi: {' '.join(parts)}",
        reply_markup=main_menu()
    )


@dp.message()
async def text_buttons_handler(message: Message):
    text = (message.text or "").strip()
    user_id = message.from_user.id

    if text == "✅ Status":
        settings = get_user_settings(user_id)
        status_text = "YONIQ ✅" if settings["enabled"] else "O‘CHIQ ❌"
        emojis = " ".join(settings["reactions"])
        await message.answer(
            f"Status: {status_text}\nReaksiyalar: {emojis}",
            reply_markup=main_menu()
        )
        return

    if text == "ℹ️ Yordam":
        await message.answer(
            "Reaction bot yordam menyusi.\n\n"
            "Kerakli tugmani bosing yoki buyruqlardan foydalaning:\n"
            "/on, /off, /status, /setemoji",
            reply_markup=main_menu()
        )
        return

    if text == "🟢 Reaction ON":
        set_user_enabled(user_id, True)
        await message.answer("Reaction yoqildi ✅", reply_markup=main_menu())
        return

    if text == "🔴 Reaction OFF":
        set_user_enabled(user_id, False)
        await message.answer("Reaction o‘chirildi ❌", reply_markup=main_menu())
        return

    if text == "😀 Emojilar":
        settings = get_user_settings(user_id)
        await message.answer(
            "Hozirgi emoji'lar: " + " ".join(settings["reactions"]) + "\n\n"
            "Almashtirish uchun misol:\n"
            "/setemoji 👍 🔥 ❤️",
            reply_markup=main_menu()
        )
        return

    if text == "♻️ Reset":
        set_user_reactions(user_id, DEFAULT_REACTIONS)
        set_user_enabled(user_id, True)
        await message.answer(
            "Sozlamalar reset qilindi ✅",
            reply_markup=main_menu()
        )
        return

    # oddiy xabarlarga auto reaction
    settings = get_user_settings(user_id)

    if not settings["enabled"]:
        return

    if not settings["reactions"]:
        return

    try:
        emoji = random.choice(settings["reactions"])

        await bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji=emoji)],
            is_big=False
        )
    except Exception as e:
        print(f"Reaction xatolik: {e}")


@app.route("/", methods=["GET"])
def home():
    return "Bot ishlayapti ✅", 200


@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        update = Update.model_validate(request.get_json(force=True))
        asyncio.run(dp.feed_update(bot, update))
        return "ok", 200
    except Exception as e:
        print(f"Webhook xatolik: {e}")
        return "error", 500


async def setup_webhook():
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        print(f"Webhook o‘rnatildi: {WEBHOOK_URL}")
    else:
        print("RENDER_EXTERNAL_URL topilmadi, webhook o‘rnatilmadi.")


try:
    asyncio.run(setup_webhook())
except Exception as e:
    print(f"Startup xatolik: {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
