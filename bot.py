import logging
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

BOT_TOKEN = "8511615749:AAHsZ94HBr5KBYSkMNmFbKt1JT67ZRZWTRE"          # сюда токен бота из BotFather
SPREADSHEET_NAME = "OS_DIARY_LOG"              # название таблицы (как на вкладке сверху слева)
SHEET_NAME = "DIARY"                           # имя листа внутри таблицы
JSON_KEY_FILE = "osdiarybot-c085486add49.json"         # точное имя JSON-файла сервиса (лежит рядом с bot.py)
ADMIN_CHAT_ID = 6673419838                     # твой chat_id для уведомлений от бота


# ========= GOOGLE SHEETS AUTH =========

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = Credentials.from_service_account_file(JSON_KEY_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open(SPREADSHEET_NAME).worksheet(SHEET_NAME)


# ========= LOGGING =========

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


# ========= ADMIN MESSAGE FORMATTER =========

def format_admin_message(user, text, ts: str) -> str:
    """Формируем красивое уведомление админу."""
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
    await update.message.reply_text("OS Diary готов принимать твои записи ✨")


async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # игнорируем ботов на всякий случай
    if message.from_user and message.from_user.is_bot:
        return

    # берём только обычный текст
    text = (message.text or "").strip()
    if not text:
        return

    user = message.from_user

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    full_name = (
        f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}"
    ).strip()

    row = [
        ts,                   # Дата/время
        "OS_DIARY",           # Продукт
        str(user.id),         # USER ID
        user.username or "",  # Username
        full_name,            # Имя
        "text",               # Тип
        text,                 # Текст/подпись/медиа
    ]

    # 1) Пишем в таблицу
    try:
        sheet.append_row(row)
        logging.info("LOGGED_ROW: %s", row)
    except Exception as e:
        logging.error("SHEET_ERROR: %s", e)

    # 2) Шлём админу
    try:
        admin_text = format_admin_message(user, text, ts)
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)
    except Exception as e:
        logging.error("ADMIN_SEND_ERROR: %s", e)


# ========= MAIN =========

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # /start отдельным хендлером
    app.add_handler(CommandHandler("start", start))

    # все текстовые сообщения из лички
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
