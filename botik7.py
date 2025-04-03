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
from aiohttp import web
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ===== CONFIGURATION =====
TOKEN = os.getenv('7501232713:AAEQG8REnPf83FqVkVqus-ZnJBKDnSt9Qvo')  # Get from environment variable
ADMIN_ID = int(os.getenv('ADMIN_ID', '1291104906'))  # Fallback to your ID if not set
PAYMENT_CARD = os.getenv("4169 7388 9268 3164")  # Get from environment variable
PORT = int(os.getenv('PORT', '10001'))  # Fallback to 10001 if not set

# Initialize bot
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ===== WEB SERVER =====
async def health_check(request):
    return web.Response(text="Bot is running")

async def run_web_app():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app, reuse_address=True)  # Critical for Render
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Server running on port {PORT}")

# ===== DATA STORAGE =====
pending_orders = {}  # Stores orders awaiting approval
completed_orders = {}  # Stores approved orders

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
    """Generate 8-character alphanumeric order code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_lang_keyboard():
    """Language selection keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский")],
            [KeyboardButton(text="🇦🇿 Azərbaycan")],
            [KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True
    )

def get_ticket_keyboard(lang):
    """Ticket selection keyboard for specific language"""
    buttons = [[KeyboardButton(text=TICKETS[lang][t][0])] for t in TICKETS[lang]]
    buttons.append([KeyboardButton(
        text="⬅️ Назад" if lang == "ru" else "⬅️ Geri" if lang == "az" else "⬅️ Back"
    )])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ===== HANDLERS =====
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    """Start command handler"""
    await state.clear()
    await state.set_state(Form.lang)
    await message.answer(
        "Выберите язык / Dil seçin / Select language:",
        reply_markup=get_lang_keyboard()
    )

@dp.message(Form.lang)
async def set_language(message: types.Message, state: FSMContext):
    """Language selection handler"""
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

