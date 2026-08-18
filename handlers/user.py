import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatAction
from handlers.keyboards import get_main_keyboard, get_settings_inline_keyboard
from ai_service import ask_gemini_async, reset_user_chat

router = Router()

# 1. Команда /start
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_name = message.from_user.first_name if message.from_user else "друг"
    text = (
        f"👋 Привет, {user_name}! Я твой умный Telegram-бот с искусственным интеллектом **Google Gemini**! 🤖✨\n\n"
        "💡 **Что я умею:**\n"
        "• Отвечать на **любые вопросы** и генерировать тексты/код\n"
        "• Помнить контекст разговора и вести диалог\n"
        "• Быстрые команды по кнопкам внизу 👇\n\n"
        "Просто напиши мне любой вопрос в чат!"
    )
    await message.answer(text, reply_markup=get_main_keyboard())

# 2. Команда /help или кнопка «💬 Помощь»
@router.message(Command("help"))
@router.message(F.text == "💬 Помощь")
async def cmd_help(message: Message):
    text = (
        "📖 **Справка по возможностям бота:**\n\n"
        "🧠 **Искусственный Интеллект**: напишите любой вопрос или задачу (например: *«Объясни теорему Пифагора»* или *«Напиши пост для блога»*).\n\n"
        "🎲 **Случайное число** — генератор случайных чисел от 1 до 100.\n"
        "⚙️ **Настройки** — управление памятью и статусом ИИ.\n"
        "ℹ️ **О боте** — стек технологий проекта."
    )
    await message.answer(text, reply_markup=get_main_keyboard())

# 3. Кнопка «🧠 Спросить ИИ»
@router.message(F.text == "🧠 Спросить ИИ")
async def btn_ask_ai(message: Message):
    await message.answer(
        "🧠 Я готов! Напишите любой интересующий вас вопрос или тему прямо сюда 👇",
        reply_markup=get_main_keyboard()
    )

# 4. Кнопка «🎲 Случайное число»
@router.message(F.text == "🎲 Случайное число")
async def btn_random_num(message: Message):
    num = random.randint(1, 100)
    await message.answer(f"🎲 Ваше случайное число: **{num}**", reply_markup=get_main_keyboard())

# 5. Кнопка «ℹ️ О боте»
@router.message(F.text == "ℹ️ О боте")
async def btn_about(message: Message):
    text = (
        "🤖 **Telegram AI Bot**\n"
        "• **Стек**: Python 3.13, aiogram 3.x (Async)\n"
        "• **ИИ-ядро**: Google Gemini 3.5 Flash-Lite / 3.6 Flash\n"
        "• **Хостинг**: 24/7 Cloud Support (Render / VPS)\n"
        "• **Разработчик**: Denis Kakan"
    )
    await message.answer(text, reply_markup=get_main_keyboard())

# 6. Кнопка «⚙️ Настройки»
@router.message(F.text == "⚙️ Настройки")
async def btn_settings(message: Message):
    await message.answer(
        "⚙️ **Панель настроек бота:**",
        reply_markup=get_settings_inline_keyboard()
    )

# 7. Callback на очистку контекста диалога
@router.callback_query(F.data == "clear_context")
async def callback_clear_context(callback: CallbackQuery):
    reset_user_chat(callback.from_user.id)
    await callback.answer("Память очищена! 🧹", show_alert=False)
    await callback.message.edit_text(
        "🧹 **Память нашего диалога очищена!**\nТеперь нейросеть начинает разговор с чистого листа.",
        reply_markup=get_settings_inline_keyboard()
    )

# 8. Callback на проверку статуса
@router.callback_query(F.data == "check_status")
async def callback_check_status(callback: CallbackQuery):
    await callback.answer("Модуль ИИ активен и готов к работе! 🟢", show_alert=True)

# 9. Обработка всех входящих текстовых сообщений через Google Gemini AI
@router.message(F.text)
async def handle_ai_message(message: Message):
    user_id = message.from_user.id
    prompt = message.text
    
    print(f"📩 [TG Сообщение] от {message.from_user.full_name} ({user_id}): «{prompt}»", flush=True)
    
    # Показываем анимацию «печатает...» в Telegram
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    # Запрашиваем ответ у нейросети асинхронно
    ai_response = await ask_gemini_async(user_id, prompt)
    
    # Отправляем ответ
    try:
        await message.answer(ai_response, parse_mode="Markdown")
    except Exception:
        # Fallback без markdown, если в тексте ИИ спецсимволы разметки
        await message.answer(ai_response)
        
    print(f"📤 [TG Ответ отправлен] для {user_id}", flush=True)
