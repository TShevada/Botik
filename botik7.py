import os
import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web
from collections import defaultdict

# --- Configuration ---
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Set in Render environment
ADMIN_ID = 1291104906  # Your Telegram ID
PORT = int(os.getenv("PORT", "10001"))  # Try 10001-10025
PAYMENT_CARD = "4169 7388 9268 3164"

# --- Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# --- Data Storage ---
user_lang = {}
user_data = {}
pending_approvals = {}
approved_tickets = defaultdict(list)

# --- Ticket Types ---
TICKET_TYPES = {
    "standard": {
        "az": {
            "name": "Standard — 20 AZN",
            "desc": "• Qarşılama kokteylləri\n• Fan Zonası",
            "note": "❗️Nəzərinizə çatdırırıq ki, biletlər alındıqdan sonra geri qaytarılmır"
        },
        "ru": {
            "name": "Стандарт — 20 AZN", 
            "desc": "• Приветственные коктейли\n• Fan Zone",
            "note": "❗️Обратите внимание, что билеты не подлежат возврату после покупки"
        },
        "en": {
            "name": "Standard — 20 AZN",
            "desc": "• Welcome cocktails\n• Fan Zone",
            "note": "❗️Please note that tickets cannot be refunded after purchase"
        }
    },
    "vip_single": {
        "az": {
            "name": "VIP (Fərdi) — 40 AZN",
            "desc": "• Fərdi masa yeri\n• Qarşılama kokteyli\n• Yerlərin sayı məhduddur",
            "note": "❗️Nəzərinizə çatdırırıq ki, biletlər alındıqdan sonra geri qaytarılmır"
        },
        "ru": {
            "name": "VIP (Индивидуальный) — 40 AZN",
            "desc": "• Индивидуальное место\n• Приветственный коктейль\n• Количество мест ограничено",
            "note": "❗️Обратите внимание, что билеты не подлежат возврату после покупки"
        },
        "en": {
            "name": "VIP (Single) — 40 AZN", 
            "desc": "• Individual seat\n• Welcome cocktail\n• Limited seats available",
            "note": "❗️Please note that tickets cannot be refunded after purchase"
        }
    },
    "vip_table": {
        "az": {
            "name": "VIP (Masa) — 160 AZN",
            "desc": "• 4 nəfərlik ayrıca masa\n• Bütün şirkət üçün qarşılama kokteylləri\n• Yerlərin sayı məhduddur",
            "note": "❗️Nəzərinizə çatdırırıq ki, biletlər alındıqdan sonra geri qaytarılmır"
        },
        "ru": {
            "name": "VIP (Столик) — 160 AZN",
            "desc": "• Столик на 4 персоны\n• Приветственные коктейли для всей компании\n• Количество мест ограничено", 
            "note": "❗️Обратите внимание, что билеты не подлежат возврату после покупки"
        },
        "en": {
            "name": "VIP (Table) — 160 AZN",
            "desc": "• Table for 4 people\n• Welcome cocktails for whole group\n• Limited seats available",
            "note": "❗️Please note that tickets cannot be refunded after purchase"
        }
    },
    "exclusive_table": {
        "az": {
            "name": "Exclusive (Masa) — 240 AZN",
            "desc": "• DJ masasının yanında giriş imkanı\n• 4 nəfərlik ayrıca masa\n• Bütün şirkət üçün qarşılama kokteylləri\n• Yerlərin sayı məhduddur",
            "note": "❗️Nəzərinizə çatdırırıq ki, biletlər alındıqdan sonra geri qaytarılmır"
        },
        "ru": {
            "name": "Exclusive (Столик) — 240 AZN",
            "desc": "• Доступ к DJ-зоне\n• Столик на 4 персоны\n• Приветственные коктейли для всей компании\n• Количество мест ограничено",
            "note": "❗️Обратите внимание, что билеты не подлежат возврату после покупки"
        },
        "en": {
            "name": "Exclusive (Table) — 240 AZN",
            "desc": "• DJ area access\n• Table for 4 people\n• Welcome cocktails for whole group\n• Limited seats available",
            "note": "❗️Please note that tickets cannot be refunded after purchase"
        }
    }
}

