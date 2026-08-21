from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура бота (Reply Keyboard)."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💵 Добавить расход"), KeyboardButton(text="📊 Анализ расходов")],
            [KeyboardButton(text="🎯 Цели и бюджет"), KeyboardButton(text="📥 Загрузить выписку")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="📰 Новости ACAT.KZ")],
            [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="🧹 Очистить")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Введите расход, отправьте выписку или выберите меню..."
    )
    return keyboard

def get_settings_inline_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-кнопки для настроек."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧹 Очистить контекст диалога", callback_data="clear_context")],
            [InlineKeyboardButton(text="🔄 Проверить статус", callback_data="check_status")]
        ]
    )
    return keyboard

def get_acat_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное инлайн-меню управления новостями acat.kz."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Кандидаты с Informburo", callback_data="acat_candidates")],
            [InlineKeyboardButton(text="🚀 Опубликовать следующую", callback_data="acat_publish_next")],
            [InlineKeyboardButton(text="🌐 Опубликованные на сайте", callback_data="acat_published")],
            [InlineKeyboardButton(text="🗑 Удалить новость с сайта", callback_data="acat_delete_list")]
        ]
    )
    return keyboard

def get_confirm_publish_keyboard(slug: str) -> InlineKeyboardMarkup:
    """Инлайн-кнопки подтверждения публикации карточки."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Опубликовать на acat.kz", callback_data=f"acat_confirm:{slug}")],
            [InlineKeyboardButton(text="📋 Назад к кандидатам", callback_data="acat_candidates")]
        ]
    )
    return keyboard

def get_confirm_delete_keyboard(news_id: str | int) -> InlineKeyboardMarkup:
    """Инлайн-кнопки подтверждения удаления новости."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Да, удалить безвозвратно", callback_data=f"acat_del_do:{news_id}")],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="acat_published")]
        ]
    )
    return keyboard
