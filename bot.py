import logging
import os
import json
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import gspread
from google.oauth2.service_account import Credentials

# ========= CONFIG =========

BOT_TOKEN = os.environ.get("8511615749:AAHsZ94HBr5KBYSkMNmFbKt1JT67ZRZWTRE", "")  # на Render берем из переменной окружения
SPREADSHEET_NAME = "OS_DIARY_LOG"           # просто для себя, открыть будем по ID
SHEET_NAME = "DIARY"
SHEET_ID = "1VWwZLhlrIc36_jIG_yo9wp9O8mVQefNbdqsl35nYR30"  # твой ID таблицы
ADMIN_CHAT_ID = 6673419838

# ========= GOOGLE SHEETS AUTH =========

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds_info = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# ========= LOGGING =========

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


# ========= ADMIN MESSAGE FORMATTER =========

def format_admin_message(user, text: str, ts: str) -> str:
    first = (user.first_name or "").strip()
    last = (user.last_name or "").strip()
    name = (first + " " + last).strip() or "(без имени)"
    username = f"@{user.username}" if user.username else ""

    return (
        "Новое сообщение в OS_DIARY\n"
        f"От: {name} {username}\n"
        f"User ID: {user.id}\n"
        "Тип: text\n"
        f"Время: {ts}\n"
        "Текст:\n"
        f"{text}"
    )


# ========= HANDLERS =========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("OS Diary готов принимать твои записи ✨ Просто пиши сообщениями.")


async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    if message.from_user and message.from_user.is_bot:
        return

    text = (message.text or "").strip()
    if not text:
        return

    user = message.from_user
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    full_name = (
        f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}"
    ).strip()

    row = [
        ts,                 # Дата/время
        "OS_DIARY",         # Продукт
        str(user.id),       # USER ID
        user.username or "",# Username
        full_name,          # Имя
        "text",             # Тип
        text,               # Текст/подпись/медиа
    ]

    # Пишем в таблицу
    try:
        sheet.append_row(row)
        logging.info("LOGGED_ROW: %s", row)
    except Exception as e:
        logging.error("SHEET_ERROR: %s", e)

    # Шлем админу
    try:
        admin_text = format_admin_message(user, text, ts)
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)
    except Exception as e:
        logging.error("ADMIN_SEND_ERROR: %s", e)


# ========= MAIN =========

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & (~filters.COMMAND),
            save_message,
        )
    )

    logging.info("Bot started. Waiting for messages...")
    app.run_polling()


if __name__ == "__main__":
    main()
