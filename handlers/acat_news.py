"""
handlers/acat_news.py - Обработчики команд и инлайн-кнопок для управления новостями acat.kz
"""

import asyncio
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.filters import Command

from services.acat_service import (
    get_published_news,
    get_candidate_cards,
    get_card_details,
    publish_card_to_acat
)
from handlers.keyboards import get_acat_menu_keyboard, get_confirm_publish_keyboard, get_main_keyboard

router = Router()

# 1. Главное меню раздела новостей (по кнопке меню или команде /news)
@router.message(Command("news"))
@router.message(F.text == "📰 Новости ACAT.KZ")
async def cmd_acat_news_menu(message: Message):
    text = (
        "⚖️ **Управление новостным порталом ACAT.KZ**\n\n"
        "Здесь вы можете в один клик отслеживать новые юридические карточки на **Informburo.kz** "
        "и мгновенно публиковать их на сайт адвокатской конторы [acat.kz](https://www.acat.kz).\n\n"
        "📌 **Выберите действие:**"
    )
    await message.answer(text, reply_markup=get_acat_menu_keyboard(), parse_mode="Markdown", disable_web_page_preview=True)

# 2. Возврат в меню новостей
@router.callback_query(F.data == "acat_menu")
async def cb_acat_menu(callback: CallbackQuery):
    text = (
        "⚖️ **Управление новостным порталом ACAT.KZ**\n\n"
        "Выберите действие ниже 👇"
    )
    await callback.message.edit_text(text, reply_markup=get_acat_menu_keyboard(), parse_mode="Markdown", disable_web_page_preview=True)
    await callback.answer()

