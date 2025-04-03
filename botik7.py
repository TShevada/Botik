import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ===== CONFIG =====
TOKEN = os.getenv("TELEGRAM_TOKEN", "DEFAULT_TOKEN")
YOUR_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "123456789"))
PORT = int(os.getenv("PORT", 10001))  # Using your requested port
# ==================

# Initialize bot
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)
user_lang = {}

# Updated Ticket Data (RU/AZ/EN)
TICKET_TYPES = {
    "standard": {
        "ru": {"name": "Стандарт", "price": "20 АЗН", "desc": "Приветственные коктейли, Fan Zone"},
        "az": {"name": "Standart", "price": "20 AZN", "desc": "Xoş gəlmisiniz kokteylləri, Fan Zone"},
        "en": {"name": "Standard", "price": "20 AZN", "desc": "Welcome cocktails, Fan Zone"}
    },
    "vip_single": {
        "ru": {"name": "VIP (Одиночный)", "price": "40 АЗН", "desc": "Индивидуальное место за столиком, Приветственный коктейль"},
        "az": {"name": "VIP (Tək)", "price": "40 AZN", "desc": "Fərdi oturacaq yeri, Xoş gəlmisiniz kokteyli"},
        "en": {"name": "VIP (Single)", "price": "40 AZN", "desc": "Individual seating, Welcome cocktail"}
    },
    "vip_table": {
        "ru": {"name": "VIP (Столик)", "price": "160 АЗН", "desc": "Отдельный столик на 4 человек, Приветственные коктейли"},
        "az": {"name": "VIP (Masalıq)", "price": "160 AZN", "desc": "4 nəfərlik masa, Xoş gəlmisiniz kokteylləri"},
        "en": {"name": "VIP (Table)", "price": "160 AZN", "desc": "Private table for 4, Welcome cocktails"}
    },
    "exclusive": {
        "ru": {"name": "Exclusive (Столик)", "price": "240 АЗН", "desc": "Доступ за DJ столом, Столик на 4 человек, Коктейли"},
        "az": {"name": "Exclusive (Masalıq)", "price": "240 AZN", "desc": "DJ masasına giriş, 4 nəfərlik masa, Kokteyllər"},
        "en": {"name": "Exclusive (Table)", "price": "240 AZN", "desc": "Access behind DJ booth, Table for 4, Cocktails"}
    }
}

# Keyboard Generators
def get_lang_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇦🇿 Azərbaycan")],
            [KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True
    )

def get_ticket_keyboard(lang):
    buttons = [
        [KeyboardButton(text=f"{TICKET_TYPES['standard'][lang]['name']} ({TICKET_TYPES['standard'][lang]['price']})")],
        [KeyboardButton(text=f"{TICKET_TYPES['vip_single'][lang]['name']} ({TICKET_TYPES['vip_single'][lang]['price']})")],
        [KeyboardButton(text=f"{TICKET_TYPES['vip_table'][lang]['name']} ({TICKET_TYPES['vip_table'][lang]['price']})")],
        [KeyboardButton(text=f"{TICKET_TYPES['exclusive'][lang]['name']} ({TICKET_TYPES['exclusive'][lang]['price']})")],
        [KeyboardButton(text="⬅️ Назад" if lang == "ru" else "⬅️ Geri" if lang == "az" else "⬅️ Back")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Handlers
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Выберите язык / Select language / Dil seçin:", reply_markup=get_lang_keyboard())

@dp.message(F.text.in_(["🇷🇺 Русский", "🇦🇿 Azərbaycan", "🇬🇧 English"]))
async def set_language(message: types.Message):
    lang_map = {"🇷🇺 Русский": "ru", "🇦🇿 Azərbaycan": "az", "🇬🇧 English": "en"}
    user_lang[message.from_user.id] = lang = lang_map[message.text]
    await message.answer(
        "Выберите билет:" if lang == "ru" else "Bilet seçin:" if lang == "az" else "Select ticket:",
        reply_markup=get_ticket_keyboard(lang)
    )

@dp.message(F.text.regexp(r"(Стандарт|Standart|Standard|VIP.*|Exclusive)"))
async def show_ticket_info(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    ticket_type = None
    
    if "Стандарт" in message.text or "Standart" in message.text or "Standard" in message.text:
        ticket_type = "standard"
    elif "Одиночный" in message.text or "Tək" in message.text or "Single" in message.text:
        ticket_type = "vip_single"
    elif "Столик" in message.text or "Masalıq" in message.text or "Table" in message.text:
        ticket_type = "vip_table" if "240" not in message.text else "exclusive"
    
    if ticket_type:
        await message.answer(
            f"🎟 {TICKET_TYPES[ticket_type][lang]['name']}\n"
            f"💵 {TICKET_TYPES[ticket_type][lang]['price']}\n"
            f"📝 {TICKET_TYPES[ticket_type][lang]['desc']}\n\n"
            f"❗️ {'Билеты не подлежат возврату!' if lang == 'ru' else 'Biletlər geri qaytarılmır!' if lang == 'az' else 'Tickets are non-refundable!'}"
        )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
