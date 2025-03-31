import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web

# ====================
# КОНФИГУРАЦИЯ
# ====================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Получаем токен из переменных окружения
ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None  # Опционально
PORT = int(os.getenv("PORT", 10000))     # Render требует указать порт

# Инициализация бота
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ====================
# КЛАВИАТУРЫ
# ====================
def main_keyboard():
    """Главное меню"""
    buttons = [
        [KeyboardButton(text="🎫 Купить билет")],
        [KeyboardButton(text="📅 Мероприятия"), KeyboardButton(text="📞 Контакты")],
        [KeyboardButton(text="⚙️ Настройки")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ====================
# ОБРАБОТЧИКИ КОМАНД
# ====================
@dp.message(Command("start"))
async def start(message: types.Message):
    """Обработчик команды /start"""
    try:
        await message.answer(
            "🎉 Добро пожаловать в бота!\n"
            "Выберите действие:",
            reply_markup=main_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")

@dp.message(F.text == "🎫 Купить билет")
async def buy_ticket(message: types.Message):
    """Обработчик кнопки покупки билета"""
    await message.answer("Выберите тип билета:\n\n• Стандарт - 20₼\n• VIP - 40₼")

@dp.message(F.text == "📞 Контакты")
async def contacts(message: types.Message):
    """Контактная информация"""
    await message.answer("Наши контакты:\nТелефон: +994 12 345 67 89")

# ====================
# АДМИН-ПАНЕЛЬ
# ====================
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    """Команды только для админа"""
    await message.answer("🔧 Админ-панель:\n/stats - статистика\n/users - список пользователей")

# ====================
# HTTP-СЕРВЕР ДЛЯ RENDER
# ====================
async def http_handler(request):
    """Обработчик HTTP-запросов"""
    return web.Response(text="🤖 Бот работает в режиме polling!")

async def run_bot():
    """Запуск бота"""
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Остановка бота: {e}")
        raise

# ====================
# ОСНОВНАЯ ФУНКЦИЯ
# ====================
async def main():
    """Точка входа"""
    # Запускаем бота в фоне
    bot_task = asyncio.create_task(run_bot())

    # Настраиваем HTTP-сервер
    app = web.Application()
    app.router.add_get("/", http_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info(f"🚀 Бот запущен на порту {PORT}")
    await asyncio.Event().wait()  # Бесконечное ожидание

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.critical(f"Фатальная ошибка: {e}")