# --- Web Server for Render ---
async def health_check(request):
    return web.Response(text="Bot is running")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logger.info(f"🌐 Health check running on port {PORT}")
    except OSError as e:
        logger.error(f"Port {PORT} unavailable, trying fallback...")
        site = web.TCPSite(runner, "0.0.0.0", 10002)  # Fallback port
        await site.start()

# --- Helper Functions ---
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

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Последние заявки", callback_data="admin_last_orders")],
        [InlineKeyboardButton(text="🔍 Поиск по ID", callback_data="admin_search"),
         InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_refresh")]
    ])

# [Previous imports and configuration remain the same...]

# --- Handlers ---
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
    await message.answer(events_info)

@dp.message(F.text.in_(["📞 Контакты", "📞 Əlaqə", "📞 Contacts"]))
async def contacts_handler(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    contact_info = {
        "ru": "📞 Контакты:\nТелефон: +994 10 531 24 06",
        "az": "📞 Əlaqə:\nTelefon: +994 10 531 24 06",
        "en": "📞 Contacts:\nPhone: +994 10 531 24 06"
    }[lang]
    await message.answer(contact_info)

@dp.message(F.text.in_(["🌐 Сменить язык", "🌐 Dil dəyiş", "🌐 Change language"]))
async def change_lang_handler(message: types.Message):
    await message.answer(
        "Выберите язык / Select language / Dil seçin:",
        reply_markup=get_lang_keyboard()
    )

@dp.message(F.text.in_(["🎫 Билеты", "🎫 Biletlər", "🎫 Tickets"]))
async def tickets_menu_handler(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    await message.answer(
        "Выберите тип билета:" if lang == "ru" else "Bilet növünü seçin:" if lang == "az" else "Select ticket type:",
        reply_markup=get_ticket_type_keyboard(lang)
    )

@dp.message(lambda message: any(
    message.text.startswith(ticket[lang]["name"].split("—")[0].strip())
    for ticket in TICKET_TYPES.values()
    for lang in ["az", "ru", "en"]
))
async def ticket_type_handler(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    
    # Find which ticket type was selected
    ticket_type = None
    for t_type, t_data in TICKET_TYPES.items():
        if message.text.startswith(t_data[lang]["name"].split("—")[0].strip()):
            ticket_type = t_type
            break
    
    if not ticket_type:
        await message.answer("Неверный тип билета" if lang == "ru" else "Yanlış bilet növü" if lang == "az" else "Invalid ticket type")
        return
    
    user_data[message.from_user.id] = {
        "step": "name",
        "lang": lang,
        "ticket_type": ticket_type,
        "ticket_price": TICKET_TYPES[ticket_type][lang]["name"].split("—")[1].strip()
    }
    
    prompt = {
        "ru": "Для покупки билетов введите ваше Имя и Фамилию:",
        "az": "Bilet almaq üçün ad və soyadınızı daxil edin:",
        "en": "To buy tickets, please enter your First and Last name:"
    }[lang]
    
    await message.answer(prompt, reply_markup=types.ReplyKeyboardRemove())

@dp.message(lambda m: user_data.get(m.from_user.id, {}).get("step") == "name")
async def get_name(message: types.Message):
    user_data[message.from_user.id]["name"] = message.text
    user_data[message.from_user.id]["step"] = "phone"
    lang = user_data[message.from_user.id].get("lang", "en")
    
    prompt = {
        "ru": "Теперь введите ваш номер телефона:",
        "az": "İndi telefon nömrənizi daxil edin:",
        "en": "Now please enter your phone number:"
    }[lang]
    
    await message.answer(prompt)

@dp.message(lambda m: user_data.get(m.from_user.id, {}).get("step") == "phone")
async def get_phone(message: types.Message):
    phone = message.text
    if not phone.replace('+', '').isdigit() or len(phone) < 9:
        lang = user_data[message.from_user.id].get("lang", "en")
        error_msg = {
            "ru": "Пожалуйста, введите корректный номер телефона",
            "az": "Zəhmət olmasa, düzgün telefon nömrəsi daxil edin",
            "en": "Please enter a valid phone number"
        }[lang]
        await message.answer(error_msg)
        return
    
    user_data[message.from_user.id]["phone"] = phone
    user_data[message.from_user.id]["step"] = "confirm"
    lang = user_data[message.from_user.id].get("lang", "en")
    
    ticket_type = user_data[message.from_user.id]["ticket_type"]
    ticket_info = TICKET_TYPES[ticket_type][lang]
    
    confirmation = {
        "ru": f"Проверьте ваши данные:\n\n"
              f"🎟 Тип билета: {ticket_info['name']}\n"
              f"💳 Сумма: {ticket_info['name'].split('—')[1].strip()}\n"
              f"👤 Имя: {user_data[message.from_user.id]['name']}\n"
              f"📱 Телефон: {phone}\n\n"
              f"Все верно?",
        "az": f"Məlumatlarınızı yoxlayın:\n\n"
              f"🎟 Bilet növü: {ticket_info['name']}\n"
              f"💳 Məbləğ: {ticket_info['name'].split('—')[1].strip()}\n"
              f"👤 Ad: {user_data[message.from_user.id]['name']}\n"
              f"📱 Telefon: {phone}\n\n"
              f"Hər şey düzgündür?",
        "en": f"Please confirm your details:\n\n"
              f"🎟 Ticket type: {ticket_info['name']}\n"
              f"💳 Amount: {ticket_info['name'].split('—')[1].strip()}\n"
              f"👤 Name: {user_data[message.from_user.id]['name']}\n"
              f"📱 Phone: {phone}\n\n"
              f"Is everything correct?"
    }[lang]
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да" if lang == "ru" else "✅ Bəli" if lang == "az" else "✅ Yes")],
            [KeyboardButton(text="❌ Нет" if lang == "ru" else "❌ Xeyr" if lang == "az" else "❌ No")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(confirmation, reply_markup=keyboard)

@dp.message(F.text.in_(["✅ Да", "✅ Bəli", "✅ Yes"]))
async def confirm_purchase(message: types.Message):
    if message.from_user.id not in user_data:
        return
    
    lang = user_data[message.from_user.id].get("lang", "en")
    user_data[message.from_user.id]["step"] = "payment"
    
    payment_info = {
        "ru": f"Оплатите {user_data[message.from_user.id]['ticket_price']} на карту: `{PAYMENT_CARD}`\n"
              "и отправьте скриншот оплаты.\n\n"
              f"{TICKET_TYPES[user_data[message.from_user.id]['ticket_type']][lang]['note']}",
        "az": f"{user_data[message.from_user.id]['ticket_price']} məbləğini kartla ödəyin: `{PAYMENT_CARD}`\n"
              "və ödəniş skrinşotu göndərin.\n\n"
              f"{TICKET_TYPES[user_data[message.from_user.id]['ticket_type']][lang]['note']}",
        "en": f"Please pay {user_data[message.from_user.id]['ticket_price']} to card: `{PAYMENT_CARD}`\n"
              "and send payment screenshot.\n\n"
              f"{TICKET_TYPES[user_data[message.from_user.id]['ticket_type']][lang]['note']}"
    }[lang]
    
    await message.answer(payment_info, reply_markup=get_menu_keyboard(lang))

@dp.message(F.text.in_(["❌ Нет", "❌ Xeyr", "❌ No"]))
async def cancel_purchase(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    if message.from_user.id in user_data:
        del user_data[message.from_user.id]
    
    msg = {
        "ru": "Заказ отменен. Можете начать заново.",
        "az": "Sifariş ləğv edildi. Yenidən başlaya bilərsiniz.",
        "en": "Order canceled. You can start again."
    }[lang]
    
    await message.answer(msg, reply_markup=get_menu_keyboard(lang))

@dp.message(lambda m: user_data.get(m.from_user.id, {}).get("step") == "payment")
async def handle_payment(message: types.Message):
    lang = user_data[message.from_user.id].get("lang", "en")
    
    if message.photo:
        try:
            photo = message.photo[-1]
            user_id = message.from_user.id
            data = user_data[user_id]
            
            # Store the pending approval
            pending_approvals[user_id] = {
                "name": data["name"],
                "phone": data["phone"],
                "ticket_type": data["ticket_type"],
                "ticket_price": data["ticket_price"],
                "photo_id": photo.file_id,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "approved": None
            }
            
            # Notify admin
            await notify_admin(
                user_id,
                data["name"],
                data["phone"],
                data["ticket_type"],
                data["ticket_price"],
                photo.file_id
            )
            
            confirmation = {
                "ru": "Спасибо! Ваша заявка на рассмотрении.",
                "az": "Təşəkkürlər! Müraciətiniz nəzərdən keçirilir.",
                "en": "Thank you! Your application is under review."
            }[lang]
            
            await message.answer(confirmation, reply_markup=get_menu_keyboard(lang))
            del user_data[message.from_user.id]
            
        except Exception as e:
            logger.error(f"Payment processing error: {e}")
            error_msg = {
                "ru": "Ошибка обработки платежа, попробуйте снова",
                "az": "Ödəniş emalı xətası, yenidən cəhd edin",
                "en": "Payment processing error, please try again"
            }[lang]
            await message.answer(error_msg)
    else:
        prompt = {
            "ru": "Пожалуйста, отправьте скриншот оплаты.",
            "az": "Zəhmət olmasa, ödəniş skrinşotu göndərin.",
            "en": "Please send the payment screenshot."
        }[lang]
        await message.answer(prompt)

@dp.message(Command("admin"))
async def admin_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён!")
        return
        
    await message.answer(
        "🛠 *Панель администратора*",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("admin_"))
async def handle_admin_callbacks(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён!")
        return
    
    try:
        action = callback.data.split('_')[1]
        
        if action == "last_orders":
            if not pending_approvals:
                await callback.message.edit_text("📭 Нет заявок на рассмотрении", reply_markup=get_admin_keyboard())
                return
                
            report = "📋 *Последние заявки:*\n\n"
            for user_id, data in list(pending_approvals.items())[-5:]:
                report += (
                    f"🔹 *ID:* {user_id}\n"
                    f"👤 *{data['name']}*\n"
                    f"📞 `{data['phone']}`\n"
                    f"🎟 {data['ticket_type']} ({data['ticket_price']})\n"
                    f"🕒 {data['date']}\n"
                    "━━━━━━━━━━━━━━\n"
                )
            await callback.message.edit_text(report, reply_markup=get_admin_keyboard())
            
        elif action == "search":
            await callback.message.answer("Введите ID пользователя:")
            admin_pending_actions[callback.from_user.id] = "waiting_for_id"
            
        elif action == "refresh":
            await callback.message.edit_text(
                "🛠 *Панель администратора*",
                reply_markup=get_admin_keyboard(),
                parse_mode="Markdown"
            )
            
        await callback.answer()
    except Exception as e:
        logger.error(f"Admin callback error: {e}")
        await callback.answer("⚠️ Произошла ошибка")

@dp.message(lambda m: admin_pending_actions.get(m.from_user.id) == "waiting_for_id")
async def handle_admin_search(message: types.Message):
    if not is_admin(message.from_user.id):
        return
        
    try:
        user_id = int(message.text)
        data = pending_approvals.get(user_id)
        
        if not data:
            await message.answer("❌ Заявка не найдена")
        else:
            report = (
                f"🔍 *Найдена заявка:*\n\n"
                f"👤 *{data['name']}*\n"
                f"📞 `{data['phone']}`\n"
                f"🎟 {data['ticket_type']} ({data['ticket_price']})\n"
                f"🕒 {data['date']}\n\n"
                f"Ответьте на это сообщение командой:\n"
                f"/accept - подтвердить\n"
                f"/reject [причина] - отклонить"
            )
            await message.answer(report, parse_mode="Markdown")
            
    except ValueError:
        await message.answer("❌ Введите числовой ID")
    finally:
        admin_pending_actions.pop(message.from_user.id, None)

@dp.message(Command("accept"))
async def accept_request(message: types.Message):
    if not is_admin(message.from_user.id):
        return
        
    if not message.reply_to_message:
        await message.answer("ℹ️ Ответьте на сообщение с заявкой для подтверждения")
        return
        
    try:
        text = message.reply_to_message.text
        user_id = int(text.split("ID:")[1].split("\n")[0].strip())
        
        if user_id in pending_approvals:
            # Move to approved tickets
            approved_tickets[user_id] = pending_approvals[user_id]
            approved_tickets[user_id]["approved"] = True
            del pending_approvals[user_id]
            
            await message.answer(f"✅ Заявка {user_id} подтверждена")
            await bot.send_message(
                user_id,
                "🎉 Ваша заявка подтверждена! Билет активен."
            )
        else:
            await message.answer("⚠️ Заявка не найдена в ожидающих")
    except Exception as e:
        logger.error(f"Accept error: {e}")
        await message.answer("❌ Ошибка подтверждения")

@dp.message(Command("reject"))
async def reject_request(message: types.Message):
    if not is_admin(message.from_user.id):
        return
        
    if not message.reply_to_message:
        await message.answer("ℹ️ Ответьте на сообщение с заявкой для отклонения")
        return
        
    try:
        text = message.reply_to_message.text
        user_id = int(text.split("ID:")[1].split("\n")[0].strip())
        reason = message.text.split("/reject")[1].strip() if len(message.text.split("/reject")) > 1 else "не указана"
        
        if user_id in pending_approvals:
            pending_approvals[user_id]["approved"] = False
            
            await message.answer(f"❌ Заявка {user_id} отклонена")
            await bot.send_message(
                user_id,
                f"⚠️ Ваша заявка отклонена. Причина: {reason}"
            )
            del pending_approvals[user_id]
        else:
            await message.answer("⚠️ Заявка не найдена в ожидающих")
    except Exception as e:
        logger.error(f"Reject error: {e}")
        await message.answer("❌ Ошибка отклонения")

async def notify_admin(user_id: int, name: str, phone: str, ticket_type: str, ticket_price: str, photo_id: str):
    try:
        # Send photo first
        await bot.send_photo(
            ADMIN_ID,
            photo_id,
            caption=(
                f"🆕 *Новая заявка на билет*\n\n"
                f"👤 ID: {user_id}\n"
                f"📛 Имя: {name}\n"
                f"📱 Телефон: `{phone}`\n"
                f"🎫 Тип: {ticket_type}\n"
                f"💵 Сумма: {ticket_price}\n"
                f"🕒 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Ответьте на это сообщение командой:\n"
                f"/accept - подтвердить\n"
                f"/reject [причина] - отклонить"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")

@dp.message()
async def handle_unmatched_messages(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("ℹ️ Используйте /admin для управления ботом")
    else:
        lang = user_lang.get(message.from_user.id, "en")
        response = {
            "ru": "Пожалуйста, используйте кнопки меню",
            "az": "Zəhmət olmasa menyu düymələrindən istifadə edin",
            "en": "Please use the menu buttons"
        }[lang]
        await message.answer(response, reply_markup=get_menu_keyboard(lang))

# --- Main ---
async def main():
    await run_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN not set in environment variables!")
    logging.info("Starting bot...")
    asyncio.run(main())
