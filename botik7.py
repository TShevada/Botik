import os
import random
import string
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiohttp import web

# --- Configuration ---
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Set in Render environment
ADMIN_ID = 1291104906  # Your Telegram ID
PORT = int(os.getenv("PORT", "10001"))  # Try 10001-10025
PAYMENT_CARD = "4169 7388 9268 3164"

# --- Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()

# --- Ticket Data ---
TICKETS = {
    'standard': {
        'ru': ('Стандарт (20 AZN)', '• Приветственные коктейли\n• Fan Zone'),
        'az': ('Standart (20 AZN)', '• Salam kokteylləri\n• Fan Zone'),
        'en': ('Standard (20 AZN)', '• Welcome cocktails\n• Fan Zone')
    },
    'vip_single': {
        'ru': ('VIP (40 AZN)', '• Индивидуальное место\n• Коктейль'),
        'az': ('VIP (40 AZN)', '• Fərdi yer\n• Kokteyl'),
        'en': ('VIP (40 AZN)', '• Individual seat\n• Cocktail')
    },
    'exclusive_single': {
        'ru': ('Exclusive (60 AZN)', '• Доступ к DJ\n• Индивидуальное место'),
        'az': ('Exclusive (60 AZN)', '• DJ girişi\n• Fərdi yer'),
        'en': ('Exclusive (60 AZN)', '• DJ access\n• Individual seat')
    },
    'exclusive_table': {
        'ru': ('Exclusive Столик (240 AZN)', '• VIP зона\n• Столик на 4\n• 4 коктейля'),
        'az': ('Exclusive Masa (240 AZN)', '• VIP zona\n• 4 nəfərlik masa\n• 4 kokteyl'),
        'en': ('Exclusive Table (240 AZN)', '• VIP area\n• Table for 4\n• 4 cocktails')
    }
}

# --- Web Server for Render ---
async def health_check(request):
    return web.Response(text="Bot is running")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logger.info(f"🌐 Health check running on port {PORT}")
    except OSError as e:
        logger.error(f"Port {PORT} unavailable, trying fallback...")
        site = web.TCPSite(runner, "0.0.0.0", 10002)  # Fallback port
        await site.start()

# --- Bot Handlers ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Выберите язык / Dil seçin / Select language:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇦🇿 Azərbaycan")],
                [KeyboardButton(text="🇬🇧 English")]
            ],
            resize_keyboard=True
        )
    )

@dp.message(F.text.in_(["🇷🇺 Русский", "🇦🇿 Azərbaycan", "🇬🇧 English"]))
async def set_language(message: types.Message):
    lang = "ru" if "🇷🇺" in message.text else "az" if "🇦🇿" in message.text else "en"
    await message.answer(
        "Выберите билет:" if lang == "ru" else "Bilet seçin:" if lang == "az" else "Select ticket:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=TICKETS[t][lang][0])] for t in TICKETS
            ] + [[KeyboardButton(
                text="⬅️ Назад" if lang == "ru" else "⬅️ Geri" if lang == "az" else "⬅️ Back"
            )]],
            resize_keyboard=True
        )
    )

# --- Main ---
async def main():
    await asyncio.gather(
        run_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN not set in environment variables!")
    logging.info("Starting bot...")
    asyncio.run(main())
