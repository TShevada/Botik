import os
import logging
import asyncio
import random
import string
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)

# Configuration
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 1291104906
PORT = int(os.getenv("PORT", 8080))  # Required for Render
PAYMENT_CARD = "4169 7388 9268 3164"

# Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher()

# Data Storage
user_lang: Dict[int, str] = {}
user_data: Dict[int, Dict[str, Any]] = {}
pending_approvals: Dict[int, Dict[str, Any]] = {}
approved_tickets = defaultdict(list)

# Helper Functions
def generate_ticket_id() -> str:
    return ''.join(random.choices(string.digits, k=6))

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def get_lang_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇦🇿 Azərbaycan")],
            [KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True
    )

def get_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    buttons = {
        "ru": [
            [KeyboardButton(text="🎫 Билеты")],
            [KeyboardButton(text="📅 Ближайшие события")],
            [KeyboardButton(text="📞 Контакты")],
            [KeyboardButton(text="🌐 Сменить язык")]
        ],
        "az": [
            [KeyboardButton(text="🎫 Biletlər")],
            [KeyboardButton(text="📅 Yaxın tədbirlər")],
            [KeyboardButton(text="📞 Əlaqə")],
            [KeyboardButton(text="🌐 Dil dəyiş")]
        ],
        "en": [
            [KeyboardButton(text="🎫 Tickets")],
            [KeyboardButton(text="📅 Upcoming events")],
            [KeyboardButton(text="📞 Contacts")],
            [KeyboardButton(text="🌐 Change language")]
        ]
    }
    return ReplyKeyboardMarkup(keyboard=buttons[lang], resize_keyboard=True)

def get_ticket_type_keyboard(lang: str) -> ReplyKeyboardMarkup:
    buttons = []
    for ticket_type in TICKET_TYPES:
        buttons.append([KeyboardButton(text=TICKET_TYPES[ticket_type][lang]["name"])])
    
    back_text = {
        "ru": "⬅️ Назад",
        "az": "⬅️ Geri",
        "en": "⬅️ Back"
    }
    buttons.append([KeyboardButton(text=back_text[lang])])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Ticket Types with Payment Notes
