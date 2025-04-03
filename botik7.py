import os
import random
import string
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from collections import defaultdict

# --- Configuration ---
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Set in Render environment
ADMIN_ID = 1291104906  # Your Telegram ID
PAYMENT_CARD = "4169 7388 9268 3164"  # Your payment card
PHOTOS_DIR = "payment_screenshots"

# --- Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
os.makedirs(PHOTOS_DIR, exist_ok=True)

bot = Bot(token=TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher()

# --- Storage ---
user_data = {}
pending_approvals = {}

# --- Ticket Data with Both Exclusive Types ---
TICKETS = {
    'standard': {
        'ru': ('Стандарт (20 AZN)', '• Приветственные коктейли\n• Fan Zone'),
        'az': ('Standart (20 AZN)', '• Salam kokteylləri\n• Fan Zone'),
        'en': ('Standard (20 AZN)', '• Welcome cocktails\n• Fan Zone')
    },
    'vip_single': {
        'ru': ('VIP (40 AZN)', '• Индивидуальное место\n• Приветственный коктейль'),
        'az': ('VIP (40 AZN)', '• Fərdi yer\n• Salam kokteyli'),
        'en': ('VIP (40 AZN)', '• Individual seat\n• Welcome cocktail')
    },
    'vip_table': {
        'ru': ('VIP Столик (160 AZN)', '• Столик на 4 человек\n• 4 коктейля'),
        'az': ('VIP Masa (160 AZN)', '• 4 nəfərlik masa\n• 4 kokteyl'),
        'en': ('VIP Table (160 AZN)', '• Table for 4\n• 4 cocktails')
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

# --- Helper Functions ---
def generate_order_code():
    """Creates unique 8-character alphanumeric codes"""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=8))
        if code not in pending_approvals:  # Ensure uniqueness
            return code

def get_lang_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇦🇿 Azərbaycan")],
            [KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True
    )

def get_ticket_keyboard(lang):
    buttons = [[KeyboardButton(text=TICKETS[t][lang][0])] for t in TICKETS]
    buttons.append([KeyboardButton(
        text="⬅️ Назад" if lang == "ru" else "⬅️ Geri" if lang == "az" else "⬅️ Back"
    )])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📝 Последние заявки", callback_data="admin_orders")]
    ])

# --- Handlers ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Выберите язык / Dil seçin / Select language:",
        reply_markup=get_lang_keyboard()
    )

