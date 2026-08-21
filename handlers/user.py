import random
import asyncio
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatAction

from handlers.keyboards import get_main_keyboard, get_settings_inline_keyboard, get_acat_menu_keyboard
from ai_service import ask_gemini_async, reset_user_chat
from database.models import (
    add_user, add_expense, add_expenses_bulk, get_expenses_by_period,
    get_total_spent, get_limits, set_limit, get_monthly_dynamics
)
from services.ai_parser import parse_expense_text, parse_voice_audio, parse_receipt_image
from services.statement_parser import parse_statement_pdf, analyze_statement_dynamics
from services.chart_generator import generate_pie_chart, generate_bar_chart
from config import CATEGORIES, DEFAULT_LIMITS

router = Router()

async def keep_typing(bot, chat_id: int, stop_event: asyncio.Event):
    """Периодически отправляет статус «печатает...» до получения ответа."""
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
        f"👋 Привет, {user.first_name}!\n\n"
        "Я твой персональный **AI-ассистент по контролю финансов, анализу выписок и помощник Google Gemini**! 🤖✨\n\n"
        "💡 **Что я умею:**\n"
        "• ✍️ **Учёт трат**: пишите текстом `Обед 2600`, `Бензин 8000 в Qazaq Oil`, `Wolt 5400`\n"
        "• 📁 **Выписки из банков**: скиньте PDF-файл выписки — я распознаю траты и сравню динамику\n"
        "• 🎙 **Голос и фото чеков**: присылайте голосовые или снимки чеков\n"
        "• 🚨 **Лимиты и бюджет**: защищаю от перерасхода на рестораны и доставки\n"
        "• 🧠 **Диалог с ИИ**: отвечу на любые вопросы и задачи\n"
        "• 📰 **Новости ACAT.KZ**: управление публикациями сайта\n\n"
        "Управляйте через меню внизу 👇"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# 2. Команда /help или кнопка «💬 Помощь»
@router.message(Command("help"))
@router.message(F.text == "💬 Помощь")
async def cmd_help(message: Message):
    text = (
        "📖 **Справка по возможностям:**\n\n"
        "📊 `/stats` или **Расходы за месяц** — круговая диаграмма и структура расходов\n"
        "📈 `/trends` или **Динамика трат** — сравнение месяцев, всплески трат (+%) и экономия (-%)\n"
        "🚨 `/limits` или **Лимиты и бюджет** — просмотр и настройка ограничений (например: `Лимит Рестораны 60000`)\n"
        "📁 **PDF-выписки** — просто отправьте файл документом\n"
        "🧠 **Спросить ИИ** — задать любой общий вопрос нейросети\n"
        "📰 **Новости ACAT.KZ** — панель синхронизации и публикаций новостей\n"
        "✍️ **Быстрый расход**: пишите прямо в чат `Кофе 1500`"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# 3. Меню настроек
@router.message(F.text == "⚙️ Настройки")
async def btn_settings(message: Message):
    text = "⚙️ **Меню настроек бота:**\n\nВыберите действие ниже:"
    await message.answer(text, reply_markup=get_settings_inline_keyboard(), parse_mode="Markdown")

# 4. Кнопка «🧠 Спросить ИИ»
@router.message(F.text == "🧠 Спросить ИИ")
async def btn_ask_ai(message: Message):
    await message.answer(
        "🧠 Я готов! Напишите любой интересующий вас вопрос прямо в чат 👇",
        reply_markup=get_main_keyboard()
    )

# 5. Статистика расходов (/stats)
@router.message(F.text == "📊 Расходы за месяц")
@router.message(Command("stats"))
async def cmd_stats(message: Message):
    user_id = message.from_user.id
    now = datetime.now()
    start_date = now.strftime("%Y-%m-01")
    end_date = now.strftime("%Y-%m-%d")
    
    category_data = get_expenses_by_period(user_id, start_date, end_date)
    total = get_total_spent(user_id, start_date, end_date)
    
    if not category_data or total == 0:
        await message.answer("ℹ️ В этом месяце расходов пока не зафиксировано. Начните добавлять траты текстом, голосом или загрузите выписку!")
        return
        
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

# 6. Динамика и тренды (/trends)
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

# 7. Лимиты и бюджет (/limits)
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

# 8. Загрузка PDF выписки
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

# 9. Голосовые сообщения
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

# 10. Фото чеков
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

# 11. Текстовые сообщения (траты или диалог с ИИ)
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

# 12. Callbacks настроек
@router.callback_query(F.data == "clear_context")
async def cb_clear_context(callback: CallbackQuery):
    reset_user_chat(callback.from_user.id)
    await callback.answer("🧹 Память диалога успешно очищена!", show_alert=True)
    await callback.message.answer("🔄 История общения с ИИ сброшена.")

@router.callback_query(F.data == "check_status")
async def cb_check_status(callback: CallbackQuery):
    await callback.answer("✅ Сервис ИИ активен и готов к работе!", show_alert=True)