TICKET_TYPES = {
    "standard": {
        "az": {
            "name": "Standard — 20 AZN",
            "full_info": "Standard — 20 AZN\n• Qarşılama kokteylləri\n• Fan Zonası\n\n❗️Nəzərinizə çatdırırıq ki, biletlər alındıqdan sonra geri qaytarılmır",
            "note": "Ödəniş etdikdən sonra skrinşot göndərməyi unutmayın!"
        },
        "ru": {
            "name": "Стандарт — 20 AZN", 
            "full_info": "Стандарт — 20 AZN\n• Приветственные коктейли\n• Fan Zone\n\n❗️Обратите внимание, что билеты не подлежат возврату после покупки",
            "note": "Не забудьте отправить скриншот после оплаты!"
        },
        "en": {
            "name": "Standard — 20 AZN",
            "full_info": "Standard — 20 AZN\n• Welcome cocktails\n• Fan Zone\n\n❗️Please note that tickets cannot be refunded after purchase",
            "note": "Don't forget to send payment screenshot!"
        }
    },
    "vip_single": {
        "az": {
            "name": "VIP (Fərdi) — 40 AZN",
            "full_info": "VIP (Fərdi) — 40 AZN\n• Fərdi masa yeri\n• Qarşılama kokteyli\n• Yerlərin sayı məhduddur\n\n❗️Nəzərinizə çatdırırıq ki, biletlər alındıqdan sonra geri qaytarılmır",
            "note": "Ödəniş etdikdən sonra skrinşot göndərməyi unutmayın!"
        },
        "ru": {
            "name": "VIP (Индивидуальный) — 40 AZN",
            "full_info": "VIP (Индивидуальный) — 40 AZN\n• Индивидуальное место\n• Приветственный коктейль\n• Количество мест ограничено\n\n❗️Обратите внимание, что билеты не подлежат возврату после покупки",
            "note": "Не забудьте отправить скриншот после оплаты!"
        },
        "en": {
            "name": "VIP (Single) — 40 AZN", 
            "full_info": "VIP (Single) — 40 AZN\n• Individual seat\n• Welcome cocktail\n• Limited seats available\n\n❗️Please note that tickets cannot be refunded after purchase",
            "note": "Don't forget to send payment screenshot!"
        }
    },
    "vip_table": {
        "az": {
            "name": "VIP (Masa) — 160 AZN",
            "full_info": "VIP (Masa) — 160 AZN\n• 4 nəfərlik ayrıca masa\n• Bütün şirkət üçün qarşılama kokteylləri\n• Yerlərin sayı məhduddur\n\n❗️Nəzərinizə çatdırırıq ki, biletlər alındıqdan sonra geri qaytarılmır",
            "note": "Ödəniş etdikdən sonra skrinşot göndərməyi unutmayın!"
        },
        "ru": {
            "name": "VIP (Столик) — 160 AZN",
            "full_info": "VIP (Столик) — 160 AZN\n• Столик на 4 персоны\n• Приветственные коктейли для всей компании\n• Количество мест ограничено\n\n❗️Обратите внимание, что билеты не подлежат возврату после покупки",
            "note": "Не забудьте отправить скриншот после оплаты!"
        },
        "en": {
            "name": "VIP (Table) — 160 AZN",
            "full_info": "VIP (Table) — 160 AZN\n• Table for 4 people\n• Welcome cocktails for whole group\n• Limited seats available\n\n❗️Please note that tickets cannot be refunded after purchase",
            "note": "Don't forget to send payment screenshot!"
        }
    },
    "exclusive_table": {
        "az": {
            "name": "Exclusive (Masa) — 240 AZN",
            "full_info": "Exclusive (Masa) — 240 AZN\n• DJ masasının yanında giriş imkanı\n• 4 nəfərlik ayrıca masa\n• Bütün şirkət üçün qarşılama kokteylləri\n• Yerlərin sayı məhduddur\n\n❗️Nəzərinizə çatdırırıq ki, biletlər alındıqdan sonra geri qaytarılmır",
            "note": "Ödəniş etdikdən sonra skrinşot göndərməyi unutmayın!"
        },
        "ru": {
            "name": "Exclusive (Столик) — 240 AZN",
            "full_info": "Exclusive (Столик) — 240 AZN\n• Доступ к DJ-зоне\n• Столик на 4 персоны\n• Приветственные коктейли для всей компании\n• Количество мест ограничено\n\n❗️Обратите внимание, что билеты не подлежат возврату после покупки",
            "note": "Не забудьте отправить скриншот после оплаты!"
        },
        "en": {
            "name": "Exclusive (Table) — 240 AZN",
            "full_info": "Exclusive (Table) — 240 AZN\n• DJ area access\n• Table for 4 people\n• Welcome cocktails for whole group\n• Limited seats available\n\n❗️Please note that tickets cannot be refunded after purchase",
            "note": "Don't forget to send payment screenshot!"
        }
    }
}

# Handlers
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Выберите язык / Select language / Dil seçin:", reply_markup=get_lang_keyboard())

@dp.message(F.text.in_(["🇷🇺 Русский", "🇦🇿 Azərbaycan", "🇬🇧 English"]))
async def set_language(message: types.Message):
    lang_map = {
        "🇷🇺 Русский": "ru",
        "🇦🇿 Azərbaycan": "az",
        "🇬🇧 English": "en"
    }
    user_lang[message.from_user.id] = lang_map[message.text]
    await message.answer(
        "Язык установлен: Русский" if lang_map[message.text] == "ru" else
        "Dil seçildi: Azərbaycan" if lang_map[message.text] == "az" else
        "Language set: English",
        reply_markup=get_menu_keyboard(lang_map[message.text])
    )

