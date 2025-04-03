import os
import random
import string
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ===== CONFIGURATION =====
TOKEN = "7883966462:AAG2udLydnyXDibLWyw8WrlVntzUB-KMXfE"  # Your bot token
ADMIN_ID = 1291104906  # Your Telegram ID
PAYMENT_CARD = "4169 7388 9268 3164"  # Your payment card

# Initialize bot
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ===== DATA STORAGE =====
pending_orders = {} 
completed_orders = {}

# ===== STATES =====
class Form(StatesGroup):
    lang = State()
    name = State()
    phone = State()
    ticket = State()
    photo = State()

# ===== TICKET DATA ===== 
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

# ===== UTILITIES =====
def generate_order_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_lang_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский")],
            [KeyboardButton(text="🇦🇿 Azərbaycan")],
            [KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True
    )

def get_ticket_keyboard(lang):
    buttons = [[KeyboardButton(text=TICKETS[lang][t][0])] for t in TICKETS[lang]]
    buttons.append([KeyboardButton(
        text="⬅️ Назад" if lang == "ru" else "⬅️ Geri" if lang == "az" else "⬅️ Back"
    )])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ===== HANDLERS ===== 
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(Form.lang)
    await message.answer(
        "Выберите язык / Dil seçin / Select language:",
        reply_markup=get_lang_keyboard()
    )

@dp.message(Form.lang)
async def set_language(message: types.Message, state: FSMContext):
    if message.text not in ["🇷🇺 Русский", "🇦🇿 Azərbaycan", "🇬🇧 English"]:
        return await message.answer("Please select a valid language option")
    
    lang = "ru" if "🇷🇺" in message.text else "az" if "🇦🇿" in message.text else "en"
    await state.update_data(lang=lang)
    await state.set_state(Form.name)
    await message.answer(
        "Введите ваше имя и фамилию:" if lang == "ru" else
        "Ad və soyadınızı daxil edin:" if lang == "az" else
        "Enter your full name:",
        reply_markup=types.ReplyKeyboardRemove()
    )

# [REST OF YOUR HANDLERS REMAIN EXACTLY THE SAME]
# ...

# ===== RUN BOT =====
async def main():
    try:
        print("🤖 Bot starting in polling mode...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Bot failed: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
