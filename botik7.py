import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- CONFIG ---
TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN")
PORT = 10001
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- STATES ---
class Form(StatesGroup):
    name = State()
    phone = State()
    photo = State()

# --- TICKET DATA ---
TICKET_TYPES = {
    "standard": {
        "ru": ["Стандарт (20 АЗН)", "Приветственные коктейли, Fan Zone"],
        "az": ["Standart (20 AZN)", "Xoş gəlmisiniz kokteylləri, Fan Zone"],
        "en": ["Standard (20 AZN)", "Welcome cocktails, Fan Zone"]
    },
    "vip_single": {
        "ru": ["VIP Одиночный (40 АЗН)", "Индивидуальное место, Коктейль"],
        "az": ["VIP Tək (40 AZN)", "Fərdi oturacaq, Kokteyl"],
        "en": ["VIP Single (40 AZN)", "Individual seat, Cocktail"]
    },
    "vip_table": {
        "ru": ["VIP Столик (160 АЗН)", "Стол на 4, Коктейли"],
        "az": ["VIP Masa (160 AZN)", "4 nəfərlik masa, Kokteyllər"],
        "en": ["VIP Table (160 AZN)", "Table for 4, Cocktails"]
    },
    "exclusive_single": {
        "ru": ["Exclusive Одиночный (60 АЗН)", "Доступ к DJ, Место"],
        "az": ["Exclusive Tək (60 AZN)", "DJ girişi, Oturacaq"],
        "en": ["Exclusive Single (60 AZN)", "DJ access, Seat"]
    },
    "exclusive_table": {
        "ru": ["Exclusive Столик (240 АЗН)", "VIP зона, Стол на 4"],
        "az": ["Exclusive Masa (240 AZN)", "VIP zona, 4 nəfərlik masa"],
        "en": ["Exclusive Table (240 AZN)", "VIP area, Table for 4"]
    }
}

# --- KEYBOARDS ---
def get_lang_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇦🇿 Azərbaycan")],
            [KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True
    )

def get_ticket_keyboard(lang):
    buttons = []
    for ticket_type in TICKET_TYPES:
        buttons.append([KeyboardButton(text=TICKET_TYPES[ticket_type][lang][0])])
    buttons.append([KeyboardButton(
        text="⬅️ Назад" if lang == "ru" else "⬅️ Geri" if lang == "az" else "⬅️ Back"
    )])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- HANDLERS ---
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите язык / Dil seçin / Select language:", 
                        reply_markup=get_lang_keyboard())

@dp.message(F.text.in_(["🇷🇺 Русский", "🇦🇿 Azərbaycan", "🇬🇧 English"]))
async def set_language(message: types.Message, state: FSMContext):
    lang = "ru" if "🇷🇺" in message.text else "az" if "🇦🇿" in message.text else "en"
    await state.update_data(lang=lang)
    await message.answer(
        "Введите ваше имя и фамилию:" if lang == "ru" else 
        "Ad və soyadınızı daxil edin:" if lang == "az" else 
        "Enter your full name:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Form.name)

@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    data = await state.get_data()
    lang = data.get('lang', 'en')
    
    await message.answer(
        "Введите ваш номер телефона:" if lang == "ru" else
        "Telefon nömrənizi daxil edin:" if lang == "az" else
        "Enter your phone number:"
    )
    await state.set_state(Form.phone)

@dp.message(Form.phone)
async def process_phone(message: types.Message, state: FSMContext):
    if not message.text.replace('+', '').isdigit():
        data = await state.get_data()
        lang = data.get('lang', 'en')
        await message.answer(
            "Неверный номер. Попробуйте еще раз:" if lang == "ru" else
            "Yanlış nömrə. Yenidən cəhd edin:" if lang == "az" else
            "Invalid number. Try again:"
        )
        return
    
    await state.update_data(phone=message.text)
    data = await state.get_data()
    lang = data.get('lang', 'en')
    
    await message.answer(
        "Выберите билет:" if lang == "ru" else "Bilet seçin:" if lang == "az" else "Select ticket:",
        reply_markup=get_ticket_keyboard(lang)
    )
    await state.set_state(Form.photo)

@dp.message(Form.photo)
async def process_ticket(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'en')
    
    # Check if message is a photo
    if message.photo:
        await message.answer(
            "Спасибо! Ваша заявка принята." if lang == "ru" else
            "Təşəkkürlər! Müraciətiniz qəbul edildi." if lang == "az" else
            "Thank you! Your application has been received."
        )
        await state.clear()
        return
    
    # Handle ticket selection
    for ticket_type in TICKET_TYPES:
        if TICKET_TYPES[ticket_type][lang][0] in message.text:
            await state.update_data(ticket_type=ticket_type)
            await message.answer(
                "Отправьте фото оплаты:" if lang == "ru" else
                "Ödəniş şəklini göndərin:" if lang == "az" else
                "Send payment photo:",
                reply_markup=types.ReplyKeyboardRemove()
            )
            return
    
    await message.answer(
        "Выберите билет из списка:" if lang == "ru" else
        "Siyahıdan bilet seçin:" if lang == "az" else
        "Select ticket from the list:",
        reply_markup=get_ticket_keyboard(lang)
    )

# --- RUN ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