@dp.message(F.text.in_(["🎫 Билеты", "🎫 Biletlər", "🎫 Tickets"]))
async def tickets_menu_handler(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    await message.answer(
        "Выберите тип билета:" if lang == "ru" else 
        "Bilet növünü seçin:" if lang == "az" else 
        "Select ticket type:",
        reply_markup=get_ticket_type_keyboard(lang))
    

@dp.message(F.text.in_(["⬅️ Назад", "⬅️ Geri", "⬅️ Back"]))
async def handle_back(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    await message.answer(
        "Главное меню" if lang == "ru" else
        "Əsas menyu" if lang == "az" else
        "Main menu",
        reply_markup=get_menu_keyboard(lang)
    )

@dp.message(F.text)
async def handle_text_messages(message: types.Message):
    # First check if we're in the middle of a ticket purchase
    if message.from_user.id in user_data:
        current_step = user_data[message.from_user.id].get("step")
        
        if current_step == "name":
            await process_name_input(message)
            return
        elif current_step == "phone":
            await process_phone_input(message)
            return
        elif current_step == "confirm":
            return  # Let the confirm handler deal with this
    
    lang = user_lang.get(message.from_user.id, "en")
    
    # Check for ticket type selection
    selected_ticket = None
    for ticket_type, data in TICKET_TYPES.items():
        if message.text == data[lang]["name"]:
            selected_ticket = ticket_type
            break
    
    if selected_ticket:
        await process_ticket_selection(message, selected_ticket, lang)
    else:
        await handle_other_commands(message, lang)

async def process_ticket_selection(message: types.Message, ticket_type: str, lang: str):
    """Handle ticket type selection"""
    await message.answer(TICKET_TYPES[ticket_type][lang]["full_info"])
    
    user_data[message.from_user.id] = {
        "step": "name",
        "lang": lang,
        "ticket_type": ticket_type,
        "ticket_price": TICKET_TYPES[ticket_type][lang]["name"].split("—")[1].strip()
    }
    
    await message.answer(
        "Для покупки введите ваше Имя и Фамилию:" if lang == "ru" else
        "Bilet almaq üçün ad və soyadınızı daxil edin:" if lang == "az" else
        "To buy tickets, enter your First and Last name:",
        reply_markup=types.ReplyKeyboardRemove()
    )

async def process_name_input(message: types.Message):
    """Process name input after ticket selection"""
    lang = user_data[message.from_user.id].get("lang", "en")
    
    if not message.text or len(message.text) < 2:
        await message.answer(
            "Введите корректное имя (минимум 2 символа)" if lang == "ru" else
            "Düzgün ad daxil edin (minimum 2 simvol)" if lang == "az" else
            "Enter valid name (min 2 characters)"
        )
        return
        
    user_data[message.from_user.id]["name"] = message.text
    user_data[message.from_user.id]["step"] = "phone"
    
    await message.answer(
        "Теперь введите ваш номер телефона:" if lang == "ru" else
        "İndi telefon nömrənizi daxil edin:" if lang == "az" else
        "Now please enter your phone number:"
    )

async def process_phone_input(message: types.Message):
    """Process phone number input"""
    lang = user_data[message.from_user.id].get("lang", "en")
    phone = ''.join(c for c in message.text if c.isdigit() or c == '+')
    
    if len(phone) < 9 or (phone.startswith('+') and len(phone) < 12):
        await message.answer(
            "Введите корректный номер (минимум 9 цифр)" if lang == "ru" else
            "Düzgün nömrə daxil edin (minimum 9 rəqəm)" if lang == "az" else
            "Enter valid number (min 9 digits)"
        )
        return
    
    user_data[message.from_user.id]["phone"] = phone
    user_data[message.from_user.id]["step"] = "confirm"
    ticket_info = TICKET_TYPES[user_data[message.from_user.id]["ticket_type"]][lang]
    
    await message.answer(
        f"Проверьте данные:\n\n🎟 {ticket_info['name']}\n👤 {user_data[message.from_user.id]['name']}\n📱 {phone}",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Да" if lang == "ru" else "✅ Bəli" if lang == "az" else "✅ Yes")],
                [KeyboardButton(text="❌ Нет" if lang == "ru" else "❌ Xeyr" if lang == "az" else "❌ No")]
            ],
            resize_keyboard=True
        )
    )

async def handle_other_commands(message: types.Message, lang: str):
    """Handle other text commands"""
    if message.text in ["📅 Ближайшие события", "📅 Yaxın tədbirlər", "📅 Upcoming events"]:
        await message.answer(
            "Ближайшие события будут здесь" if lang == "ru" else
            "Yaxın tədbirlər burada olacaq" if lang == "az" else
            "Upcoming events will be here"
        )
    elif message.text in ["📞 Контакты", "📞 Əlaqə", "📞 Contacts"]:
        await message.answer(
            "Контакты: @username" if lang == "ru" else
            "Əlaqə: @username" if lang == "az" else
            "Contacts: @username"
        )
    elif message.text in ["🌐 Сменить язык", "🌐 Dil dəyiş", "🌐 Change language"]:
        await message.answer(
            "Выберите язык:" if lang == "ru" else
            "Dil seçin:" if lang == "az" else
            "Select language:",
            reply_markup=get_lang_keyboard())
        )
    else:
        await message.answer(
            "Неизвестная команда" if lang == "ru" else
            "Naməlum əmr" if lang == "az" else
            "Unknown command"
        )

