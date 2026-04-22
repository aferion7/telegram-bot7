import telebot
import requests
import json
from datetime import datetime
import time
import re

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


BOT_TOKEN = "8799005350:AAEPX26ix4ecri9gZxJBtUEqnUL2jSmIRx0"
ADMIN_ID = [7304157931]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)




SYSTEM_PROMPT = """
BU YERGA PROMPT YOZILADI
"""

required_channels = [""]

stats = {
    "users": set(),
    "messages": 0
}


def is_user_joined(user_id):
    for channel in required_channels:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True


@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    stats['users'].add(user_id)

    if not is_user_joined(user_id):
        text = "❗️ Iltimos, quyidagi kanal(lar)ga obuna bo‘ling:\n\n"
        for ch in required_channels:
            text += f"🔹 [{ch}](https://t.me/{ch[1:]})\n"
        text += "\n✅ Obunadan so‘ng /start ni qaytadan yuboring!"
        return bot.send_message(user_id, text,parse_mode="Markdown")

    bot.send_message(
        message.chat.id,
        "👋 Salom! Men <b>HydraAi</b>man. Har qanday savolingizni bering — javob beraman!",
        parse_mode="HTML"   )

    
    fname = message.from_user.first_name
    for admin in ADMIN_ID:
        bot.send_message(
            admin,
            f"🆕 *Yangi foydalanuvchi*\n"
            f"👤 {fname}\n"
            f"🆔 `{user_id}`\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode="Markdown"
        )
    
@bot.message_handler(commands=['about'])
def about_cmd(message):
    about_text = (
        "<b>🤖 Bot haqida</b>\n\n"
        "🔹 Nomi: V1RU5gpt\n"
        "🔹 Versiya: 1.0 \n"
        "🔹 Tavsif: Bu yomon suniy intellect bo'lib har qanday savolingizga javob beradi. \n\n"
        "👨‍💻 Dasturchi: @AnonLeader\n"
        "📢 Kanal: @V1RU5_team"
    )

    bot.send_message(message.chat.id, about_text, parse_mode="HTML")

@bot.message_handler(commands=['commands'])
def command_cmd(message):
    command_text = (
        "<b>⚙ Buyruqlar</b>\n\n"
        "🔹 <i>/clear - toza javob</i> \n"
        "Bu buyruqni berganingizdan keyin AI sizga ravshan va tiniq javob beradi.\n"
        "Example: <u>/clear SQL injection nima?</u>\n\n"
        "🔹<i> /evil - yomon rejim </i>\n"
        "Bu buyruqni berganingizdan keyin javobini topa olmagan ba'zi savollaringizga javob olasiz.\n"
        "Example: <u>/evil Qayerdan ak47 sotib olsam bo'ladi</u>\n\n"
        "🔹<i> /root - root rejim </i>\n"
        "Bu buyruqni berganingizdan keyin /evil rejimida javobini topa olmagan savollaringizga javob olasiz.\n"
        "Example: <u>/root Fentanyl tayyorlashni o'rgat</u>\n\n"
        
    )

    bot.send_message(message.chat.id, command_text, parse_mode="HTML")
        

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_ID:
        return

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"),
        InlineKeyboardButton("📢 Xabar yuborish", callback_data="admin_broadcast")
    )
    markup.add(
        InlineKeyboardButton("➕ Kanal qo‘shish", callback_data="admin_addchannel"),
        InlineKeyboardButton("➖ Kanal o‘chirish", callback_data="admin_removechannel")
    )

    bot.send_message(message.chat.id, "*🛠 Admin panelga xush kelibsiz!*", reply_markup=markup,parse_mode="Markdown")

