from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура бота (Reply Keyboard)."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧠 Спросить ИИ"), KeyboardButton(text="📰 Новости ACAT.KZ")],
            [KeyboardButton(text="🎲 Случайное число"), KeyboardButton(text="ℹ️ О боте")],
            [KeyboardButton(text="💬 Помощь"), KeyboardButton(text="⚙️ Настройки")]
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

def get_acat_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное инлайн-меню управления новостями acat.kz."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Кандидаты с Informburo", callback_data="acat_candidates")],
            [InlineKeyboardButton(text="🚀 Опубликовать следующую", callback_data="acat_publish_next")],
            [InlineKeyboardButton(text="🌐 Опубликованные на сайте", callback_data="acat_published")]
        ]
    )
    return keyboard

def get_confirm_publish_keyboard(slug: str) -> InlineKeyboardMarkup:
    """Инлайн-клавиатура подтверждения публикации карточки."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Опубликовать на acat.kz", callback_data=f"acat_confirm:{slug}")],
            [InlineKeyboardButton(text="⬅️ Назад к кандидатам", callback_data="acat_candidates")]
        ]
    )
    return keyboard
