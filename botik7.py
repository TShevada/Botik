import os
import logging
import asyncio
import random
import string
from datetime import datetime
from collections import defaultdict
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ===== CONFIGURATION =====
TOKEN = os.getenv("BOT_TOKEN")
YOUR_TELEGRAM_ID = 1291104906
PAYMENT_CARD = "4169 7388 9268 3164"
WELCOME_BANNER = "welcome.jpg"  # Make sure this file exists in your project
# ========================

# Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Storage
user_lang = {}
user_data = {}
pending_approvals = {}
ticket_codes = {}
orders = []
statistics = defaultdict(int)

# Ticket Types
TICKET_TYPES = {
    "standard": {
        "ru": {"name": "Стандарт", "price": "20 AZN"},
        "az": {"name": "Standart", "price": "20 AZN"}, 
        "en": {"name": "Standard", "price": "20 AZN"}
    },
    "vip_single": {
        "ru": {"name": "VIP Одиночный", "price": "40 AZN"},
        "az": {"name": "VIP Tək", "price": "40 AZN"},
        "en": {"name": "VIP Single", "price": "40 AZN"}
    },
    "vip_table": {
        "ru": {"name": "VIP Столик", "price": "160 AZN"},
        "az": {"name": "VIP Masalıq", "price": "160 AZN"},
        "en": {"name": "VIP Table", "price": "160 AZN"}
    },
    "exclusive_table": {
        "ru": {"name": "Exclusive Столик", "price": "240 AZN"},
        "az": {"name": "Exclusive Masalıq", "price": "240 AZN"},
        "en": {"name": "Exclusive Table", "price": "240 AZN"}
    }
}

# Helper Functions
def generate_ticket_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_lang_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇦🇿 Azərbaycan")],
            [KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True
    )

def get_menu_keyboard(lang):
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎫 Билеты" if lang == "ru" else "🎫 Biletlər" if lang == "az" else "🎫 Tickets"),
                KeyboardButton(text="📅 Ближайшие события" if lang == "ru" else "📅 Yaxın tədbirlər" if lang == "az" else "📅 Upcoming events")
            ],
            [
                KeyboardButton(text="📞 Контакты" if lang == "ru" else "📞 Əlaqə" if lang == "az" else "📞 Contacts"),
                KeyboardButton(text="🌐 Сменить язык" if lang == "ru" else "🌐 Dil dəyiş" if lang == "az" else "🌐 Change language")
            ]
        ],
        resize_keyboard=True
    )

def get_ticket_type_keyboard(lang):
    buttons = []
    for ticket_type, names in TICKET_TYPES.items():
        name = names[lang]["name"]
        price = names[lang]["price"]
        buttons.append([KeyboardButton(text=f"{name} ({price})")])
    
    back_text = "⬅️ Назад" if lang == "ru" else "⬅️ Geri" if lang == "az" else "⬅️ Back"
    buttons.append([KeyboardButton(text=back_text)])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📝 Последние заявки", callback_data="admin_orders")],
        [InlineKeyboardButton(text="⏳ Ожидающие", callback_data="admin_pending")]
    ])

async def notify_admin(user_id: int, name: str, phone: str, ticket_type: str):
    try:
        ticket_name = TICKET_TYPES[ticket_type]["ru"]["name"]
        await bot.send_message(
            YOUR_TELEGRAM_ID,
            f"🆕 Новая заявка:\n\n"
            f"👤 ID: {user_id}\n"
            f"📛 Имя: {name}\n"
            f"📱 Телефон: {phone}\n"
            f"🎫 Тип: {ticket_name}\n\n"
            f"Ответьте:\n"
            f"/accept_{user_id} - подтвердить\n"
            f"/reject_{user_id} - отклонить"
        )
    except Exception as e:
        logger.error(f"Admin notify error: {e}")

# ================= HANDLERS =================

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    try:
        if os.path.exists(WELCOME_BANNER):
            await message.answer_photo(types.InputFile(WELCOME_BANNER))
    except Exception as e:
        logger.error(f"Banner error: {e}")
    await message.answer("Выберите язык / Select language / Dil seçin:", reply_markup=get_lang_keyboard())

@dp.message(F.text.in_(["🇷🇺 Русский", "🇦🇿 Azərbaycan", "🇬🇧 English"]))
async def set_language(message: types.Message):
    lang_map = {
        "🇷🇺 Русский": "ru",
        "🇦🇿 Azərbaycan": "az",
        "🇬🇧 English": "en"
    }
    user_lang[message.from_user.id] = lang_map[message.text]
    
    confirmation = {
        "ru": "Язык установлен: Русский",
        "az": "Dil seçildi: Azərbaycan",
        "en": "Language set: English"
    }[lang_map[message.text]]
    
    await message.answer(confirmation, reply_markup=get_menu_keyboard(lang_map[message.text]))

