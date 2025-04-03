import os
from aiogram import Bot

# Get token - THIS IS MANDATORY
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # ← Correct syntax
if not TOKEN:
    raise RuntimeError("Telegram token missing!")

bot = Bot(token=TOKEN)  # ← Token used here