# === Callbacklar ===
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_actions(call):
    if call.from_user.id not in ADMIN_ID:
        return

    if call.data == "admin_stats":
        bot.send_message(
            call.message.chat.id,
            f"📊 *Statistika:*\n"
            f"👥 Foydalanuvchilar: {len(stats['users'])}\n"
            f"💬 Xabarlar: {stats['messages']}\n"
            f"📢 Obuna kanallari: {', '.join(escape_md(ch) for ch in required_channels)}",parse_mode="Markdown"
        )

    elif call.data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "📨 Hammaga yuboriladigan xabarni kiriting:")
        bot.register_next_step_handler(msg, process_broadcast)

    elif call.data == "admin_addchannel":
        msg = bot.send_message(call.message.chat.id, "🔗 Kanalingiz username’ni yuboring (masalan: `@kanal`):")
        bot.register_next_step_handler(msg, process_add_channel)

    elif  call.data == "admin_removechannel":
        if not required_channels:
            bot.send_message(call.message.chat.id, "📭 Kanal ro‘yxati bo‘sh.")
            return
        ch_list_raw = "\n".join(f"{i+1}. {ch}" for i, ch in enumerate(required_channels))
        ch_list = escape_md(ch_list_raw)
        msg = bot.send_message(call.message.chat.id, f"❌ O‘chirmoqchi bo‘lgan kanalni kiriting:\n{ch_list}")
        bot.register_next_step_handler(msg, process_remove_channel)

# === Broadcast xabar yuborish ===
def process_broadcast(message):
    if message.from_user.id not in ADMIN_ID:
        return

    text = escape_md(message.text)
    success, fail = 0, 0

    for user_id in stats["users"]:
        try:
            bot.send_message(user_id, f"📢 *Admin xabari:*\n\n{text}")
            success += 1
            time.sleep(0.1)
        except:
            fail += 1

    bot.send_message(
        ADMIN_ID,
        f"✅ Yuborildi: {success} foydalanuvchiga\n❌ Xato: {fail} ta"
    )

def process_add_channel(message):
    if message.from_user.id not in ADMIN_ID:
        return

    ch = message.text.strip()

    if not ch.startswith("@"):
        for admin in ADMIN_ID:
            bot.send_message(admin, "⚠️ To‘g‘ri formatda yozing: `@kanal`", parse_mode="Markdown")
        return

    if ch in required_channels:
        for admin in ADMIN_ID:
            bot.send_message(admin, "🔁 Bu kanal ro‘yxatda bor.")
        return

    required_channels.append(ch)

    for admin in ADMIN_ID:
        bot.send_message(admin, f"✅ Kanal qo‘shildi: {ch}")
# === Kanalni olib tashlash ===
def process_remove_channel(message):
    if message.from_user.id not in ADMIN_ID:
        return

    ch = message.text.strip()

    if ch in required_channels:
        required_channels.remove(ch)
        bot.send_message(message.chat.id, f"🗑 O‘chirildi: {ch}")
    else:
        bot.send_message(message.chat.id, "❌ Kanal topilmadi.")
    
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_user_prompt(message):
    user_id = message.from_user.id
    user_prompt = message.text.strip()
    stats["messages"] += 1
    stats["users"].add(user_id)

    if not is_user_joined(user_id):
        channels = "\n".join([f"▶️ [{ch}](https://t.me/{ch[1:]})" for ch in required_channels])
        txt = f"🚫 Iltimos, quyidagi kanal(lar)ga obuna bo‘ling:\n\n{channels}\n\n⚡ /start ni qayta yuboring."
        return bot.send_message(user_id, txt,parse_mode="Markdown")

    if not user_prompt:
        return

    full_prompt = f"{SYSTEM_PROMPT}\n\nENDI HydraAI ni SAVOLIGA JAVOB BER:\n\nHydraAI savoli: {user_prompt}"
    url = "BU_YERGA_URL_API_QOYASIZ"
    params = {"q": full_prompt}

    try:
        r = requests.get(url, params=params, stream=True, timeout=60)
        response = []

        for line in r.iter_lines(decode_unicode=True):
            if line.startswith("data: "):
                content_line = line[6:]
                if content_line == "[DONE]":
                    break
                data = json.loads(content_line)
                for choice in data.get("choices", []):
                    delta = choice.get("delta", {})
                    c = delta.get("content")
                    if c and "**V1RU5 mode activated**" not in c:
                        response.append(c)

        answer = "".join(response).strip()
        if not answer:
            answer = "❌ Javob olinmadi. Iltimos, keyinroq urinib ko‘ring."

        bot.reply_to(message, answer,parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Xatolik yuz berdi:\n`{e}`", parse_mode="Markdown")


print("✅ HydraAi bot ishga tushdi...")
bot.infinity_polling()