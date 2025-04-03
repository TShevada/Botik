import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ===== CONFIGURATION =====
TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN")
YOUR_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "YOUR_ADMIN_ID"))
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "4169 7388 9268 3164")
PORT = int(os.getenv("PORT", 10001))  # Changed to port 10001
# ========================

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Storage
user_lang = {}
user_data = {}

# Updated Ticket Prices
TICKET_TYPES = {
    "standard": {
        "ru": {
            "name": "Стандарт",
            "price": "20 АЗН",
            "desc": "Приветственные коктейли, Fan Zone",
            "features": ["Приветственные коктейли", "Fan Zone"]
        },
        "az": {
            "name": "Standart",
            "price": "20 AZN",
            "desc": "Xoş gəlmisiniz kokteylləri, Fan Zone",
            "features": ["Xoş gəlmisiniz kokteylləri", "Fan Zone"]
        },
        "en": {
            "name": "Standard",
            "price": "20 AZN",
            "desc": "Welcome cocktails, Fan Zone",
            "features": ["Welcome cocktails", "Fan Zone"]
        }
    },
    "vip_single": {
        "ru": {
            "name": "VIP (Одиночный)",
            "price": "40 АЗН",
            "desc": "Индивидуальное место за столиком, Приветственный коктейль",
            "features": ["Индивидуальное место", "Приветственный коктейль", "Ограниченное количество"]
        },
        "az": {
            "name": "VIP (Tək)",
            "price": "40 AZN",
            "desc": "Fərdi oturacaq yeri, Xoş gəlmisiniz kokteyli",
            "features": ["Fərdi oturacaq", "Xoş gəlmisiniz kokteyli", "Məhdud sayda"]
        },
        "en": {
            "name": "VIP (Single)",
            "price": "40 AZN",
            "desc": "Individual seating, Welcome cocktail",
            "features": ["Individual seat", "Welcome cocktail", "Limited availability"]
        }
    },
    "vip_table": {
        "ru": {
            "name": "VIP (Столик)",
            "price": "160 АЗН",
            "desc": "Отдельный столик на 4 человек, Приветственные коктейли",
            "features": ["Столик на 4 персоны", "Приветственные коктейли", "Ограниченное количество"]
        },
        "az": {
            "name": "VIP (Masalıq)",
            "price": "160 AZN",
            "desc": "4 nəfərlik masa, Xoş gəlmisiniz kokteylləri",
            "features": ["4 nəfərlik masa", "Xoş gəlmisiniz kokteylləri", "Məhdud sayda"]
        },
        "en": {
            "name": "VIP (Table)",
            "price": "160 AZN",
            "desc": "Private table for 4, Welcome cocktails",
            "features": ["Table for 4", "Welcome cocktails", "Limited availability"]
        }
    },
    "exclusive": {
        "ru": {
            "name": "Exclusive (Столик)",
            "price": "240 АЗН",
            "desc": "Доступ за DJ столом, Столик на 4 человек, Коктейли",
            "features": ["Доступ за DJ", "Столик на 4 персоны", "Приветственные коктейли", "Ограниченное количество"]
        },
        "az": {
            "name": "Exclusive (Masalıq)",
            "price": "240 AZN",
            "desc": "DJ masasına giriş, 4 nəfərlik masa, Kokteyllər",
            "features": ["DJ masasına giriş", "4 nəfərlik masa", "Xoş gəlmisiniz kokteylləri", "Məhdud sayda"]
        },
        "en": {
            "name": "Exclusive (Table)",
            "price": "240 AZN",
            "desc": "Access behind DJ booth, Table for 4, Cocktails",
            "features": ["DJ booth access", "Table for 4", "Welcome cocktails", "Limited availability"]
        }
    }
}

# Helper Functions
def is_admin(user_id: int) -> bool:
    return user_id == YOUR_TELEGRAM_ID

def get_lang_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇦🇿 Azərbaycan")],
            [KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True
    )

