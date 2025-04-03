import os
import random
import string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- CONFIGURATION ---
TOKEN = "7883966462:AAG2udLydnyXDibLWyw8WrlVntzUB-KMXfE"  # Your Telegram bot token
ADMIN_ID = 1291104906  # Your Telegram user ID
PORT = 10001  # Your specified port

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- STATES ---
class Form(StatesGroup):
    lang = State()
    name = State()
    phone = State()
    ticket = State()
    photo = State()

# --- TICKET DATA ---
TICKETS = {
    'ru': {
        'standard': ('Стандарт (20 АЗН)', 'Коктейли, Fan Zone'),
        'vip_single': ('VIP (40 АЗН)', 'Место + коктейль'),
        'vip_table': ('VIP Столик (160 АЗН)', 'Стол на 4'),
        'exclusive_single': ('Exclusive (60 АЗН)', 'Доступ к DJ'),
        'exclusive_table': ('Exclusive (240 АЗН)', 'VIP зона + стол') 
    },
    'az': {
        'standard': ('Standart (20 AZN)', 'Kokteyllər, Fan Zone'),
        'vip_single': ('VIP (40 AZN)', 'Oturacaq + kokteyl'),
        'vip_table': ('VIP Masa (160 AZN)', '4 nəfərlik masa'),
        'exclusive_single': ('Exclusive (60 AZN)', 'DJ girişi'),
        'exclusive_table': ('Exclusive (240 AZN)', 'VIP zona + masa')
    },
    'en': {
        'standard': ('Standard (20 AZN)', 'Cocktails, Fan Zone'),
        'vip_single': ('VIP (40 AZN)', 'Seat + cocktail'),
        'vip_table': ('VIP Table (160 AZN)', 'Table for 4'),
        'exclusive_single': ('Exclusive (60 AZN)', 'DJ access'),
        'exclusive_table': ('Exclusive (240 AZN)', 'VIP area + table')
    }
}

# --- UTILITIES ---
def generate_ticket_number():
    return f"TKT-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"

def get_lang_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🇷🇺 Русский")],
            [types.KeyboardButton(text="🇦🇿 Azərbaycan")],
            [types.KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True
    )

# --- HANDLERS ---
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.set_state(Form.lang)
    await message.answer("Выберите язык / Dil seçin / Select language:", 
                        reply_markup=get_lang_keyboard())

@dp.message(Form.lang)
async def set_language(message: types.Message, state: FSMContext):
    if message.text not in ["🇷🇺 Русский", "🇦🇿 Azərbaycan", "🇬🇧 English"]:
        return await message.answer("Пожалуйста, выберите язык из предложенных")
    
    lang = "ru" if "🇷🇺" in message.text else "az" if "🇦🇿" in message.text else "en"
    await state.update_data(lang=lang)
    await state.set_state(Form.name)
    await message.answer(
        "Введите ваше имя и фамилию:" if lang == "ru" else
        "Ad və soyadınızı daxil edin:" if lang == "az" else
        "Enter your full name:",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    if len(message.text.split()) < 2:
        data = await state.get_data()
        lang = data.get('lang', 'en')
        return await message.answer(
            "Введите имя и фамилию полностью:" if lang == "ru" else
            "Ad və soyadınızı tam daxil edin:" if lang == "az" else
            "Please enter full name:"
        )
    
    await state.update_data(name=message.text)
    await state.set_state(Form.phone)
    data = await state.get_data()
    lang = data.get('lang', 'en')
    await message.answer(
        "Введите ваш номер телефона:" if lang == "ru" else
        "Telefon nömrənizi daxil edin:" if lang == "az" else
        "Enter your phone number:"
    )

@dp.message(Form.phone)
async def process_phone(message: types.Message, state: FSMContext):
    if not message.text.replace('+', '').isdigit():
        data = await state.get_data()
        lang = data.get('lang', 'en')
        return await message.answer(
            "Неверный номер телефона. Попробуйте снова:" if lang == "ru" else
            "Yanlış telefon nömrəsi. Yenidən cəhd edin:" if lang == "az" else
            "Invalid phone number. Try again:"
        )
    
    await state.update_data(phone=message.text)
    data = await state.get_data()
    lang = data.get('lang', 'en')
    
    buttons = [[types.KeyboardButton(text=ticket[0])] for ticket in TICKETS[lang].values()]
    await message.answer(
        "Выберите билет:" if lang == "ru" else "Bilet seçin:" if lang == "az" else "Select ticket:",
        reply_markup=types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    )
    await state.set_state(Form.ticket)

@dp.message(Form.ticket)
async def process_ticket(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'en')
    
    # Find selected ticket
    selected = None
    for ticket_type, (name, desc) in TICKETS[lang].items():
        if name in message.text:
            selected = (ticket_type, name, desc)
            break
    
    if not selected:
        buttons = [[types.KeyboardButton(text=ticket[0])] for ticket in TICKETS[lang].values()]
        return await message.answer(
            "Пожалуйста, выберите билет из списка:" if lang == "ru" else
            "Zəhmət olmasa siyahıdan bilet seçin:" if lang == "az" else
            "Please select ticket from the list:",
            reply_markup=types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
        )
    
    ticket_number = generate_ticket_number()
    await state.update_data(ticket_type=selected[0], ticket_name=selected[1], ticket_number=ticket_number)
    
    await message.answer(
        f"🎫 {selected[1]}\n"
        f"📝 {selected[2]}\n\n"
        f"🔢 Номер билета: {ticket_number}\n"
        "📸 Отправьте фото оплаты:" if lang == "ru" else
        f"🎫 {selected[1]}\n"
        f"📝 {selected[2]}\n\n"
        f"🔢 Bilet nömrəsi: {ticket_number}\n"
        "📸 Ödəniş şəklini göndərin:" if lang == "az" else
        f"🎫 {selected[1]}\n"
        f"📝 {selected[2]}\n\n"
        f"🔢 Ticket number: {ticket_number}\n"
        "📸 Send payment photo:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Form.photo)

@dp.message(Form.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'en')
    ticket_number = data.get('ticket_number', 'UNKNOWN')
    
    # Send confirmation to user
    await message.answer(
        f"✅ Билет {ticket_number} подтвержден!\n"
        "❗️ Билеты не подлежат возврату" if lang == "ru" else
        f"✅ Bilet {ticket_number} təsdiqləndi!\n"
        "❗️ Biletlər geri qaytarılmır" if lang == "az" else
        f"✅ Ticket {ticket_number} confirmed!\n"
        "❗️ Tickets are non-refundable"
    )
    
    # Notify admin
    await bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=(
            f"🎫 Новый билет: {ticket_number}\n"
            f"👤 {data.get('name')}\n"
            f"📞 {data.get('phone')}\n"
            f"💵 {data.get('ticket_name')}"
        )
    )
    
    await state.clear()

# --- ADMIN COMMANDS ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Доступ запрещен")
    
    await message.answer(
        "Панель администратора",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="/stats")]
            ],
            resize_keyboard=True
        )
    )

@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Статистика будет отображаться здесь")

# --- RUN THE BOT ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