@dp.message(F.text.in_(["✅ Да", "✅ Bəli", "✅ Yes"]))
async def confirm_purchase(message: types.Message):
    if message.from_user.id not in user_data:
        lang = user_lang.get(message.from_user.id, "en")
        await message.answer(
            "Нет активной заявки" if lang == "ru" else
            "Aktiv müraciət yoxdur" if lang == "az" else
            "No active application",
            reply_markup=get_menu_keyboard(lang))
        return
    
    lang = user_data[message.from_user.id].get("lang", "en")
    user_data[message.from_user.id]["step"] = "payment"
    
    await message.answer(
        f"Оплатите {user_data[message.from_user.id]['ticket_price']} на карту: `{PAYMENT_CARD}`\n"
        "и отправьте скриншот оплаты.\n\n"
        f"{TICKET_TYPES[user_data[message.from_user.id]['ticket_type']][lang]['note']}",
        reply_markup=get_menu_keyboard(lang))
    )

@dp.message(F.text.in_(["❌ Нет", "❌ Xeyr", "❌ No"]))
async def cancel_purchase(message: types.Message):
    if message.from_user.id in user_data:
        lang = user_data[message.from_user.id].get("lang", "en")
        del user_data[message.from_user.id]
        await message.answer(
            "Покупка отменена" if lang == "ru" else
            "Alış etmək ləğv edildi" if lang == "az" else
            "Purchase canceled",
            reply_markup=get_menu_keyboard(lang))
        )

@dp.message(F.photo, lambda m: user_data.get(m.from_user.id, {}).get("step") == "payment")
async def handle_payment_photo(message: types.Message):
    if message.from_user.id not in user_data:
        return
        
    lang = user_data[message.from_user.id].get("lang", "en")
    try:
        ticket_id = generate_ticket_id()
        pending_approvals[message.from_user.id] = {
            **user_data[message.from_user.id],
            "photo_id": message.photo[-1].file_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket_id": ticket_id,
            "username": message.from_user.username or "N/A"
        }
        
        # Notify admin
        ticket_name = TICKET_TYPES[pending_approvals[message.from_user.id]["ticket_type"]]["ru"]["name"]
        await bot.send_photo(
            ADMIN_ID,
            message.photo[-1].file_id,
            caption=(
                f"🆕 Новая заявка #{ticket_id}\n\n"
                f"👤 Пользователь: @{pending_approvals[message.from_user.id]['username']} [ID:{message.from_user.id}]\n"
                f"📝 Имя: {user_data[message.from_user.id]['name']}\n"
                f"📱 Телефон: {user_data[message.from_user.id]['phone']}\n"
                f"🎟 Тип: {ticket_name} ({user_data[message.from_user.id]['ticket_price']})\n\n"
                f"Для обработки используйте команды:\n"
                f"/approve_{message.from_user.id} - подтвердить\n"
                f"/reject_{message.from_user.id} [причина] - отклонить"
            )
        )
        
        await message.answer(
            f"✅ Спасибо! Заявка #{ticket_id} на рассмотрении" if lang == "ru" else
            f"✅ Təşəkkürlər! {ticket_id} nömrəli müraciətiniz nəzərdən keçirilir" if lang == "az" else
            f"✅ Thank you! Application #{ticket_id} is under review",
            reply_markup=get_menu_keyboard(lang))
        )
        del user_data[message.from_user.id]
    except Exception as e:
        logger.error(f"Payment error: {e}")
        await message.answer(
            "Ошибка обработки платежа" if lang == "ru" else
            "Ödəniş emalı xətası" if lang == "az" else
            "Payment processing error"
        )

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    text = "🛠 Админ панель\n\n"
    text += f"⏳ Ожидают подтверждения: {len(pending_approvals)}\n"
    text += f"✅ Подтвержденных билетов: {sum(len(v) for v in approved_tickets.values())}\n\n"
    text += "Команды:\n"
    text += "/pending - список ожидающих заявок\n"
    text += "/approved - список подтвержденных билетов"
    
    await message.answer(text)