def get_menu_keyboard(lang):
    buttons = [
        [KeyboardButton(text="🎫 Билеты" if lang == "ru" else "🎫 Biletlər" if lang == "az" else "🎫 Tickets")],
        [KeyboardButton(text="📅 Мероприятия" if lang == "ru" else "📅 Tədbirlər" if lang == "az" else "📅 Events")],
        [KeyboardButton(text="📞 Контакты" if lang == "ru" else "📞 Əlaqə" if lang == "az" else "📞 Contacts")],
        [KeyboardButton(text="🌐 Язык" if lang == "ru" else "🌐 Dil" if lang == "az" else "🌐 Language")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_ticket_type_keyboard(lang):
    buttons = [
        [KeyboardButton(text=f"{TICKET_TYPES['standard'][lang]['name']} ({TICKET_TYPES['standard'][lang]['price']})"],
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
    confirmation = {
        "ru": "Язык установлен: Русский",
        "az": "Dil seçildi: Azərbaycan",
        "en": "Language set: English"
    }[lang]
    await message.answer(confirmation, reply_markup=get_menu_keyboard(lang))

@dp.message(F.text.in_(["🎫 Билеты", "🎫 Biletlər", "🎫 Tickets"]))
async def tickets_menu_handler(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    
    tickets_info = {
        "ru": "🎟 Доступные билеты:\n\n"
              "1. Стандарт - 20 АЗН\n"
              "   • Приветственные коктейли\n"
              "   • Fan Zone\n\n"
              "2. VIP (Одиночный) - 40 АЗН\n"
              "   • Индивидуальное место\n"
              "   • Приветственный коктейль\n"
              "   • Ограниченное количество\n\n"
              "3. VIP (Столик) - 160 АЗН\n"
              "   • Столик на 4 персоны\n"
              "   • Приветственные коктейли\n"
              "   • Ограниченное количество\n\n"
              "4. Exclusive (Столик) - 240 АЗН\n"
              "   • Доступ за DJ столом\n"
              "   • Столик на 4 персоны\n"
              "   • Приветственные коктейли\n"
              "   • Ограниченное количество\n\n"
              "❗️Билеты не подлежат возврату❗️",
        "az": "🎟 Mövcud biletlər:\n\n"
              "1. Standart - 20 AZN\n"
              "   • Xoş gəlmisiniz kokteylləri\n"
              "   • Fan Zone\n\n"
              "2. VIP (Tək) - 40 AZN\n"
              "   • Fərdi oturacaq\n"
              "   • Xoş gəlmisiniz kokteyli\n"
              "   • Məhdud sayda\n\n"
              "3. VIP (Masalıq) - 160 AZN\n"
              "   • 4 nəfərlik masa\n"
              "   • Xoş gəlmisiniz kokteylləri\n"
              "   • Məhdud sayda\n\n"
              "4. Exclusive (Masalıq) - 240 AZN\n"
              "   • DJ masasına giriş\n"
              "   • 4 nəfərlik masa\n"
              "   • Xoş gəlmisiniz kokteylləri\n"
              "   • Məhdud sayda\n\n"
              "❗️Biletlər geri qaytarılmır❗️",
        "en": "🎟 Available tickets:\n\n"
              "1. Standard - 20 AZN\n"
              "   • Welcome cocktails\n"
              "   • Fan Zone\n\n"
              "2. VIP (Single) - 40 AZN\n"
              "   • Individual seat\n"
              "   • Welcome cocktail\n"
              "   • Limited availability\n\n"
              "3. VIP (Table) - 160 AZN\n"
              "   • Table for 4\n"
              "   • Welcome cocktails\n"
              "   • Limited availability\n\n"
              "4. Exclusive (Table) - 240 AZN\n"
              "   • DJ booth access\n"
              "   • Table for 4\n"
              "   • Welcome cocktails\n"
              "   • Limited availability\n\n"
              "❗️Tickets are non-refundable❗️"
    }[lang]
    
    await message.answer(tickets_info, reply_markup=get_ticket_type_keyboard(lang))

# [Rest of your handlers...]

async def main():
    # Start bot polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
