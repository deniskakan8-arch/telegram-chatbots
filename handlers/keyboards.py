from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import CATEGORIES

def get_main_keyboard():
    kb = [
        [KeyboardButton(text="📊 Статистика за месяц"), KeyboardButton(text="📈 Динамика трат")],
        [KeyboardButton(text="🚨 Лимиты и бюджет"), KeyboardButton(text="📁 Загрузить выписку")],
        [KeyboardButton(text="🧠 Спросить ИИ"), KeyboardButton(text="💬 Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_settings_inline_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🔄 Сбросить память диалога", callback_data="reset_chat")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
