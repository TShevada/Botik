# ... (предыдущие импорты остаются без изменений)

# --- Handlers ---
@dp.message(F.text.regexp(r"(Стандарт|Standart|Standard|VIP|Эксклюзив|Eksklüziv|Exclusive).*"))
async def ticket_type_handler(message: types.Message):
    lang = user_lang.get(message.from_user.id, "en")
    
    ticket_type = None
    if "Стандарт" in message.text or "Standart" in message.text or "Standard" in message.text:
        ticket_type = "standard"
    elif "VIP" in message.text:
        ticket_type = "vip"
    elif "Эксклюзив" in message.text or "Eksklüziv" in message.text or "Exclusive" in message.text:
        ticket_type = "exclusive"
    
    if not ticket_type:
        await message.answer("Неверный тип билета" if lang == "ru" else "Yanlış bilet növü" if lang == "az" else "Invalid ticket type")
        return
    
    user_data[message.from_user.id] = {
        "step": "name",
        "lang": lang,
        "ticket_type": ticket_type,
        "ticket_price": TICKET_TYPES[ticket_type][lang]["price"]
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
              f"💳 Сумма: {ticket_info['price']}\n"
              f"👤 Имя: {user_data[message.from_user.id]['name']}\n"
              f"📱 Телефон: {phone}\n\n"
              f"Все верно?",
        "az": f"Məlumatlarınızı yoxlayın:\n\n"
              f"🎟 Bilet növü: {ticket_info['name']}\n"
              f"💳 Məbləğ: {ticket_info['price']}\n"
              f"👤 Ad: {user_data[message.from_user.id]['name']}\n"
              f"📱 Telefon: {phone}\n\n"
              f"Hər şey düzgündür?",
        "en": f"Please confirm your details:\n\n"
              f"🎟 Ticket type: {ticket_info['name']}\n"
              f"💳 Amount: {ticket_info['price']}\n"
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
              "и отправьте скриншот оплаты.",
        "az": f"{user_data[message.from_user.id]['ticket_price']} məbləğini kartla ödəyin: `{PAYMENT_CARD}`\n"
              "və ödəniş skrinşotu göndərin.",
        "en": f"Please pay {user_data[message.from_user.id]['ticket_price']} to card: `{PAYMENT_CARD}`\n"
              "and send payment screenshot."
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
            file = await bot.get_file(photo.file_id)
            path = f"{PHOTOS_DIR}/{message.from_user.id}_{photo.file_id}.jpg"
            await bot.download_file(file.file_path, path)
            
            if save_to_excel(
                message.from_user.id,
                user_data[message.from_user.id]["name"],
                user_data[message.from_user.id]["phone"],
                user_data[message.from_user.id]["ticket_type"],
                user_data[message.from_user.id]["ticket_price"],
                path
            ):
                await notify_admin(
                    message.from_user.id,
                    user_data[message.from_user.id]["name"],
                    user_data[message.from_user.id]["phone"],
                    user_data[message.from_user.id]["ticket_type"],
                    user_data[message.from_user.id]["ticket_price"]
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

# ... (остальной код остается без изменений)
