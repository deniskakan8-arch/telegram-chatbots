from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура бота (Reply Keyboard)."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧠 Спросить ИИ"), KeyboardButton(text="💬 Помощь")],
            [KeyboardButton(text="🎲 Случайное число"), KeyboardButton(text="ℹ️ О боте")],
            [KeyboardButton(text="⚙️ Настройки")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Напишите вопрос ИИ или выберите команду..."
    )
    return keyboard

def get_settings_inline_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура для меню настроек."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧹 Очистить память диалога", callback_data="clear_context")],
            [InlineKeyboardButton(text="ℹ️ Статус ИИ", callback_data="check_status")]
        ]
    )
    return keyboard
