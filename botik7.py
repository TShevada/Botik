import os
import logging
import asyncio
import random
import string
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)

# Configuration
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 1291104906
PORT = int(os.getenv("PORT", "8080"))  # Now properly closed
PAYMENT_CARD = "4169 7388 9268 3164"

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# Data Storage
user_lang = {}
user_data = {}
pending_approvals = {}
approved_tickets = defaultdict(list)

# Helper Functions
def generate_ticket_id():
    return ''.join(random.choices(string.digits, k=6))

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def get_lang_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇦🇿 Azərbaycan")],
            [KeyboardButton(text="🇬🇧 English")]
        ],
        resize_keyboard=True
    )

def get_menu_keyboard(lang):
    if lang == "ru":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎫 Билеты")],
                [KeyboardButton(text="📅 Ближайшие события")],
                [KeyboardButton(text="📞 Контакты")],
                [KeyboardButton(text="🌐 Сменить язык")]
            ],
            resize_keyboard=True
        )
    elif lang == "az":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎫 Biletlər")],
                [KeyboardButton(text="📅 Yaxın tədbirlər")],
                [KeyboardButton(text="📞 Əlaqə")],
                [KeyboardButton(text="🌐 Dil dəyiş")]
            ],
            resize_keyboard=True
        )
    else:  # English
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎫 Tickets")],
                [KeyboardButton(text="📅 Upcoming events")],
                [KeyboardButton(text="📞 Contacts")],
                [KeyboardButton(text="🌐 Change language")]
            ],
            resize_keyboard=True
        )

def get_ticket_type_keyboard(lang):
    buttons = []
    for ticket_type in TICKET_TYPES:
        buttons.append([KeyboardButton(text=TICKET_TYPES[ticket_type][lang]["name"])])
    
    back_text = "⬅️ Назад" if lang == "ru" else "⬅️ Geri" if lang == "az" else "⬅️ Back"
    buttons.append([KeyboardButton(text=back_text)])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Ticket Types with Payment Notes