@dp.message(F.text.in_(["🇷🇺 Русский", "🇦🇿 Azərbaycan", "🇬🇧 English"]))
async def set_language(message: types.Message):
    lang = "ru" if "🇷🇺" in message.text else "az" if "🇦🇿" in message.text else "en"
    user_data[message.from_user.id] = {"lang": lang, "step": "name"}
    
    await message.answer(
        "Введите ваше имя и фамилию:" if lang == "ru" else
        "Ad və soyadınızı daxil edin:" if lang == "az" else
        "Enter your full name:",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(lambda m: user_data.get(m.from_user.id, {}).get("step") == "name")
async def process_name(message: types.Message):
    if len(message.text.split()) < 2:
        lang = user_data[message.from_user.id]["lang"]
        await message.answer(
            "Пожалуйста, введите имя и фамилию:" if lang == "ru" else
            "Ad və soyadınızı daxil edin:" if lang == "az" else
            "Please enter both first and last name:"
        )
        return
    
    user_data[message.from_user.id].update({
        "name": message.text,
        "step": "phone"
    })
    
    lang = user_data[message.from_user.id]["lang"]
    await message.answer(
        "Введите ваш номер телефона:" if lang == "ru" else
        "Telefon nömrənizi daxil edin:" if lang == "az" else
        "Enter your phone number:"
    )

@dp.message(lambda m: user_data.get(m.from_user.id, {}).get("step") == "phone")
async def process_phone(message: types.Message):
    if not message.text.replace('+', '').isdigit():
        lang = user_data[message.from_user.id]["lang"]
        await message.answer(
            "Неверный номер телефона. Попробуйте снова:" if lang == "ru" else
            "Yanlış telefon nömrəsi. Yenidən cəhd edin:" if lang == "az" else
            "Invalid phone number. Try again:"
        )
        return
    
    user_data[message.from_user.id].update({
        "phone": message.text,
        "step": "ticket"
    })
    
    lang = user_data[message.from_user.id]["lang"]
    await message.answer(
        "Выберите билет:" if lang == "ru" else "Bilet seçin:" if lang == "az" else "Select ticket:",
        reply_markup=get_ticket_keyboard(lang)
    )

@dp.message(F.text.in_([TICKETS[t][lang][0] for t in TICKETS for lang in ['ru', 'az', 'en']]))
async def process_ticket(message: types.Message):
    user_id = message.from_user.id
    lang = user_data[user_id]["lang"]
    
    # Find selected ticket
    for ticket_type in TICKETS:
        if TICKETS[ticket_type][lang][0] in message.text:
            user_data[user_id].update({
                "ticket_type": ticket_type,
                "ticket_name": TICKETS[ticket_type][lang][0],
                "step": "payment"
            })
            break
    
    # Payment instructions
    await message.answer(
        f"💳 Оплатите {user_data[user_id]['ticket_name']} на карту:\n"
        f"<code>{PAYMENT_CARD}</code>\n\n"
        "📸 Отправьте скриншот оплаты:" if lang == "ru" else
        f"💳 {user_data[user_id]['ticket_name']} kartına köçürün:\n"
        f"<code>{PAYMENT_CARD}</code>\n\n"
        "📸 Ödəniş skrinşotu göndərin:" if lang == "az" else
        f"💳 Pay {user_data[user_id]['ticket_name']} to card:\n"
        f"<code>{PAYMENT_CARD}</code>\n\n"
        "📸 Send payment screenshot:",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(F.photo, lambda m: user_data.get(m.from_user.id, {}).get("step") == "payment")
async def process_payment(message: types.Message):
    user_id = message.from_user.id
    user_info = user_data[user_id]
    lang = user_info["lang"]
    
    # Generate unique order code
    order_code = generate_order_code()
    
    # Save payment photo
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    photo_path = f"{PHOTOS_DIR}/{order_code}.jpg"
    await bot.download_file(file.file_path, photo_path)
    
    # Store order with all details
    pending_approvals[order_code] = {
        "user_id": user_id,
        "name": user_info["name"],
        "phone": user_info["phone"],
        "ticket_type": user_info["ticket_type"],
        "ticket_name": user_info["ticket_name"],
        "photo_path": photo_path,
        "lang": lang,
        "approved": None
    }
    
    # Notify admin
    admin_text = (
        f"🆔 *Новая заявка*: `{order_code}`\n"
        f"👤 {user_info['name']}\n"
        f"📞 {user_info['phone']}\n"
        f"🎟 {user_info['ticket_name']}\n\n"
        f"💬 Ответьте командой:\n"
        f"/approve - подтвердить\n"
        f"/reject [причина] - отклонить"
    )
    
    await bot.send_photo(
        ADMIN_ID,
        photo.file_id,
        caption=admin_text
    )
    
    # Confirm to user
    user_text = {
        "ru": f"✅ Заявка #{order_code} отправлена!\nОжидайте подтверждения.",
        "az": f"✅ #{order_code} müraciəti göndərildi!\nTəsdiq gözləyin.",
        "en": f"✅ Order #{order_code} submitted!\nAwaiting approval."
    }[lang]
    
    await message.answer(user_text)
    del user_data[user_id]

# --- Admin Commands ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    stats_text = (
        f"📊 *Статистика заявок*\n\n"
        f"• Всего: {len(pending_approvals)}\n"
        f"• На рассмотрении: {len([x for x in pending_approvals.values() if x['approved'] is None])}\n"
        f"• Подтверждено: {len([x for x in pending_approvals.values() if x['approved'] is True])}\n"
        f"• Отклонено: {len([x for x in pending_approvals.values() if x['approved'] is False])}"
    )
    
    await message.answer(stats_text, reply_markup=get_admin_keyboard())

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    stats_text = (
        f"📊 *Статистика заявок*\n\n"
        f"• Всего: {len(pending_approvals)}\n"
        f"• На рассмотрении: {len([x for x in pending_approvals.values() if x['approved'] is None])}\n"
        f"• Подтверждено: {len([x for x in pending_approvals.values() if x['approved'] is True])}\n"
        f"• Отклонено: {len([x for x in pending_approvals.values() if x['approved'] is False])}"
    )
    
    await callback.message.edit_text(stats_text, reply_markup=get_admin_keyboard())

@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    pending = [x for x in pending_approvals.items() if x[1]['approved'] is None][:5]
    
    if not pending:
        await callback.answer("Нет заявок на рассмотрении")
        return
    
    orders_text = "📝 *Последние заявки:*\n\n"
    for code, data in pending:
        orders_text += (
            f"🆔 Код: `{code}`\n"
            f"👤 {data['name']}\n"
            f"📞 {data['phone']}\n"
            f"🎟 {data['ticket_name']}\n"
            "━━━━━━━━━━━━━━\n"
        )
    
    await callback.message.edit_text(orders_text, reply_markup=get_admin_keyboard())

@dp.message(Command("approve"))
async def approve_order(message: types.Message):
    if message.from_user.id != ADMIN_ID or not message.reply_to_message:
        return
    
    try:
        order_code = message.reply_to_message.caption.split("`")[1]
        order = pending_approvals.get(order_code)
        
        if not order:
            await message.answer("⚠️ Заявка не найдена")
            return
            
        # Mark as approved
        order["approved"] = True
        
        # Notify user
        lang = order["lang"]
        confirm_text = {
            "ru": (
                f"🎉 Ваш билет подтвержден!\n"
                f"🔢 Номер: `{order_code}`\n"
                f"🎫 {order['ticket_name']}\n\n"
                f"❗️ Билеты не подлежат возврату"
            ),
            "az": (
                f"🎉 Biletiniz təsdiqləndi!\n"
                f"🔢 Nömrə: `{order_code}`\n"
                f"🎫 {order['ticket_name']}\n\n"
                f"❗️ Biletlər geri qaytarılmır"
            ),
            "en": (
                f"🎉 Ticket confirmed!\n"
                f"🔢 Number: `{order_code}`\n"
                f"🎫 {order['ticket_name']}\n\n"
                f"❗️ Non-refundable"
            )
        }[lang]
        
        await bot.send_message(order["user_id"], confirm_text)
        await message.answer(f"✅ Заявка {order_code} подтверждена")
        
    except Exception as e:
        logger.error(f"Approve error: {e}")
        await message.answer("❌ Ошибка подтверждения")

@dp.message(Command("reject"))
async def reject_order(message: types.Message):
    if message.from_user.id != ADMIN_ID or not message.reply_to_message:
        return
    
    try:
        order_code = message.reply_to_message.caption.split("`")[1]
        order = pending_approvals.get(order_code)
        
        if not order:
            await message.answer("⚠️ Заявка не найдена")
            return
            
        reason = " ".join(message.text.split()[1:]) or "не указана"
        
        # Mark as rejected
        order["approved"] = False
        
        # Notify user
        lang = order["lang"]
        reject_text = {
            "ru": (
                f"❌ Заявка отклонена\n"
                f"Причина: {reason}\n\n"
                f"Попробуйте оформить заново"
            ),
            "az": (
                f"❌ Müraciət rədd edildi\n"
                f"Səbəb: {reason}\n\n"
                f"Yenidən sifariş verin"
            ),
            "en": (
                f"❌ Application rejected\n"
                f"Reason: {reason}\n\n"
                f"Please try again"
            )
        }[lang]
        
        await bot.send_message(
            order["user_id"],
            reject_text,
            reply_markup=get_lang_keyboard()
        )
        await message.answer(f"❌ Заявка {order_code} отклонена")
        
    except Exception as e:
        logger.error(f"Reject error: {e}")
        await message.answer("❌ Ошибка отклонения")

# --- Main ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.info("Starting bot...")
    asyncio.run(main())