@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    """Name input handler"""
    if len(message.text.split()) < 2:
        data = await state.get_data()
        lang = data.get('lang', 'en')
        return await message.answer(
            "Пожалуйста, введите имя и фамилию:" if lang == "ru" else
            "Zəhmət olmasa ad və soyadınızı daxil edin:" if lang == "az" else
            "Please enter both first and last name:"
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
    """Phone number input handler"""
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
    await message.answer(
        "Выберите билет:" if lang == "ru" else "Bilet seçin:" if lang == "az" else "Select ticket:",
        reply_markup=get_ticket_keyboard(lang)
    )
    await state.set_state(Form.ticket)

@dp.message(Form.ticket)
async def process_ticket(message: types.Message, state: FSMContext):
    """Ticket selection handler"""
    data = await state.get_data()
    lang = data.get('lang', 'en')
    
    # Find selected ticket
    selected = None
    for ticket_type, (name, desc) in TICKETS[lang].items():
        if name in message.text:
            selected = (ticket_type, name, desc)
            break
    
    if not selected:
        buttons = [[KeyboardButton(text=ticket[0])] for ticket in TICKETS[lang].values()]
        return await message.answer(
            "Пожалуйста, выберите билет из списка:" if lang == "ru" else
            "Zəhmət olmasa siyahıdan bilet seçin:" if lang == "az" else
            "Please select ticket from the list:",
            reply_markup=types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
        )
    
    order_code = generate_order_code()
    await state.update_data(
        ticket_type=selected[0],
        ticket_name=selected[1],
        order_code=order_code
    )
    
    # Payment instructions
    await message.answer(
        f"💳 Оплатите {selected[1]} на карту:\n"
        f"<code>{PAYMENT_CARD}</code>\n\n"
        "📸 Отправьте скриншот оплаты:" if lang == "ru" else
        f"💳 {selected[1]} kartına köçürün:\n"
        f"<code>{PAYMENT_CARD}</code>\n\n"
        "📸 Ödəniş skrinşotu göndərin:" if lang == "az" else
        f"💳 Pay {selected[1]} to card:\n"
        f"<code>{PAYMENT_CARD}</code>\n\n"
        "📸 Send payment screenshot:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Form.photo)

@dp.message(Form.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    """Photo upload handler"""
    data = await state.get_data()
    lang = data.get('lang', 'en')
    order_code = data.get('order_code', 'UNKNOWN')
    
    # Save order for admin approval
    pending_orders[order_code] = {
        "user_id": message.from_user.id,
        "data": data,
        "photo_id": message.photo[-1].file_id,
        "lang": lang
    }
    
    # Notify admin
    admin_msg = await bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=(
            f"🆔 Код: <code>{order_code}</code>\n"
            f"👤 {data['name']}\n"
            f"📞 {data['phone']}\n"
            f"🎟 {data['ticket_name']}\n\n"
            "Ответьте на это сообщение:\n"
            "/approve - подтвердить\n"
            "/reject [причина] - отклонить"
        )
    )
    
    # Save admin message ID for replies
    pending_orders[order_code]["admin_msg_id"] = admin_msg.message_id
    
    await message.answer(
        f"✅ Заявка #{order_code} отправлена на проверку!\n"
        "Ожидайте подтверждения." if lang == "ru" else
        f"✅ #{order_code} müraciəti yoxlanılır!\n"
        "Təsdiq gözləyin." if lang == "az" else
        f"✅ Application #{order_code} submitted!\n"
        "Awaiting approval."
    )
    await state.clear()

# ===== ADMIN COMMANDS =====
@dp.message(Command("approve"))
async def approve_order(message: types.Message):
    """Approve order command"""
    if message.from_user.id != ADMIN_ID or not message.reply_to_message:
        return
    
    # Extract order code from replied message
    try:
        order_code = message.reply_to_message.caption.split("\n")[0].split()[-1]
    except (AttributeError, IndexError):
        return await message.answer("⚠️ Неверный формат сообщения")
    
    if order_code not in pending_orders:
        return await message.answer("⚠️ Заявка не найдена")
    
    order = pending_orders.pop(order_code)
    completed_orders[order_code] = order
    lang = order['lang']
    ticket_name = order['data']['ticket_name']
    
    # Notify user
    await bot.send_message(
        order['user_id'],
        f"🎉 Ваш билет подтвержден!\n"
        f"🔢 Номер: <code>{order_code}</code>\n"
        f"🎫 {ticket_name}\n\n"
        "❗️ Билеты не подлежат возврату" if lang == "ru" else
        f"🎉 Biletiniz təsdiqləndi!\n"
        f"🔢 Nömrə: <code>{order_code}</code>\n"
        f"🎫 {ticket_name}\n\n"
        "❗️ Biletlər geri qaytarılmır" if lang == "az" else
        f"🎉 Your ticket confirmed!\n"
        f"🔢 Number: <code>{order_code}</code>\n"
        f"🎫 {ticket_name}\n\n"
        "❗️ Tickets are non-refundable"
    )
    
    await message.answer(f"✅ Заявка {order_code} подтверждена")

@dp.message(Command("reject"))
async def reject_order(message: types.Message):
    """Reject order command"""
    if message.from_user.id != ADMIN_ID or not message.reply_to_message:
        return
    
    # Extract order code from replied message
    try:
        order_code = message.reply_to_message.caption.split("\n")[0].split()[-1]
    except (AttributeError, IndexError):
        return await message.answer("⚠️ Неверный формат сообщения")
    
    if order_code not in pending_orders:
        return await message.answer("⚠️ Заявка не найдена")
    
    reason = " ".join(message.text.split()[1:]) or "не указана"
    order = pending_orders.pop(order_code)
    lang = order['lang']
    
    # Notify user
    await bot.send_message(
        order['user_id'],
        f"❌ Заявка отклонена\n"
        f"Причина: {reason}\n\n"
        "Попробуйте оформить заявку снова" if lang == "ru" else
        f"❌ Müraciət rədd edildi\n"
        f"Səbəb: {reason}\n\n"
        "Yenidən müraciət edin" if lang == "az" else
        f"❌ Application rejected\n"
        f"Reason: {reason}\n\n"
        "Please try again",
        reply_markup=get_lang_keyboard()
    )
    
    await message.answer(f"❌ Заявка {order_code} отклонена")

# ===== RUN BOT =====
async def main():
    # Start web server first
    await run_web_app()
    
    # Then start bot
    print("🤖 Bot starting...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
