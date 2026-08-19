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
    user_name = message.from_user.first_name if message.from_user else "друг"
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
    prompt = message.text
    
    print(f"📩 [TG Сообщение] от {message.from_user.full_name} ({user_id}): «{prompt}»", flush=True)
    
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
        
    print(f"📤 [TG Ответ отправлен] для {user_id}", flush=True)