@dp.message(Command("pending"))
async def show_pending(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    if not pending_approvals:
        await message.answer("⏳ Нет заявок на рассмотрении")
        return
    
    text = "⏳ Заявки на рассмотрении:\n\n"
    for user_id, data in pending_approvals.items():
        ticket_name = TICKET_TYPES[data["ticket_type"]]["ru"]["name"]
        text += (
            f"🆔 #{data['ticket_id']}\n"
            f"👤 @{data['username']} [ID:{user_id}]\n"
            f"📝 {data['name']} | 📱 {data['phone']}\n"
            f"🎟 {ticket_name} ({data['ticket_price']})\n"
            f"🕒 {data['date']}\n"
            f"🔹 /approve_{user_id} | /reject_{user_id} [причина]\n\n"
        )
    
    await message.answer(text)

@dp.message(Command("approved"))
async def show_approved(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    if not approved_tickets:
        await message.answer("✅ Нет подтвержденных билетов")
        return
    
    text = "✅ Подтвержденные билеты:\n\n"
    for user_id, tickets in approved_tickets.items():
        for ticket in tickets:
            ticket_name = TICKET_TYPES[ticket["ticket_type"]]["ru"]["name"]
            text += (
                f"🆔 #{ticket['ticket_id']}\n"
                f"👤 ID:{user_id}\n"
                f"🎟 {ticket_name}\n"
                f"🕒 {ticket['date']}\n\n"
            )
    
    await message.answer(text)

@dp.message(Command("approve"))
async def approve_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Extract user_id from message text (expecting "/approve_12345")
        args = message.text.split('_')
        if len(args) < 2:
            await message.answer("⚠️ Неверный формат команды. Используйте /approve_12345")
            return
            
        user_id = int(args[1])
        data = pending_approvals.get(user_id)
        
        if not data:
            await message.answer("⚠️ Заявка не найдена")
            return
            
        approved_tickets[user_id].append({
            "ticket_id": data["ticket_id"],
            "ticket_type": data["ticket_type"],
            "date": data["date"]
        })
        
        # Notify user
        lang = data["lang"]
        ticket_name = TICKET_TYPES[data["ticket_type"]][lang]["name"]
        await bot.send_message(
            user_id,
            f"✅ Ваш билет подтвержден!\n\n"
            f"🎟 {ticket_name}\n"
            f"🆔 Номер билета: #{data['ticket_id']}\n\n"
            f"Сохраните этот номер для входа на мероприятие." if lang == "ru" else
            f"✅ Biletiniz təsdiqləndi!\n\n"
            f"🎟 {ticket_name}\n"
            f"🆔 Bilet nömrəsi: #{data['ticket_id']}\n\n"
            f"Tədbirə giriş üçün bu nömrəni saxlayın." if lang == "az" else
            f"✅ Your ticket is approved!\n\n"
            f"🎟 {ticket_name}\n"
            f"🆔 Ticket ID: #{data['ticket_id']}\n\n"
            f"Save this number for event entry."
        )
        
        await message.answer(f"✅ Заявка #{data['ticket_id']} подтверждена")
        del pending_approvals[user_id]
        
    except Exception as e:
        logger.error(f"Approve error: {e}")
        await message.answer("⚠️ Ошибка команды. Формат: /approve_12345")

@dp.message(Command("reject"))
async def reject_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Extract user_id and reason from message text (expecting "/reject_12345 reason")
        parts = message.text.split('_', maxsplit=2)
        if len(parts) < 2:
            await message.answer("⚠️ Неверный формат команды. Используйте /reject_12345 причина")
            return
            
        user_id = int(parts[1])
        reason = parts[2] if len(parts) > 2 else (
            "Причина не указана" if message.from_user.language_code == "ru" else
            "Səbəb göstərilməyib" if message.from_user.language_code == "az" else
            "No reason provided"
        )
        
        data = pending_approvals.get(user_id)
        if not data:
            await message.answer("⚠️ Заявка не найдена")
            return
            
        # Notify user
        lang = data["lang"]
        await bot.send_message(
            user_id,
            f"❌ Ваша заявка отклонена\n\n"
            f"Причина: {reason}\n\n"
            f"Если вы считаете это ошибкой, свяжитесь с администратором." if lang == "ru" else
            f"❌ Müraciətiniz rədd edildi\n\n"
            f"Səbəb: {reason}\n\n"
            f"Əgər səhv olduğunu düşünürsünüzsə, administratorla əlaqə saxlayın." if lang == "az" else
            f"❌ Your application was rejected\n\n"
            f"Reason: {reason}\n\n"
            f"If you think this is a mistake, please contact admin."
        )
        
        await message.answer(f"❌ Заявка #{data['ticket_id']} отклонена. Причина: {reason}")
        del pending_approvals[user_id]
        
    except Exception as e:
        logger.error(f"Reject error: {e}")
        await message.answer("⚠️ Ошибка команды. Формат: /reject_12345 причина")

# Required for Render port binding
async def web_app():
    app = web.Application()
    app.router.add_get("/", lambda request: web.Response(text="Bot is running"))
    return app

async def on_startup(bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)

async def main():
    # Start the bot
    await dp.start_polling(bot)
    
    # Start web app for Render port binding
    app = await web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=PORT)
    await site.start()
    
    # Keep the application running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
