import telebot
import requests
import json
from datetime import datetime
import time
import threading
import os
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def ask_ai(user_text):
    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4.1-mini",
        "input": user_text
    }

    r = requests.post(url, headers=headers, json=data, timeout=60)
    r.raise_for_status()
    result = r.json()

    return result["output"][0]["content"][0]["text"]
# === CONFIG ===
BOT_TOKEN = ("8799005350:AAFHmFzLKMOrKg5qoRnUN-hsrFY_wBQtTtw")
ADMIN_ID = [7304157931]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
app = Flask(__name__)

SYSTEM_PROMPT = """
BU YERGA PROMPT YOZILADI
"""

stats = {
    "users": set(),
    "messages": 0
}

# === FLASK ROUTES (Render uchun) ===
@app.route("/")
def home():
    return "HydraAI ishlayapti", 200

@app.route("/health")
def health():
    return {"status": "ok"}, 200


# === START ===
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    fname = message.from_user.first_name or "NoName"

    # adminga xabar
    for admin in ADMIN_ID:
        try:
            bot.send_message(
                admin,
                f"🆕 *Yangi foydalanuvchi*\n"
                f"👤 {fname}\n"
                f"🆔 `{user_id}`\n"
                f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode="Markdown"
            )
        except:
            pass

    bot.send_message(
        message.chat.id,
        "<b>👋 Salom! Men HydraAI</b>man.\n\nSavolingizni yozing.",
        parse_mode="HTML"
    )


# === ABOUT ===
@bot.message_handler(commands=['about'])
def about_cmd(message):
    about_text = (
        "<b>🤖 Bot haqida</b>\n\n"
        "🔹 Nomi: HydraAI\n"
        "🔹 Versiya: 1.0\n"
        "🔹 Tavsif: AI chatbot\n\n"
        "👨‍💻 Dasturchi: @farruhbek_umarjonov"
    )
    bot.send_message(message.chat.id, about_text, parse_mode="HTML")


# === COMMANDS ===
@bot.message_handler(commands=['commands'])
def command_cmd(message):
    text = (
        "<b>⚙ Buyruqlar</b>\n\n"
        "🔹 /about\n"
        "🔹 /commands\n"
        "🔹 /admin\n"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")


# === ADMIN PANEL ===
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_ID:
        return

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"),
        InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
    )

    bot.send_message(
        message.chat.id,
        "*Admin panel*",
        reply_markup=markup,
        parse_mode="Markdown"
    )


# === CALLBACK ===
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id not in ADMIN_ID:
        return

    if call.data == "admin_stats":
        bot.send_message(
            call.message.chat.id,
            f"👥 Users: {len(stats['users'])}\n💬 Messages: {stats['messages']}"
        )

    elif call.data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "Xabar kiriting:")
        bot.register_next_step_handler(msg, process_broadcast)


# === BROADCAST ===
def process_broadcast(message):
    if message.from_user.id not in ADMIN_ID:
        return

    text = message.text
    success, fail = 0, 0

    for user in list(stats["users"]):
        try:
            bot.send_message(user, f"📢 {text}")
            success += 1
            time.sleep(0.05)
        except:
            fail += 1

    for admin in ADMIN_ID:
        bot.send_message(admin, f"✅ {success} ta yuborildi\n❌ {fail} ta xato")


# === CHAT ===
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text

    stats["users"].add(user_id)
    stats["messages"] += 1

    full_prompt = f"{SYSTEM_PROMPT}\n\nSavol: {text}"

    url = "OPENAI_API_KEY"
    params = {"q": full_prompt}

    try:
        r = requests.get(url, params=params, timeout=60)
        answer = r.text

        if not answer:
            answer = "❌ Javob topilmadi"

        bot.reply_to(message, answer)

    except Exception as e:
        bot.reply_to(message, f"Xato: {e}")


# === RUN BOT ===
def run_bot():
    print("Bot ishlayapti...")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
