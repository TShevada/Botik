import os
import random
import string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Конфигурация
TOKEN = "7883966462:AAG2udLydnyXDibLWyw8WrlVntzUB-KMXfE"
ADMIN_ID = 1291104906
PAYMENT_CARD = "4169 7388 9268 3164"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранение заявок
pending_orders = {}
completed_orders = {}

# Состояния
class Form(StatesGroup):
    lang = State()
    name = State()
    phone = State()
    ticket = State()
    photo = State()

# Данные билетов
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

# Генерация кода билета
def generate_order_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Клавиатуры
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

# Обработчики
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.set_state(Form.lang)
    await message.answer("Выберите язык / Dil seçin / Select language:", 
                        reply_markup=get_lang_keyboard())

@dp.message(Form.lang)
async def set_lang(message: types.Message, state: FSMContext):
    lang = "ru" if "🇷🇺" in message.text else "az" if "🇦🇿" in message.text else "en"
    await state.update_data(lang=lang)
    await state.set_state(Form.name)
    await message.answer(
        "Введите имя и фамилию:" if lang == "ru" else 
        "Ad və soyadınızı daxil edin:" if lang == "az" else 
        "Enter your full name:",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Form.phone)
    data = await state.get_data()
    lang = data['lang']
    await message.answer(
        "Введите номер телефона:" if lang == "ru" else
        "Telefon nömrənizi daxil edin:" if lang == "az" else
        "Enter phone number:"
    )

@dp.message(Form.phone)
async def process_phone(message: types.Message, state: FSMContext):
    if not message.text.replace('+', '').isdigit():
        data = await state.get_data()
        lang = data['lang']
        await message.answer(
            "Неверный номер. Попробуйте снова:" if lang == "ru" else
            "Yanlış nömrə. Yenidən cəhd edin:" if lang == "az" else
            "Invalid number. Try again:"
        )
        return
    
    await state.update_data(phone=message.text)
    data = await state.get_data()
    await message.answer(
        "Выберите билет:" if data['lang'] == "ru" else 
        "Bilet seçin:" if data['lang'] == "az" else 
        "Select ticket:",
        reply_markup=get_ticket_keyboard(data['lang'])
    )
    await state.set_state(Form.ticket)

@dp.message(Form.ticket)
async def process_ticket(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data['lang']
    
    # Поиск выбранного билета
    selected = None
    for ticket_type in TICKETS[lang]:
        if TICKETS[lang][ticket_type][0] in message.text:
            selected = ticket_type
            break
    
    if not selected:
        await message.answer(
            "Выберите билет из списка:" if lang == "ru" else
            "Siyahıdan bilet seçin:" if lang == "az" else
            "Select ticket from list:",
            reply_markup=get_ticket_keyboard(lang)
        )
        return
    
    order_code = generate_order_code()
    await state.update_data(ticket_type=selected, order_code=order_code)
    
    # Инструкция по оплате
    await message.answer(
        f"💳 Оплатите {TICKETS[lang][selected][0]} на карту:\n"
        f"<code>{PAYMENT_CARD}</code>\n\n"
        "📸 Отправьте скриншот оплаты:" if lang == "ru" else
        f"💳 {TICKETS[lang][selected][0]} kartına köçürün:\n"
        f"<code>{PAYMENT_CARD}</code>\n\n"
        "📸 Ödəniş skrinşotu göndərin:" if lang == "az" else
        f"💳 Pay {TICKETS[lang][selected][0]} to card:\n"
        f"<code>{PAYMENT_CARD}</code>\n\n"
        "📸 Send payment screenshot:",
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Form.photo)

@dp.message(Form.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data['lang']
    order_code = data['order_code']
    
    # Сохраняем заявку
    pending_orders[order_code] = {
        "user_id": message.from_user.id,
        "data": data,
        "photo_id": message.photo[-1].file_id
    }
    
    # Уведомление админу
    admin_msg = await bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=(
            f"🆔 Код: <code>{order_code}</code>\n"
            f"👤 {data['name']}\n"
            f"📞 {data['phone']}\n"
            f"🎟 {TICKETS[lang][data['ticket_type']][0]}\n\n"
            "Ответьте на это сообщение:\n"
            "/approve - подтвердить\n"
            "/reject [причина] - отклонить"
        ),
        parse_mode="HTML"
    )
    
    # Сохраняем ID сообщения для ответа
    pending_orders[order_code]["admin_msg_id"] = admin_msg.message_id
    
    await message.answer(
        f"✅ Заявка #{order_code} отправлена на проверку!\n"
        "Ожидайте подтверждения." if lang == "ru" else
        f"✅ #{order_code} müraciəti yoxlanılır!\n"
        "Təsdiq gözləyin." if lang == "az" else
        f"✅ Application #{order_code} submitted!\n"
        "Awaiting approval.",
        reply_markup=get_lang_keyboard()
    )
    await state.clear()

# Админ-команды
@dp.message(Command("approve"))
async def approve_order(message: types.Message):
    if message.from_user.id != ADMIN_ID or not message.reply_to_message:
        return
    
    order_code = message.reply_to_message.caption.split("\n")[0].split()[-1]
    if order_code not in pending_orders:
        return await message.answer("⚠️ Заявка не найдена")
    
    order = pending_orders.pop(order_code)
    completed_orders[order_code] = order
    
    # Уведомление пользователю
    lang = order['data']['lang']
    ticket_name = TICKETS[lang][order['data']['ticket_type']][0]
    
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
        "❗️ Tickets are non-refundable",
        parse_mode="HTML"
    )
    
    await message.answer(f"✅ Заявка {order_code} подтверждена")

@dp.message(Command("reject"))
async def reject_order(message: types.Message):
    if message.from_user.id != ADMIN_ID or not message.reply_to_message:
        return
    
    order_code = message.reply_to_message.caption.split("\n")[0].split()[-1]
    if order_code not in pending_orders:
        return await message.answer("⚠️ Заявка не найдена")
    
    reason = " ".join(message.text.split()[1:]) or "не указана"
    order = pending_orders.pop(order_code)
    
    # Уведомление пользователю
    lang = order['data']['lang']
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

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