# 3. Список опубликованных новостей на acat.kz
@router.callback_query(F.data == "acat_published")
async def cb_acat_published(callback: CallbackQuery):
    await callback.answer("Загрузка новостей с acat.kz...")
    published = await asyncio.to_thread(get_published_news)
    
    if not published:
        text = "⚠️ Не удалось получить список опубликованных новостей с сайта."
    else:
        lines = ["🌐 **Последние новости на сайте [acat.kz](https://www.acat.kz/news/):**\n"]
        for i, item in enumerate(published[:7], 1):
            lines.append(f"{i}. **[{item['date']}]** [{item['title']}]({item['url']}) `(ID: {item['id']})`")
        text = "\n".join(lines)
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Кандидаты с Informburo", callback_data="acat_candidates")],
        [InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown", disable_web_page_preview=True)

# 4. Список юридических кандидатов с Informburo
@router.callback_query(F.data == "acat_candidates")
async def cb_acat_candidates(callback: CallbackQuery):
    await callback.answer("Сканирую Informburo.kz...")
    cards = await asyncio.to_thread(get_candidate_cards)
    
    if not cards:
        text = "⚠️ Не удалось загрузить карточки с Informburo.kz."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Меню", callback_data="acat_menu")]])
        await callback.message.edit_text(text, reply_markup=kb)
        return
        
    lines = ["📋 **Актуальные юридические карточки на Informburo:**\n"]
    buttons = []
    
    for i, c in enumerate(cards[:6], 1):
        status = "✅ _(Опубликовано)_" if c["is_published"] else "🆕 **(Новая)**"
        lines.append(f"{i}. {status} {c['title']}")
        
        if not c["is_published"]:
            slug_short = c["slug"][:45]
            buttons.append([
                InlineKeyboardButton(text=f"👁 Превью #{i}", callback_data=f"acat_prev:{slug_short}"),
                InlineKeyboardButton(text=f"🚀 Опубликовать #{i}", callback_data=f"acat_pub_now:{slug_short}")
            ])
            
    lines.append("\n_Нажмите кнопку под сообщением для предпросмотра или быстрой публикации._")
    buttons.append([InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("\n".join(lines), reply_markup=kb, parse_mode="Markdown")

# 5. Опубликовать следующую актуальную
@router.callback_query(F.data == "acat_publish_next")
async def cb_acat_publish_next(callback: CallbackQuery):
    await callback.answer("Ищу следующую подходящую новость...")
    cards = await asyncio.to_thread(get_candidate_cards)
    
    target_card = None
    for c in cards:
        if not c["is_published"]:
            target_card = c
            break
            
    if not target_card:
        await callback.message.edit_text(
            "🎉 **Все актуальные юридические карточки уже опубликованы на acat.kz!**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")]])
        )
        return
        
    # Загружаем детали карточки
    details = await asyncio.to_thread(get_card_details, target_card["url"])
    if not details:
        await callback.message.answer("⚠️ Не удалось загрузить детали выбранной карточки.")
        return
        
    caption = (
        f"🚀 **Кандидат на публикацию:**\n\n"
        f"📰 **Заголовок:** {details['title']}\n"
        f"📅 **Дата источника:** {details['date']}\n\n"
        f"📝 **Лид:** {details['excerpt']}\n\n"
        f"🔗 [Открыть оригинал на Informburo]({details['card_url']})"
    )
    
    kb = get_confirm_publish_keyboard(target_card["slug"][:45])
    
    if details["image_url"]:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(
            photo=details["image_url"],
            caption=caption,
            reply_markup=kb,
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(caption, reply_markup=kb, parse_mode="Markdown")

# 6. Предпросмотр карточки по кнопке
@router.callback_query(F.data.startswith("acat_prev:"))
async def cb_acat_preview(callback: CallbackQuery):
    slug_part = callback.data.split("acat_prev:")[1]
    await callback.answer("Загрузка карточки...")
    
    cards = await asyncio.to_thread(get_candidate_cards)
    matched_url = None
    full_slug = slug_part
    for c in cards:
        if c["slug"].startswith(slug_part):
            matched_url = c["url"]
            full_slug = c["slug"]
            break
            
    if not matched_url:
        matched_url = f"https://informburo.kz/cards/{slug_part}"
        
    details = await asyncio.to_thread(get_card_details, matched_url)
    if not details:
        await callback.message.answer("⚠️ Не удалось получить информацию о карточке.")
        return
        
    caption = (
        f"👁 **Предпросмотр карточки:**\n\n"
        f"📰 **{details['title']}**\n"
        f"📅 Дата: `{details['date']}`\n\n"
        f"📝 **Лид:** {details['excerpt']}\n\n"
        f"🔗 [Оригинал статьи]({details['card_url']})"
    )
    
    kb = get_confirm_publish_keyboard(full_slug[:45])
    
    if details["image_url"]:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(
            photo=details["image_url"],
            caption=caption,
            reply_markup=kb,
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(caption, reply_markup=kb, parse_mode="Markdown")

# 7. Подтверждение публикации карточки
@router.callback_query(F.data.startswith("acat_confirm:") | F.data.startswith("acat_pub_now:"))
async def cb_acat_confirm_publish(callback: CallbackQuery):
    if "acat_confirm:" in callback.data:
        slug_part = callback.data.split("acat_confirm:")[1]
    else:
        slug_part = callback.data.split("acat_pub_now:")[1]
        
    await callback.answer("Начинаю публикацию...")
    status_msg = await callback.message.answer("⏳ **Публикация на acat.kz...**\n_Авторизация в CMS, загрузка фото и создание записи..._")
    
    cards = await asyncio.to_thread(get_candidate_cards)
    target_url = None
    for c in cards:
        if c["slug"].startswith(slug_part):
            target_url = c["url"]
            break
            
    if not target_url:
        target_url = f"https://informburo.kz/cards/{slug_part}"
        
    res = await asyncio.to_thread(publish_card_to_acat, target_url)
    
    if res.get("success"):
        success_text = (
            f"✅ **Новость успешно опубликована на сайте acat.kz!**\n\n"
            f"📰 **Заголовок:** {res['title']}\n"
            f"📅 **Дата:** {res['date']}\n\n"
            f"👉 **Ссылка:** [Открыть новость на acat.kz]({res['url']})\n"
            f"🌐 [Общий раздел новостей](https://www.acat.kz/news/)"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Открыть новость на сайте", url=res['url'])],
            [InlineKeyboardButton(text="📋 Список кандидатов", callback_data="acat_candidates")],
            [InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")]
        ])
        await status_msg.edit_text(success_text, reply_markup=kb, parse_mode="Markdown", disable_web_page_preview=False)
    else:
        err_text = f"❌ **Ошибка при публикации:**\n`{res.get('error', 'Неизвестная ошибка')}`"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")]])
        await status_msg.edit_text(err_text, reply_markup=kb, parse_mode="Markdown")

# 8. Перехват ссылок на informburo.kz/cards, отправленных пользователем в чат
@router.message(F.text.regexp(r'https?://informburo\.kz/cards/([a-zA-Z0-9_-]+)'))
async def handle_informburo_url(message: Message):
    match = re.search(r'https?://informburo\.kz/cards/([a-zA-Z0-9_-]+)', message.text)
    if not match:
        return
        
    card_url = match.group(0)
    slug = match.group(1)
    
    status_msg = await message.answer("🔍 **Обнаружена карточка Informburo!** Загружаю данные...")
    details = await asyncio.to_thread(get_card_details, card_url)
    
    if not details:
        await status_msg.edit_text("⚠️ Не удалось получить содержимое карточки по ссылке.")
        return
        
    caption = (
        f"📰 **{details['title']}**\n\n"
        f"📅 **Дата:** `{details['date']}`\n"
        f"📝 **Лид:** {details['excerpt']}\n\n"
        f"Хотите опубликовать эту новость на **acat.kz**?"
    )
    
    kb = get_confirm_publish_keyboard(slug[:45])
    await status_msg.delete()
    
    if details["image_url"]:
        await message.answer_photo(
            photo=details["image_url"],
            caption=caption,
            reply_markup=kb,
            parse_mode="Markdown"
        )
    else:
        await message.answer(caption, reply_markup=kb, parse_mode="Markdown")
