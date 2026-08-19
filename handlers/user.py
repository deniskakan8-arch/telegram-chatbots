import asyncio
import random
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatAction

from ai_service import ask_gemini_async, reset_user_chat
from handlers.keyboards import get_main_keyboard, get_settings_inline_keyboard

router = Router()

async def keep_typing(bot: Bot, chat_id: int, stop_event: asyncio.Event):
    """Фоновая анимация 'печатает...' во время ожидания ответа ИИ."""
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(4.0)
        except Exception:
            break

# 1. Команда /start
@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    add_user(user.id, user.username, user.first_name)
    
    current_limits = get_limits(user.id)
    if not current_limits:
        for cat, limit in DEFAULT_LIMITS.items():
            set_limit(user.id, cat, limit)
            
    text = (
        f"👋 Привет, {user_name}! Я твой умный Telegram-ассистент с искусственным интеллектом **Google Gemini**! 🤖✨\n\n"
        "💡 **Что я умею:**\n"
        "• 📰 **Управлять новостями ACAT.KZ** (поиск на Informburo, авто-вёрстка и публикация)\n"
        "• 🧠 Отвечать на любые вопросы и генерировать тексты через ИИ\n"
        "• 💬 Помнить контекст диалога\n"
        "• ⚡ Быстрые команды по кнопкам внизу 👇\n\n"
        "Просто напиши мне любой вопрос или нажми **«📰 Новости ACAT.KZ»**!"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# 2. Команда /help или кнопка «💬 Помощь»
@router.message(Command("help"))
@router.message(F.text == "💬 Помощь")
async def cmd_help(message: Message):
    text = (
        "📖 **Справка по возможностям бота:**\n\n"
        "📰 **Новости ACAT.KZ** — поиск юридических карточек на Informburo, просмотр кандидатов и публикация на сайт www.acat.kz в 1 клик.\n\n"
        "🧠 **Искусственный Интеллект**: напишите любой вопрос или задачу (например: *«Объясни квантовую физику»* или *«Напиши план тренировок»*).\n\n"
        "🎲 **Случайное число** — генератор случайных чисел от 1 до 100.\n"
        "⚙️ **Настройки** — управление памятью диалога и сброс контекста.\n"
        "ℹ️ **О боте** — информация о стеке технологий."
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# 3. Кнопка «🧠 Спросить ИИ»
@router.message(F.text == "🧠 Спросить ИИ")
async def btn_ask_ai(message: Message):
    await message.answer(
        "🧠 Я готов! Напишите любой интересующий вас вопрос прямо в чат 👇",
        reply_markup=get_main_keyboard()
    )

# 4. Кнопка «🎲 Случайное число»
@router.message(F.text == "🎲 Случайное число")
async def btn_random_num(message: Message):
    num = random.randint(1, 100)
    await message.answer(f"🎲 Ваше случайное число: **{num}**", reply_markup=get_main_keyboard(), parse_mode="Markdown")

# 5. Кнопка «ℹ️ О боте»
@router.message(F.text == "ℹ️ О боте")
async def btn_about(message: Message):
    text = (
        "🤖 **Telegram AI & Automation Bot**\n"
        "• **Стек**: Python 3.13, aiogram 3.x (Async)\n"
        "• **ИИ-модель**: Google Gemini Flash-Lite\n"
        "• **Интеграция**: FastEdit CMS (acat.kz) & Informburo Cards Sync\n"
        "• **Хостинг**: 24/7 Cloud Support (Render / VPS)\n"
        "• **Разработчик**: Denis Kakan"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# 6. Кнопка «⚙️ Настройки»
@router.message(F.text == "⚙️ Настройки")
async def btn_settings(message: Message):
    await message.answer(
        "⚙️ **Панель настроек бота:**",
        reply_markup=get_settings_inline_keyboard(),
        parse_mode="Markdown"
    )

# 7. Callback на очистку контекста диалога
@router.callback_query(F.data == "clear_context")
async def callback_clear_context(callback: CallbackQuery):
    reset_user_chat(callback.from_user.id)
    await callback.answer("Память очищена! 🧹", show_alert=False)
    await callback.message.edit_text(
        "🧹 **Память нашего диалога очищена!**\nТеперь нейросеть начинает разговор с чистого листа.",
        reply_markup=get_settings_inline_keyboard(),
        parse_mode="Markdown"
    )

# 8. Callback на проверку статуса
@router.callback_query(F.data == "check_status")
async def callback_check_status(callback: CallbackQuery):
    await callback.answer("Модуль ИИ активен и готов к работе! 🟢", show_alert=True)

# 9. Обработка всех входящих текстовых сообщений через Google Gemini AI
@router.message(F.text)
async def handle_ai_message(message: Message):
    user_id = message.from_user.id
    now = datetime.now()
    start_date = now.strftime("%Y-%m-01")
    end_date = now.strftime("%Y-%m-%d")
    
    category_data = get_expenses_by_period(user_id, start_date, end_date)
    total = get_total_spent(user_id, start_date, end_date)
    
    stop_typing_event = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(message.bot, message.chat.id, stop_typing_event))
    
    try:
        ai_response = await ask_gemini_async(user_id, prompt)
    finally:
        stop_typing_event.set()
        typing_task.cancel()
    
    try:
        await message.answer(ai_response, parse_mode="Markdown")
    except Exception:
        await message.answer(ai_response)
        
    lines = [f"📊 **Расходы за текущий месяц ({now.strftime('%m.%Y')}):**\n"]
    for cat, amt, count in category_data:
        pct = (amt / total) * 100
        lines.append(f"• {cat}: **{int(amt):,} ₸** ({pct:.1f}%) — {count} оплат")
    lines.append(f"\n💰 **ИТОГО за месяц:** **{int(total):,} ₸**")
    
    try:
        chart_buf = generate_pie_chart(category_data, title=f"Расходы {now.strftime('%m.%Y')}")
        photo = BufferedInputFile(chart_buf.getvalue(), filename="chart.png")
        await message.answer_photo(photo=photo, caption="\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await message.answer("\n".join(lines), parse_mode="Markdown")

# 5. Динамика и тренды (/trends)
@router.message(F.text == "📈 Динамика трат")
@router.message(Command("trends"))
async def cmd_trends(message: Message):
    user_id = message.from_user.id
    dynamics = get_monthly_dynamics(user_id)
    
    if len(dynamics) < 2:
        await message.answer(
            "📈 Для анализа динамики нужно хотя бы 2 периода данных.\n"
            "Вы можете скинуть мне PDF-выписку за прошлые месяцы, и я построю полный сравнительный отчёт!"
        )
        return
        
    months = list(dynamics.keys())
    prev_m = months[-2]
    curr_m = months[-1]
    
    analysis_text = analyze_statement_dynamics(dynamics[prev_m], dynamics[curr_m])
    
    try:
        bar_buf = generate_bar_chart(dynamics)
        photo = BufferedInputFile(bar_buf.getvalue(), filename="dynamics.png")
        await message.answer_photo(photo=photo, caption=analysis_text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(analysis_text, parse_mode="Markdown")

# 6. Лимиты и бюджет (/limits)
@router.message(F.text == "🚨 Лимиты и бюджет")
@router.message(Command("limits"))
async def cmd_limits(message: Message):
    user_id = message.from_user.id
    now = datetime.now()
    start_date = now.strftime("%Y-%m-01")
    end_date = now.strftime("%Y-%m-%d")
    
    limits = get_limits(user_id)
    if not limits:
        limits = DEFAULT_LIMITS
        for cat, lim in limits.items():
            set_limit(user_id, cat, lim)
            
    category_data = dict([(c[0], c[1]) for c in get_expenses_by_period(user_id, start_date, end_date)])
    
    lines = ["🚨 **Контроль лимитов на месяц:**\n"]
    for cat, monthly_limit in limits.items():
        spent = category_data.get(cat, 0.0)
        pct = (spent / monthly_limit) * 100 if monthly_limit > 0 else 0
        status_icon = "🟢" if pct < 80 else ("🟡" if pct < 100 else "🔴")
        lines.append(
            f"{status_icon} **{cat}**:\n"
            f"   Израсходовано: **{int(spent):,} ₸** из **{int(monthly_limit):,} ₸** ({pct:.1f}%)\n"
            f"   Остаток: **{int(max(0, monthly_limit - spent)):,} ₸**\n"
        )
    lines.append("💡 *Чтобы изменить лимит, напишите:* `Лимит Рестораны 60000`")
    await message.answer("\n".join(lines), parse_mode="Markdown")

# 7. Загрузка PDF выписки
@router.message(F.text == "📁 Загрузить выписку")
async def btn_upload_statement(message: Message):
    await message.answer("📁 Просто прикрепите и отправьте мне файл банковской выписки в формате **PDF**.")

@router.message(F.document)
async def handle_document(message: Message):
    doc = message.document
    if not doc.file_name.lower().endswith(".pdf"):
        await message.answer("⚠️ Пожалуйста, отправьте банковскую выписку в формате **PDF**.")
        return
        
    status_msg = await message.answer("⏳ Анализирую выписку и извлекаю транзакции с помощью AI...")
    
    file = await message.bot.get_file(doc.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    
    parsed_items = parse_statement_pdf(file_bytes.read())
    
    if not parsed_items:
        await status_msg.edit_text("❌ Не удалось извлечь расходные операции из этого PDF. Проверьте формат выписки.")
        return
        
    records = []
    total_imported = 0.0
    for item in parsed_items:
        amt = float(item.get("amount", 0))
        cat = item.get("category", "📦 Прочее")
        merchant = item.get("merchant", "Выписка")
        dt = item.get("date", datetime.now().strftime("%Y-%m-%d"))
        records.append((amt, cat, merchant, dt, "statement"))
        total_imported += amt
        
    add_expenses_bulk(message.from_user.id, records)
    
    dynamics = get_monthly_dynamics(message.from_user.id)
    summary_report = ""
    if len(dynamics) >= 2:
        months = list(dynamics.keys())
        summary_report = "\n\n" + analyze_statement_dynamics(dynamics[months[-2]], dynamics[months[-1]])
        
    res_text = (
        f"✅ **Выписка успешно обработана!**\n\n"
        f"📥 Загружено транзакций: **{len(records)}** шт.\n"
        f"💰 Общая сумма трат: **{int(total_imported):,} ₸**"
        f"{summary_report}"
    )
    await status_msg.edit_text(res_text, parse_mode="Markdown")

# 8. Голосовые сообщения
@router.message(F.voice)
async def handle_voice(message: Message):
    status_msg = await message.answer("🎙 Слушаю и распознаю голосовое...")
    file = await message.bot.get_file(message.voice.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    
    data = parse_voice_audio(file_bytes.read())
    if not data.get("is_expense") or data.get("amount", 0) <= 0:
        await status_msg.edit_text(f"🗣 Распознано: *\"{data.get('transcript', '')}\"*\nНе удалось найти сумму расхода. Попробуйте сказать, например: *«Обед 2600»*.")
        return
        
    amt = float(data["amount"])
    cat = data["category"]
    comment = data.get("comment", "")
    
    add_expense(message.from_user.id, amt, cat, comment, source="voice")
    
    await status_msg.edit_text(
        f"✅ **Расход добавлен из голоса!**\n\n"
        f"🗣 *\"{data.get('transcript', '')}\"*\n"
        f"💰 Сумма: **{int(amt):,} ₸**\n"
        f"📂 Категория: **{cat}**\n"
        f"📝 Заметка: {comment}",
        parse_mode="Markdown"
    )

# 9. Фото чеков
@router.message(F.photo)
async def handle_photo(message: Message):
    status_msg = await message.answer("🔍 Распознаю чек с фотографии...")
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    
    data = parse_receipt_image(file_bytes.read())
    if not data.get("is_receipt") or data.get("amount", 0) <= 0:
        await status_msg.edit_text("❌ Не удалось распознать сумму на чеке. Попробуйте сфотографировать чётче.")
        return
        
    amt = float(data["amount"])
    cat = data["category"]
    comment = data.get("comment", "Чек")
    
    add_expense(message.from_user.id, amt, cat, comment, source="receipt")
    
    await status_msg.edit_text(
        f"🧾 **Чек успешно распознан и записан!**\n\n"
        f"💰 Сумма: **{int(amt):,} ₸**\n"
        f"📂 Категория: **{cat}**\n"
        f"📝 Описание: {comment}",
        parse_mode="Markdown"
    )

# 10. Текстовые сообщения (траты или диалог с ИИ)
@router.message(F.text)
async def handle_text(message: Message):
    text = message.text.strip()
    
    # Изменение лимитов
    if text.lower().startswith("лимит"):
        parts = text.split()
        if len(parts) >= 3 and parts[-1].isdigit():
            lim_val = float(parts[-1])
            target_cat_part = " ".join(parts[1:-1]).lower()
            matched_cat = None
            for c in CATEGORIES:
                if target_cat_part in c.lower():
                    matched_cat = c
                    break
            if matched_cat:
                set_limit(message.from_user.id, matched_cat, lim_val)
                await message.answer(f"✅ Лимит для **{matched_cat}** установлен: **{int(lim_val):,} ₸ / месяц**", parse_mode="Markdown")
                return
                
    # Парсим на предмет расхода
    data = parse_expense_text(text)
    if data.get("is_expense") and data.get("amount", 0) > 0:
        amt = float(data["amount"])
        cat = data.get("category", "📦 Прочее")
        comment = data.get("comment", text)
        
        add_expense(message.from_user.id, amt, cat, comment, source="manual")
        
        now = datetime.now()
        start_date = now.strftime("%Y-%m-01")
        end_date = now.strftime("%Y-%m-%d")
        limits = get_limits(message.from_user.id)
        limit_alert = ""
        
        if cat in limits:
            total_cat = get_total_spent(message.from_user.id, start_date, end_date)
            lim = limits[cat]
            if total_cat > lim:
                limit_alert = f"\n\n🚨 **Внимание! Лимит на месяц превышен на {int(total_cat - lim):,} ₸!**"
            elif total_cat >= lim * 0.8:
                limit_alert = f"\n\n⚠️ **Осталось всего {int(lim - total_cat):,} ₸ до исчерпания месячного лимита!**"
                
        await message.answer(
            f"✅ **Записано:** **{int(amt):,} ₸**\n"
            f"📂 Категория: **{cat}**\n"
            f"📝 Заметка: {comment}{limit_alert}",
            parse_mode="Markdown"
        )
    else:
        # Если это не трата, отвечаем как ИИ-ассистент
        stop_event = asyncio.Event()
        typing_task = asyncio.create_task(keep_typing(message.bot, message.chat.id, stop_event))
        try:
            ai_response = await ask_gemini_async(message.from_user.id, text)
            await message.answer(ai_response)
        finally:
            stop_event.set()
            await typing_task

# 11. Callback сброса диалога
@router.callback_query(F.data == "reset_chat")
async def cb_reset_chat(callback: CallbackQuery):
    reset_user_chat(callback.from_user.id)
    await callback.answer("🧹 Память диалога успешно очищена!", show_alert=True)
    await callback.message.answer("🔄 История общения с ИИ сброшена.")
