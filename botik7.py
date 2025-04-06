import os
import logging
import asyncio
from aiogram.types import Update
import random
import string
from typing import Optional
from aiohttp import web
from datetime import datetime
from collections import defaultdict
from aiogram import Bot, Dispatcher, types, F
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiogram.enums import ParseMode    
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
#TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7598421595:AAFIBwcEENiYq23qGLItJNGx6AHbAH7K17Y")
WEB_SERVER_HOST = "0.0.0.0"  # Render requires this
WEB_SERVER_PORT = int(os.getenv("PORT", 8000))  # Render provides PORT
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://botik-aao9.onrender.com{WEBHOOK_PATH}"  # Case-sensitive!
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
# Helper Functions
def generate_ticket_id():
    """Generate a unique 8-character ticket ID with prefix"""
    prefix = random.choice(['VIP', 'STD', 'EXT'])
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=5))
    return f"{prefix}-{suffix}"

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistics", callback_data="stats")],
        [InlineKeyboardButton(text="📝 Recent Orders", callback_data="orders")],
        [InlineKeyboardButton(text="⏳ Pending Approvals", callback_data="pending")]
    ])

# ===== ADMIN HANDLERS =====
@dp.message(Command("admin"))
async def admin_command(message: types.Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        await message.answer("You are not authorized to use this command")
        return
    
    await message.answer(
        "Admin Panel:",
        reply_markup=get_admin_keyboard()
    )

@dp.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    stats_text = (
        f"📊 <b>Statistics</b>\n\n"
        f"Standard Tickets: {statistics.get('standard', 0)}\n"
        f"VIP Single Tickets: {statistics.get('vip_single', 0)}\n"
        f"VIP Table Tickets: {statistics.get('vip_table', 0)}\n"
        f"Exclusive Table Tickets: {statistics.get('exclusive_table', 0)}\n"
        f"Total Revenue: {sum(int(t['price'].split()[0]) for t in orders if t.get('status') == 'approved')} AZN"
    )
    await callback.message.edit_text(stats_text, reply_markup=get_admin_keyboard())

@dp.callback_query(F.data == "orders")
async def show_recent_orders(callback: types.CallbackQuery):
    recent = "\n".join(
        f"{o['date'].strftime('%Y-%m-%d')}: {o['name']} - {o['ticket_type']} ({o['price']})"
        for o in sorted(orders[-5:], key=lambda x: x['date'], reverse=True)
    )
    await callback.message.edit_text(
        f"📝 <b>Recent Orders</b>\n\n{recent}" if recent else "No orders yet",
        reply_markup=get_admin_keyboard()
    )

@dp.callback_query(F.data == "pending")
async def show_pending(callback: types.CallbackQuery):
    pending = [o for o in orders if o.get('status') == 'pending']
    if pending:
        text = "⏳ <b>Pending Approvals</b>\n\n" + "\n".join(
            f"{o['name']} - {o['ticket_type']} (ID: {o['user_id']})"
            for o in pending
        )
    else:
        text = "No pending approvals"
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())

# ===== TICKET PURCHASE FLOW =====
@dp.message(lambda m: user_data.get(m.from_user.id, {}).get("step") == "payment")
async def process_payment(message: types.Message):
    user_id = message.from_user.id
    try:
        # Generate unique ticket ID
        ticket_id = generate_ticket_id()
        while ticket_id in ticket_codes.values():
            ticket_id = generate_ticket_id()
            
        ticket_codes[user_id] = ticket_id
        lang = user_data[user_id]["lang"]
        
        # Create order
        order = {
            "user_id": user_id,
            "name": user_data[user_id]["name"],
            "phone": user_data[user_id]["phone"],
            "ticket_type": user_data[user_id]["ticket_type"],
            "price": user_data[user_id]["price"],
            "ticket_id": ticket_id,
            "date": datetime.now(),
            "status": "pending"
        }
        orders.append(order)
        statistics[user_data[user_id]["ticket_type"]] += 1

        # Notify admin
        await notify_admin(
            user_id=user_id,
            name=user_data[user_id]["name"],
            phone=user_data[user_id]["phone"],
            ticket_type=user_data[user_id]["ticket_type"]
        )

        # Confirm to user
        await message.answer(
            f"✅ <b>Заявка принята!</b>\nВаш ID билета: <code>{ticket_id}</code>" if lang == "ru" else
            f"✅ <b>Müraciət qəbul edildi!</b>\nBilet ID-niz: <code>{ticket_id}</code>" if lang == "az" else
            f"✅ <b>Request accepted!</b>\nYour ticket ID: <code>{ticket_id}</code>",
            reply_markup=get_menu_keyboard(lang)
        )

        del user_data[user_id]

    except Exception as e:
        logger.error(f"Payment processing error: {e}")
        lang = user_lang.get(user_id, "en")
        await message.answer(
            "Ошибка обработки платежа" if lang == "ru" else
            "Ödənişin emalı zamanı xəta" if lang == "az" else
            "Payment processing error",
            reply_markup=get_menu_keyboard(lang)
        )
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