@dp.message(F.text.in_(["📅 Ближайшие события", "📅 Yaxın tədbirlər", "📅 Upcoming events"]))
async def events_handler(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    events_info = {
        "ru": "Текущий ивент: Afro-Party в Voodoo!\n"
              "📅 Дата: 27 апреля 2025\n"
              "🕒 Время: 18:00 - 00:00\n"
              "📍 Место: Рестобар Voodoo, ТРЦ Наргиз Молл, 3 этаж",
        "az": "Cari tədbir: Afro-Party Voodoo-da!\n"
              "📅 Tarix: 27 Aprel 2025\n"
              "🕒 Vaxt: 18:00 - 00:00\n"
              "📍 Yer: Voodoo Restobar, Nargiz Mall, 3-cü mərtəbə",
        "en": "Current event: Afro-Party at Voodoo!\n"
              "📅 Date: April 27, 2025\n"
              "🕒 Time: 6:00 PM - 12:00 AM\n"
              "📍 Location: Voodoo Restobar, Nargiz Mall, 3rd floor"
    }[lang]
    await message.answer(events_info, reply_markup=get_menu_keyboard(lang))

@dp.message(F.text.in_(["📞 Контакты", "📞 Əlaqə", "📞 Contacts"]))
async def contacts_handler(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    contact_info = {
        "ru": "📞 Контакты:\nТелефон: +994 10 531 24 06",
        "az": "📞 Əlaqə:\nTelefon: +994 10 531 24 06",
        "en": "📞 Contacts:\nPhone: +994 10 531 24 06"
    }[lang]
    await message.answer(contact_info, reply_markup=get_menu_keyboard(lang))

@dp.message(F.text.in_(["🌐 Сменить язык", "🌐 Dil dəyiş", "🌐 Change language"]))
async def change_lang_handler(message: types.Message):
    await message.answer(
        "Выберите язык / Select language / Dil seçin:",
        reply_markup=get_lang_keyboard()
    )

@dp.message(F.text.in_(["🎫 Билеты", "🎫 Biletlər", "🎫 Tickets"]))
async def tickets_menu(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    await message.answer(
        "Выберите тип билета:" if lang == "ru" else
        "Bilet növünü seçin:" if lang == "az" else
        "Select ticket type:",
        reply_markup=get_ticket_type_keyboard(lang)
    )
@dp.message(F.text.regexp(r"(Стандарт|Standart|Standard|VIP.*|Exclusive.*)"))
async def select_ticket(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    text = message.text.lower()
    
    if "стандарт" in text or "standart" in text or "standard" in text:
        ticket_type = "standard"
    elif "одиночный" in text or "tək" in text or "single" in text:
        ticket_type = "vip_single"
    elif "столик" in text or "masalıq" in text or "table" in text:
        ticket_type = "vip_table"
    elif "exclusive" in text:
        ticket_type = "exclusive_table"
    else:
        await message.answer("Invalid ticket type")
        return

    user_data[message.from_user.id] = {
        "step": "name",
        "lang": lang,
        "ticket_type": ticket_type,
        "price": TICKET_TYPES[ticket_type][lang]["price"]
    }

    await message.answer(
        "Введите имя и фамилию:" if lang == "ru" else
        "Ad və soyadınızı daxil edin:" if lang == "az" else
        "Enter your full name:",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(lambda m: user_data.get(m.from_user.id, {}).get("step") == "name")
async def get_name(message: types.Message):
    try:
        # First check if we have text content
        if not message.text:
            lang = user_data.get(message.from_user.id, {}).get("lang", "en")
            error_msg = {
                "ru": "Пожалуйста, введите текст",
                "az": "Zəhmət olmasa, mətn daxil edin",
                "en": "Please enter text"
            }[lang]
            await message.answer(error_msg)
            return

        # Then validate name input (at least 2 words for name+surname)
        if len(message.text.split()) < 2:
            lang = user_data[message.from_user.id].get("lang", "en")
            error_msg = {
                "ru": "Пожалуйста, введите имя и фамилию",
                "az": "Zəhmət olmasa, ad və soyadınızı daxil edin",
                "en": "Please enter both first and last name"
            }[lang]
            await message.answer(error_msg)
            return

        # Store the name and move to next step
        user_data[message.from_user.id]["name"] = message.text
        user_data[message.from_user.id]["step"] = "phone"
        lang = user_data[message.from_user.id].get("lang", "en")
        
        prompt = {
            "ru": "Теперь введите ваш номер телефона:",
            "az": "İndi telefon nömrənizi daxil edin:",
            "en": "Now please enter your phone number:"
        }[lang]
        
        await message.answer(prompt)
        
    except Exception as e:
        logger.error(f"Error in get_name handler: {e}")
        lang = user_lang.get(message.from_user.id, "en")
        error_msg = {
            "ru": "Произошла ошибка, пожалуйста, попробуйте снова",
            "az": "Xəta baş verdi, zəhmət olmasa yenidən cəhd edin",
            "en": "An error occurred, please try again"
        }[lang]
        await message.answer(error_msg, reply_markup=get_menu_keyboard(lang))
        if message.from_user.id in user_data:
            del user_data[message.from_user.id]
    await message.answer(
        f"Оплатите {user_data[user_id]['price']} на карту: {PAYMENT_CARD}\n"
        "Отправьте скриншот оплаты." if lang == "ru" else
        f"{user_data[user_id]['price']} məbləğini {PAYMENT_CARD} kartına ödəyin.\n"
        "Ödəniş skrinşotu göndərin." if lang == "az" else
        f"Please pay {user_data[user_id]['price']} to card: {PAYMENT_CARD}\n"
        "Send payment screenshot.",
        reply_markup=get_menu_keyboard(lang)
    )

@dp.message(lambda m: user_data.get(m.from_user.id, {}).get("step") == "payment")
async def process_payment(message: types.Message):
    user_id = message.from_user.id
    if not message.photo:
        lang = user_data[user_id]["lang"]
        await message.answer("Please send payment screenshot")
        return

    try:
        # Generate ticket code
        code = generate_ticket_code()
        ticket_codes[user_id] = code
        
        # Store order
        order = {
            "user_id": user_id,
            "name": user_data[user_id]["name"],
            "phone": user_data[user_id]["phone"],
            "ticket_type": user_data[user_id]["ticket_type"],
            "price": user_data[user_id]["price"],
            "date": datetime.now(),
            "status": "pending",
            "code": code
        }
        orders.append(order)
        statistics[user_data[user_id]["ticket_type"]] += 1

        # Notify admin
        await notify_admin(
            user_id,
            user_data[user_id]["name"],
            user_data[user_id]["phone"],
            user_data[user_id]["ticket_type"]
        )

        lang = user_data[user_id]["lang"]
        await message.answer(
            f"Заявка принята! Код: {code}" if lang == "ru" else
            f"Müraciət qəbul edildi! Kod: {code}" if lang == "az" else
            f"Request accepted! Code: {code}",
            reply_markup=get_menu_keyboard(lang)
        )

        del user_data[user_id]

    except Exception as e:
        logger.error(f"Payment error: {e}")
        await message.answer("Payment processing failed")

# ================= ADMIN FUNCTIONS =================

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        return
    await message.answer("Админ панель:", reply_markup=get_admin_keyboard())

@dp.callback_query(F.data.startswith("admin_"))
async def admin_actions(callback: types.CallbackQuery):
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        return

    action = callback.data.split("_")[1]
    
    if action == "stats":
        stats_text = (
            "📊 Статистика:\n"
            f"Стандарт: {statistics.get('standard', 0)}\n"
            f"VIP Одиночный: {statistics.get('vip_single', 0)}\n"
            f"VIP Столик: {statistics.get('vip_table', 0)}\n"
            f"Exclusive: {statistics.get('exclusive_table', 0)}\n"
            f"Всего: {sum(statistics.values())}"
        )
        await callback.message.edit_text(stats_text, reply_markup=get_admin_keyboard())
    
    elif action == "orders":
        last_orders = "\n".join(
            f"{o['name']} - {o['ticket_type']} ({o['date'].strftime('%d.%m %H:%M')})"
            for o in orders[-5:]
        )
        await callback.message.edit_text(
            f"Последние заявки:\n{last_orders}" if last_orders else "Нет заявок",
            reply_markup=get_admin_keyboard()
        )
    
    elif action == "pending":
        pending = [o for o in orders if o["status"] == "pending"]
        if pending:
            text = "⏳ Ожидающие:\n" + "\n".join(
                f"{o['name']} - {o['ticket_type']} (ID: {o['user_id']})"
                for o in pending
            )
        else:
            text = "Нет ожидающих заявок"
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard())

@dp.message(F.text.regexp(r"^/(accept|reject)_\d+"))
async def handle_admin_decision(message: types.Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        return

    command, user_id = message.text.split("_")
    user_id = int(user_id)
    action = command[1:]  # "accept" or "reject"

    # Find the order
    order = next((o for o in orders if o["user_id"] == user_id and o["status"] == "pending"), None)
    if not order:
        await message.answer("Заявка не найдена")
        return

    # Update status
    order["status"] = "approved" if action == "accept" else "rejected"

    # Notify user
    lang = user_lang.get(user_id, "en")
    if action == "accept":
        await bot.send_message(
            user_id,
            f"🎉 Ваш билет подтвержден! Код: {order['code']}" if lang == "ru" else
            f"🎉 Biletiniz təsdiqləndi! Kod: {order['code']}" if lang == "az" else
            f"🎉 Your ticket is approved! Code: {order['code']}"
        )
        await message.answer(f"Заявка {user_id} подтверждена")
    else:
        await bot.send_message(
            user_id,
            "❌ Ваша заявка отклонена" if lang == "ru" else
            "❌ Müraciətiniz rədd edildi" if lang == "az" else
            "❌ Your request was rejected"
        )
        await message.answer(f"Заявка {user_id} отклонена")



async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
