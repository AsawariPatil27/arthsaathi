import os
import tempfile

import requests
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3000")
VOICE_TIMEOUT = int(os.getenv("VOICE_TIMEOUT", 600))


def profile(update: Update):
    user = update.effective_user
    return {
        "telegramId": str(user.id),
        "username": user.username or "",
        "firstName": user.first_name or "",
    }


def keyboard(buttons):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(button["text"], callback_data=button["data"]) for button in row]
        for row in buttons
    ])


async def send(update: Update, data):
    target = update.message or update.callback_query.message
    markup = keyboard(data.get("buttons", [])) if data.get("buttons") else None
    await target.reply_text(data.get("reply", ""), reply_markup=markup)
    if data.get("imagePath"):
        with open(data["imagePath"], "rb") as image:
            await target.reply_photo(image)


def post(path, data=None, files=None, timeout=120):
    kwargs = {"data": data, "files": files} if files else {"json": data}
    response = requests.post(f"{BACKEND_URL}{path}", **kwargs, timeout=timeout)
    response.raise_for_status()
    return response.json()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = post("/chat", {**profile(update), "message": "/start"})
    await send(update, data)


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = post("/chat", {**profile(update), "message": update.message.text})
    await send(update, data)


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = post("/callback", {"telegramId": str(query.from_user.id), "callbackData": query.data})
    await send(update, data)


async def voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice_file = await update.message.voice.get_file()
    path = None

    try:
        await update.message.reply_text("Processing your voice note. First run can take a little time.")

        with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as temp:
            path = temp.name

        await voice_file.download_to_drive(path)

        with open(path, "rb") as audio:
            data = post("/voice", profile(update), {"audio": ("voice.oga", audio, "audio/ogg")}, timeout=VOICE_TIMEOUT)

        await send(update, data)
    except requests.exceptions.Timeout:
        await update.message.reply_text("Voice processing is taking too long. Try a shorter voice note once the model finishes loading.")
    except Exception as error:
        print("[BOT ERROR]", error)
        await update.message.reply_text("Could not process voice. Please try again.")
    finally:
        if path and os.path.exists(path):
            os.remove(path)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.VOICE, voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    print("[BOT] ArthSaathi bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