async def notify_admin(user_id: int, name: str, phone: str, ticket_type: str):
    try:
        ticket_name = TICKET_TYPES[ticket_type]["ru"]["name"]
        await bot.send_message(
            YOUR_TELEGRAM_ID,
            f"<b>🆕 Новая заявка:</b>\n\n"
            f"👤 <b>ID:</b> {user_id}\n"
            f"📛 <b>Имя:</b> {name}\n"
            f"📱 <b>Телефон:</b> {phone}\n"
            f"🎫 <b>Тип:</b> {ticket_name}\n\n"
            f"<b>Ответьте:</b>\n"
            f"/accept_{user_id} - подтвердить\n"
            f"/reject_{user_id} - отклонить"
        )
    except Exception as e:
        logger.error(f"Admin notify error: {e}")

# ===== HANDLERS =====
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
        "ru": "<b>Текущий ивент: Afro-Party в Voodoo!</b>\n\n"
              "📅 <b>Дата:</b> 27 апреля 2025\n"
              "🕒 <b>Время:</b> 18:00 - 00:00\n"
              "📍 <b>Место:</b> Рестобар Voodoo, ТРЦ Наргиз Молл, 3 этаж",
        "az": "<b>Cari tədbir: Afro-Party Voodoo-da!</b>\n\n"
              "📅 <b>Tarix:</b> 27 Aprel 2025\n"
              "🕒 <b>Vaxt:</b> 18:00 - 00:00\n"
              "📍 <b>Yer:</b> Voodoo Restobar, Nargiz Mall, 3-cü mərtəbə",
        "en": "<b>Current event: Afro-Party at Voodoo!</b>\n\n"
              "📅 <b>Date:</b> April 27, 2025\n"
              "🕒 <b>Time:</b> 6:00 PM - 12:00 AM\n"
              "📍 <b>Location:</b> Voodoo Restobar, Nargiz Mall, 3rd floor"
    }[lang]
    await message.answer(events_info, reply_markup=get_menu_keyboard(lang))

@dp.message(F.text.in_(["📞 Контакты", "📞 Əlaqə", "📞 Contacts"]))
async def contacts_handler(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    contact_info = {
        "ru": "<b>📞 Контакты:</b>\nТелефон: +994 10 531 24 06",
        "az": "<b>📞 Əlaqə:</b>\nTelefon: +994 10 531 24 06",
        "en": "<b>📞 Contacts:</b>\nPhone: +994 10 531 24 06"
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
        if not message.text or len(message.text.split()) < 2:
            lang = user_data[message.from_user.id].get("lang", "en")
            error_msg = {
                "ru": "Пожалуйста, введите имя и фамилию",
                "az": "Zəhmət olmasa, ad və soyadınızı daxil edin",
                "en": "Please enter both first and last name"
            }[lang]
            await message.answer(error_msg)
            return

        user_data[message.from_user.id]["name"] = message.text
        user_data[message.from_user.id]["step"] = "phone"
        lang = user_data[message.from_user.id]["lang"]
        
        await message.answer(
            "Теперь введите ваш номер телефона:" if lang == "ru" else
            "İndi telefon nömrənizi daxil edin:" if lang == "az" else
            "Now please enter your phone number:"
        )
        
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

@dp.message(lambda m: user_data.get(m.from_user.id, {}).get("step") == "phone")
async def get_phone(message: types.Message):
    try:
        user_id = message.from_user.id
        if not message.text:
            raise ValueError("Empty phone number")
            
        user_data[user_id]["phone"] = message.text
        user_data[user_id]["step"] = "payment"
        lang = user_data[user_id]["lang"]
        
        await message.answer(
            f"Оплатите {user_data[user_id]['price']} на карту: {PAYMENT_CARD}\n"
            "Отправьте скриншот оплаты." if lang == "ru" else
            f"{user_data[user_id]['price']} məbləğini {PAYMENT_CARD} kartına ödəyin.\n"
            "Ödəniş skrinşotu göndərin." if lang == "az" else
            f"Please pay {user_data[user_id]['price']} to card: {PAYMENT_CARD}\n"
            "Send payment screenshot.",
            reply_markup=get_menu_keyboard(lang)
        )

    except Exception as e:
        logger.error(f"Error in get_phone handler: {e}")
        lang = user_lang.get(message.from_user.id, "en")
        await message.answer(
            "Неверный номер телефона, попробуйте снова" if lang == "ru" else
            "Yanlış telefon nömrəsi, yenidən cəhd edin" if lang == "az" else
            "Invalid phone number, please try again",
            reply_markup=get_menu_keyboard(lang)
        )

async def health_check(request):
    """Endpoint for Render health checks"""
    return web.Response(text="🤖 Botik is healthy!")

async def on_startup(app: web.Application):
    # Reset any existing webhook first
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Set new webhook with correct case
    await bot.set_webhook(WEBHOOK_URL)
    
    # Verify
    webhook_info = await bot.get_webhook_info()
    logger.info(f"Webhook set to: {webhook_info.url}")
    logger.info(f"Is active: {webhook_info.url == WEBHOOK_URL}")  # Should be True

@dp.update()
async def log_updates(update: Update):
    """Log all incoming updates"""
    logger.info(f"📨 Update received: {update.update_id}")
    return

async def main():
    """Configure and start the application"""
    app = web.Application()
    
    # 1. Add health check first (Render requirement)
    app.router.add_get("/", health_check)
    
    # 2. Register webhook handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    # 3. Add startup callback
    app.on_startup.append(on_startup)
    
    # 4. Start server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)
    await site.start()
    
    logger.info(f"🚀 Server started on {WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
    logger.info(f"Webhook URL: {WEBHOOK_URL}")
    
    # 5. Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