TICKET_TYPES = {
    "standard": {
        "az": {
            "name": "Standard — 20 AZN",
            "full_info": (
                "Standard — 20 AZN\n"
                "• Qarşılama kokteylləri\n"
                "• Fan Zonası\n\n"
                "❗️Nəzərinizə çatdırırıq ki, biletlər alındıqdan sonra geri qaytarılmır"
            ),
            "note": "Ödəniş etdikdən sonra skrinşot göndərməyi unutmayın!"
        },
        "ru": {
            "name": "Стандарт — 20 AZN", 
            "full_info": (
                "Стандарт — 20 AZN\n"
                "• Приветственные коктейли\n"
                "• Fan Zone\n\n"
                "❗️Обратите внимание, что билеты не подлежат возврату после покупки"
            ),
            "note": "Не забудьте отправить скриншот после оплаты!"
        },
        "en": {
            "name": "Standard — 20 AZN",
            "full_info": (
                "Standard — 20 AZN\n"
                "• Welcome cocktails\n"
                "• Fan Zone\n\n"
                "❗️Please note that tickets cannot be refunded after purchase"
            ),
            "note": "Don't forget to send payment screenshot!"
        }
    },
    "vip_single": {
        "az": {
            "name": "VIP (Fərdi) — 40 AZN",
            "full_info": (
                "VIP (Fərdi) — 40 AZN\n"
                "• Fərdi masa yeri\n"
                "• Qarşılama kokteyli\n"
                "• Yerlərin sayı məhduddur\n\n"
                "❗️Nəzərinizə çatdırırıq ki, biletlər alındıqdan sonra geri qaytarılmır"
            ),
            "note": "Ödəniş etdikdən sonra skrinşot göndərməyi unutmayın!"
        },
        "ru": {
            "name": "VIP (Индивидуальный) — 40 AZN",
            "full_info": (
                "VIP (Индивидуальный) — 40 AZN\n"
                "• Индивидуальное место\n"
                "• Приветственный коктейль\n"
                "• Количество мест ограничено\n\n"
                "❗️Обратите внимание, что билеты не подлежат возврату после покупки"
            ),
            "note": "Не забудьте отправить скриншот после оплаты!"
        },
        "en": {
            "name": "VIP (Single) — 40 AZN", 
            "full_info": (
                "VIP (Single) — 40 AZN\n"
                "• Individual seat\n"
                "• Welcome cocktail\n"
                "• Limited seats available\n\n"
                "❗️Please note that tickets cannot be refunded after purchase"
            ),
            "note": "Don't forget to send payment screenshot!"
        }
    },
    "vip_table": {
        "az": {
            "name": "VIP (Masa) — 160 AZN",
            "full_info": (
                "VIP (Masa) — 160 AZN\n"
                "• 4 nəfərlik ayrıca masa\n"
                "• Bütün şirkət üçün qarşılama kokteylləri\n"
                "• Yerlərin sayı məhduddur\n\n"
                "❗️Nəzərinizə çatdırırıq ki, biletlər alındıqdan sonra geri qaytarılmır"
            ),
            "note": "Ödəniş etdikdən sonra skrinşot göndərməyi unutmayın!"
        },
        "ru": {
            "name": "VIP (Столик) — 160 AZN",
            "full_info": (
                "VIP (Столик) — 160 AZN\n"
                "• Столик на 4 персоны\n"
                "• Приветственные коктейли для всей компании\n"
                "• Количество мест ограничено\n\n"
                "❗️Обратите внимание, что билеты не подлежат возврату после покупки"
            ),
            "note": "Не забудьте отправить скриншот после оплаты!"
        },
        "en": {
            "name": "VIP (Table) — 160 AZN",
            "full_info": (
                "VIP (Table) — 160 AZN\n"
                "• Table for 4 people\n"
                "• Welcome cocktails for whole group\n"
                "• Limited seats available\n\n"
                "❗️Please note that tickets cannot be refunded after purchase"
            ),
            "note": "Don't forget to send payment screenshot!"
        }
    },
    "exclusive_table": {
        "az": {
            "name": "Exclusive (Masa) — 240 AZN",
            "full_info": (
                "Exclusive (Masa) — 240 AZN\n"
                "• DJ masasının yanında giriş imkanı\n"
                "• 4 nəfərlik ayrıca masa\n"
                "• Bütün şirkət üçün qarşılama kokteylləri\n"
                "• Yerlərin sayı məhduddur\n\n"
                "❗️Nəzərinizə çatdırırıq ki, biletlər alındıqdan sonra geri qaytarılmır"
            ),
            "note": "Ödəniş etdikdən sonra skrinşot göndərməyi unutmayın!"
        },
        "ru": {
            "name": "Exclusive (Столик) — 240 AZN",
            "full_info": (
                "Exclusive (Столик) — 240 AZN\n"
                "• Доступ к DJ-зоне\n"
                "• Столик на 4 персоны\n"
                "• Приветственные коктейли для всей компании\n"
                "• Количество мест ограничено\n\n"
                "❗️Обратите внимание, что билеты не подлежат возврату после покупки"
            ),
            "note": "Не забудьте отправить скриншот после оплаты!"
        },
        "en": {
            "name": "Exclusive (Table) — 240 AZN",
            "full_info": (
                "Exclusive (Table) — 240 AZN\n"
                "• DJ area access\n"
                "• Table for 4 people\n"
                "• Welcome cocktails for whole group\n"
                "• Limited seats available\n\n"
                "❗️Please note that tickets cannot be refunded after purchase"
            ),
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
        reply_markup=get_ticket_type_keyboard(lang)
    )

async def back_handler(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    await message.answer(
        "Главное меню" if lang == "ru" else
        "Əsas menyu" if lang == "az" else
        "Main menu",
        reply_markup=get_menu_keyboard(lang)
    )

@dp.message(F.text.in_(["⬅️ Назад", "⬅️ Geri", "⬅️ Back"]))
async def handle_back(message: types.Message):
    await back_handler(message)

@dp.message(F.text)
async def handle_text_messages(message: types.Message):
    # Check if user is in the middle of a process
    if message.from_user.id in user_data and user_data[message.from_user.id].get("step") in ["name", "phone", "confirm"]:
        # Let the specific handlers deal with these cases
        return
        
    lang = user_lang.get(message.from_user.id, "en")
    
    # Check if this is a ticket type selection
    selected_ticket = None
    for ticket_type, data in TICKET_TYPES.items():
        if message.text == data[lang]["name"]:
            selected_ticket = ticket_type
            break
    
    if selected_ticket:
        # Process ticket selection
        await message.answer(TICKET_TYPES[selected_ticket][lang]["full_info"])
        
        user_data[message.from_user.id] = {
            "step": "name",
            "lang": lang,
            "ticket_type": selected_ticket,
            "ticket_price": TICKET_TYPES[selected_ticket][lang]["name"].split("—")[1].strip()
        }
        
        await message.answer(
            "Для покупки введите ваше Имя и Фамилию:" if lang == "ru" else
            "Bilet almaq üçün ad və soyadınızı daxil edin:" if lang == "az" else
            "To buy tickets, enter your First and Last name:",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        # Not a ticket selection, check if it's a menu item
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
                reply_markup=get_lang_keyboard()
            )

@dp.message(lambda m: user_data.get(m.from_user.id, {}).get("step") == "name")
async def get_name(message: types.Message):
    if not message.text or len(message.text) < 2:
        lang = user_data[message.from_user.id].get("lang", "en")
        await message.answer(
            "Введите корректное имя (минимум 2 символа)" if lang == "ru" else
            "Düzgün ad daxil edin (minimum 2 simvol)" if lang == "az" else
            "Enter valid name (min 2 characters)"
        )
        return
        
    user_data[message.from_user.id]["name"] = message.text
    user_data[message.from_user.id]["step"] = "phone"
    lang = user_data[message.from_user.id].get("lang", "en")
    
    await message.answer(
        "Теперь введите ваш номер телефона:" if lang == "ru" else
        "İndi telefon nömrənizi daxil edin:" if lang == "az" else
        "Now please enter your phone number:"
    )

@dp.message(lambda m: user_data.get(m.from_user.id, {}).get("step") == "phone")
async def get_phone(message: types.Message):
    phone = message.text
    cleaned_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    if len(cleaned_phone) < 9 or (cleaned_phone.startswith('+') and len(cleaned_phone) < 12):
        lang = user_data[message.from_user.id].get("lang", "en")
        await message.answer(
            "Введите корректный номер (минимум 9 цифр)" if lang == "ru" else
            "Düzgün nömrə daxil edin (minimum 9 rəqəm)" if lang == "az" else
            "Enter valid number (min 9 digits)"
        )
        return
    
    user_data[message.from_user.id]["phone"] = cleaned_phone
    user_data[message.from_user.id]["step"] = "confirm"
    lang = user_data[message.from_user.id].get("lang", "en")
    ticket_info = TICKET_TYPES[user_data[message.from_user.id]["ticket_type"]][lang]
    
    await message.answer(
        f"Проверьте данные:\n\n🎟 {ticket_info['name']}\n👤 {user_data[message.from_user.id]['name']}\n📱 {cleaned_phone}" if lang == "ru" else
        f"Məlumatları yoxlayın:\n\n🎟 {ticket_info['name']}\n👤 {user_data[message.from_user.id]['name']}\n📱 {cleaned_phone}" if lang == "az" else
        f"Check details:\n\n🎟 {ticket_info['name']}\n👤 {user_data[message.from_user.id]['name']}\n📱 {cleaned_phone}",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Да" if lang == "ru" else "✅ Bəli" if lang == "az" else "✅ Yes")],
                [KeyboardButton(text="❌ Нет" if lang == "ru" else "❌ Xeyr" if lang == "az" else "❌ No")]
            ],
            resize_keyboard=True
        )
    )

@dp.message(F.text.in_(["✅ Да", "✅ Bəli", "✅ Yes"]))
async def confirm_purchase(message: types.Message):
    if message.from_user.id not in user_data:
        lang = user_lang.get(message.from_user.id, "en")
        await message.answer(
            "Нет активной заявки" if lang == "ru" else
            "Aktiv müraciət yoxdur" if lang == "az" else
            "No active application",
            reply_markup=get_menu_keyboard(lang)
        )
        return
    
    lang = user_data[message.from_user.id].get("lang", "en")
    user_data[message.from_user.id]["step"] = "payment"
    
    await message.answer(
        f"Оплатите {user_data[message.from_user.id]['ticket_price']} на карту: `{PAYMENT_CARD}`\n"
        "и отправьте скриншот оплаты.\n\n"
        f"{TICKET_TYPES[user_data[message.from_user.id]['ticket_type']][lang]['note']}",
        reply_markup=get_menu_keyboard(lang)
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
            reply_markup=get_menu_keyboard(lang)
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
            reply_markup=get_menu_keyboard(lang)
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

@dp.message(Command(commands=["approve", "reject"]))
async def handle_admin_approval(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Extract command and user_id from text like "/approve_12345" or "/reject_12345 reason"
        command_parts = message.text.split('_')
        if len(command_parts) < 2:
            await message.answer("⚠️ Неверный формат команды. Используйте /approve_12345 или /reject_12345 причина")
            return
            
        command = command_parts[0][1:]  # Remove leading slash
        user_id = int(command_parts[1].split()[0])  # Get user_id before any space
        data = pending_approvals.get(user_id)
        
        if not data:
            await message.answer("⚠️ Заявка не найдена")
            return
            
        if command == "approve":
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
            
        elif command == "reject":
            reason = message.text.split(maxsplit=2)[2] if len(message.text.split()) > 2 else (
                "Причина не указана" if data["lang"] == "ru" else
                "Səbəb göstərilməyib" if data["lang"] == "az" else
                "No reason provided"
            )
            
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
        logger.error(f"Admin error: {e}")
        await message.answer("⚠️ Ошибка команды. Формат:\n"
                           "/approve_12345 - подтвердить\n"
                           "/reject_12345 причина - отклонить")

async def main():
    # Start polling (ignore PORT since we're not using webhooks)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
