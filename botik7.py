import os
import logging
import asyncio
import random
import string
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web
from collections import defaultdict

# Configuration
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 1291104906
PORT = int(os.getenv("PORT", "10001"))
PAYMENT_CARD = "4169 7388 9268 3164"

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
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

@dp.message(F.text)
async def handle_ticket_selection(message: types.Message):
    if message.from_user.id in user_data and user_data[message.from_user.id].get("step") in ["name", "phone", "confirm"]:
        return
        
    lang = user_lang.get(message.from_user.id, "en")
    
    if message.text in ["⬅️ Назад", "⬅️ Geri", "⬅️ Back"]:
        await back_handler(message)
        return
    
    selected_ticket = None
    for ticket_type, data in TICKET_TYPES.items():
        if message.text == data[lang]["name"]:
            selected_ticket = ticket_type
            break
    
    if not selected_ticket:
        await message.answer(
            "Неверный тип билета" if lang == "ru" else
            "Yanlış bilet növü" if lang == "az" else
            "Invalid ticket type"
        )
        return
    
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

@dp.message(lambda m: user_data.get(m.from_user.id, {}).get("step") == "name")
async def get_name(message: types.Message):
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
        return
    
    lang = user_data[message.from_user.id].get("lang", "en")
    user_data[message.from_user.id]["step"] = "payment"
    
    await message.answer(
        f"Оплатите {user_data[message.from_user.id]['ticket_price']} на карту: `{PAYMENT_CARD}`\n"
        "и отправьте скриншот оплаты.\n\n"
        f"{TICKET_TYPES[user_data[message.from_user.id]['ticket_type']][lang]['note']}",
        reply_markup=get_menu_keyboard(lang)
    )

@dp.message(F.photo, lambda m: user_data.get(m.from_user.id, {}).get("step") == "payment")
async def handle_payment_photo(message: types.Message):
    lang = user_data[message.from_user.id].get("lang", "en")
    try:
        ticket_id = generate_ticket_id()
        pending_approvals[message.from_user.id] = {
            **user_data[message.from_user.id],
            "photo_id": message.photo[-1].file_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket_id": ticket_id
        }
        
        # Notify admin
        ticket_name = TICKET_TYPES[pending_approvals[message.from_user.id]["ticket_type"]]["ru"]["name"]
        await bot.send_photo(
            ADMIN_ID,
            message.photo[-1].file_id,
            caption=(
                f"🆕 Новая заявка #{ticket_id}\n\n"
                f"👤 [ID:{message.from_user.id}] {user_data[message.from_user.id]['name']}\n"
                f"📱 {user_data[message.from_user.id]['phone']}\n"
                f"🎟 {ticket_name} ({user_data[message.from_user.id]['ticket_price']})\n\n"
                f"Для обработки ответьте:\n"
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

@dp.message(Command(commands=["approve", "reject"]))
async def handle_admin_approval(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        command, user_id = message.text.split('_')
        user_id = int(user_id.split()[0])
        data = pending_approvals.get(user_id)
        
        if not data:
            await message.answer("⚠️ Заявка не найдена")
            return
            
        if command == "/approve":
            approved_tickets[user_id].append({
                "ticket_id": data["ticket_id"],
                "ticket_type": data["ticket_type"],
                "date": data["date"]
            })
            await bot.send_message(
                user_id,
                "✅ Ваш билет подтвержден!" if data["lang"] == "ru" else
                "✅ Biletiniz təsdiqləndi!" if data["lang"] == "az" else
                "✅ Your ticket is approved!"
            )
            await message.answer(f"✅ Заявка #{data['ticket_id']} подтверждена")
            
        elif command == "/reject":
            reason = message.text.split(maxsplit=2)[2] if len(message.text.split()) > 2 else "Не указана"
            await bot.send_message(
                user_id,
                f"❌ Заявка отклонена. Причина: {reason}" if data["lang"] == "ru" else
                f"❌ Müraciət rədd edildi. Səbəb: {reason}" if data["lang"] == "az" else
                f"❌ Application rejected. Reason: {reason}"
            )
            await message.answer(f"❌ Заявка #{data['ticket_id']} отклонена")
        
        del pending_approvals[user_id]
        
    except Exception as e:
        logger.error(f"Admin error: {e}")
        await message.answer("⚠️ Ошибка команды")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
