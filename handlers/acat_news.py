"""
handlers/acat_news.py - Обработчики команд и инлайн-кнопок для управления новостями acat.kz
"""

import asyncio
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from services.acat_service import (
    get_published_news,
    get_candidate_cards,
    get_card_details,
    publish_card_to_acat,
    delete_news_from_acat
)
from handlers.keyboards import (
    get_acat_menu_keyboard,
    get_confirm_publish_keyboard,
    get_confirm_delete_keyboard
)

router = Router()

# 1. Главное меню раздела новостей (по кнопке меню или команде /news)
@router.message(Command("news"))
@router.message(F.text == "📰 Новости ACAT.KZ")
async def cmd_acat_news_menu(message: Message):
    text = (
        "⚖️ <b>Управление новостным порталом ACAT.KZ</b>\n\n"
        "Здесь вы можете в один клик отслеживать новые юридические карточки на <b>Informburo.kz</b>, "
        "мгновенно публиковать их на сайт адвокатской конторы <a href=\"https://www.acat.kz\">acat.kz</a> "
        "и управлять опубликованными статьями (удаление/просмотр).\n\n"
        "📌 <b>Выберите действие:</b>"
    )
    await message.answer(text, reply_markup=get_acat_menu_keyboard(), parse_mode="HTML", disable_web_page_preview=True)

# 2. Возврат в меню новостей
@router.callback_query(F.data == "acat_menu")
async def cb_acat_menu(callback: CallbackQuery):
    text = (
        "⚖️ <b>Управление новостным порталом ACAT.KZ</b>\n\n"
        "Выберите действие ниже 👇"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_acat_menu_keyboard(), parse_mode="HTML", disable_web_page_preview=True)
    except Exception:
        await callback.message.answer(text, reply_markup=get_acat_menu_keyboard(), parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()

# 3. Список опубликованных новостей на acat.kz с кнопками удаления
@router.callback_query(F.data == "acat_published")
async def cb_acat_published(callback: CallbackQuery):
    await callback.answer("Загрузка новостей с acat.kz...")
    published = await asyncio.to_thread(get_published_news)
    
    if not published:
        text = "⚠️ Не удалось получить список опубликованных новостей с сайта."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")]])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        return
        
    lines = ["🌐 <b>Последние опубликованные новости на сайте <a href=\"https://www.acat.kz/news/\">acat.kz</a>:</b>\n"]
    buttons = []
    
    for i, item in enumerate(published[:6], 1):
        lines.append(f"{i}. <b>[{item['date']}]</b> <a href=\"{item['url']}\">{item['title']}</a> <code>(ID: {item['id']})</code>")
        buttons.append([
            InlineKeyboardButton(text=f"🌐 #{i} Читать", url=item["url"]),
            InlineKeyboardButton(text=f"🗑 #{i} Удалить (ID: {item['id']})", callback_data=f"acat_del_ask:{item['id']}")
        ])
        
    lines.append("\n<i>Для удаления новости нажмите кнопку с корзиной или введите:</i> <code>/delnews ID</code>")
    buttons.append([InlineKeyboardButton(text="📋 Кандидаты с Informburo", callback_data="acat_candidates")])
    buttons.append([InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await callback.message.edit_text("\n".join(lines), reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
    except Exception:
        await callback.message.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)

# 4. Отдельный список для удаления новостей
@router.callback_query(F.data == "acat_delete_list")
async def cb_acat_delete_list(callback: CallbackQuery):
    await callback.answer("Загружаю список для удаления...")
    published = await asyncio.to_thread(get_published_news)
    
    if not published:
        text = "⚠️ Список опубликованных новостей пуст или не удалось подключиться к сайту."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")]])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        return
        
    lines = ["🗑 <b>Выберите новость для удаления с сайта acat.kz:</b>\n"]
    buttons = []
    
    for i, item in enumerate(published[:6], 1):
        lines.append(f"{i}. <b>{item['title']}</b> <code>(ID: {item['id']}, {item['date']})</code>")
        buttons.append([
            InlineKeyboardButton(text=f"🗑 Удалить #{i} (ID {item['id']})", callback_data=f"acat_del_ask:{item['id']}")
        ])
        
    lines.append("\n<i>Либо введите команду вручную:</i> <code>/delnews ID</code>")
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="acat_menu")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await callback.message.edit_text("\n".join(lines), reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")

# 5. Запрос подтверждения удаления новости
@router.callback_query(F.data.startswith("acat_del_ask:"))
async def cb_acat_del_ask(callback: CallbackQuery):
    news_id = callback.data.split("acat_del_ask:")[1]
    await callback.answer()
    
    published = await asyncio.to_thread(get_published_news)
    title = f"Новость ID {news_id}"
    for item in published:
        if str(item["id"]) == str(news_id):
            title = item["title"]
            break
            
    text = (
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы действительно хотите безвозвратно удалить с сайта <b>acat.kz</b> новость:\n"
        f"📰 <b>{title}</b>\n"
        f"🆔 <b>ID в CMS:</b> <code>{news_id}</code>\n\n"
        f"<i>Действие удалит запись из базы FastEdit CMS и уберёт страницу с сайта.</i>"
    )
    
    kb = get_confirm_delete_keyboard(news_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

# 6. Выполнение удаления новости
@router.callback_query(F.data.startswith("acat_del_do:"))
async def cb_acat_del_do(callback: CallbackQuery):
    news_id = callback.data.split("acat_del_do:")[1]
    await callback.answer("Удаление новости...")
    
    res = await asyncio.to_thread(delete_news_from_acat, news_id)
    
    if res.get("success"):
        text = (
            f"✅ <b>Новость ID <code>{news_id}</code> успешно удалена с сайта acat.kz!</b>\n\n"
            f"Страница новости удалена из CMS и больше не отображается в ленте сайта."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Список опубликованных", callback_data="acat_published")],
            [InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        text = (
            f"❌ <b>Не удалось удалить новость ID <code>{news_id}</code></b>\n\n"
            f"Ошибка: <code>{res.get('error', 'Неизвестная ошибка')}</code>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

# 7. Команда /delnews <ID>
@router.message(Command("delnews"))
async def cmd_delnews(message: Message):
    args = message.text.strip().split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer(
            "ℹ️ <b>Использование команды:</b>\n<code>/delnews ID_новости</code>\n\n"
            "Пример: <code>/delnews 3031</code>\n\n"
            "Посмотреть список ID опубликованных новостей можно через кнопку меню <b>«🌐 Опубликованные на сайте»</b>.",
            parse_mode="HTML"
        )
        return
        
    news_id = args[1]
    published = await asyncio.to_thread(get_published_news)
    title = f"Новость ID {news_id}"
    for item in published:
        if str(item["id"]) == str(news_id):
            title = item["title"]
            break
            
    text = (
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы действительно хотите безвозвратно удалить с сайта <b>acat.kz</b> новость:\n"
        f"📰 <b>{title}</b>\n"
        f"🆔 <b>ID в CMS:</b> <code>{news_id}</code>\n\n"
        f"<i>Действие удалит запись из базы FastEdit CMS и уберёт страницу с сайта.</i>"
    )
    
    kb = get_confirm_delete_keyboard(news_id)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

# 8. Список юридических кандидатов с Informburo
@router.callback_query(F.data == "acat_candidates")
async def cb_acat_candidates(callback: CallbackQuery):
    await callback.answer("Сканирую Informburo.kz...")
    cards = await asyncio.to_thread(get_candidate_cards)
    
    if not cards:
        text = "⚠️ Не удалось загрузить карточки с Informburo.kz."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Меню", callback_data="acat_menu")]])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        return
        
    lines = ["📋 <b>Актуальные юридические карточки на Informburo:</b>\n"]
    buttons = []
    
    for i, c in enumerate(cards[:6], 1):
        status = "✅ <i>(Опубликовано)</i>" if c["is_published"] else "🆕 <b>(Новая)</b>"
        lines.append(f"{i}. {status} {c['title']}")
        
        if not c["is_published"]:
            slug_short = c["slug"][:45]
            buttons.append([
                InlineKeyboardButton(text=f"👁 Превью #{i}", callback_data=f"acat_prev:{slug_short}"),
                InlineKeyboardButton(text=f"🚀 Опубликовать #{i}", callback_data=f"acat_pub_now:{slug_short}")
            ])
            
    lines.append("\n<i>Нажмите кнопку под сообщением для предпросмотра или быстрой публикации.</i>")
    buttons.append([InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await callback.message.edit_text("\n".join(lines), reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")

# 9. Опубликовать следующую актуальную
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
            "🎉 <b>Все актуальные юридические карточки уже опубликованы на acat.kz!</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")]]),
            parse_mode="HTML"
        )
        return
        
    details = await asyncio.to_thread(get_card_details, target_card["url"])
    if not details:
        await callback.message.answer("⚠️ Не удалось загрузить детали выбранной карточки.")
        return
        
    caption = (
        f"🚀 <b>Кандидат на публикацию:</b>\n\n"
        f"📰 <b>Заголовок:</b> {details['title']}\n"
        f"📅 <b>Дата источника:</b> {details['date']}\n\n"
        f"📝 <b>Лид:</b> {details['excerpt']}\n\n"
        f"🔗 <a href=\"{details['card_url']}\">Открыть оригинал на Informburo</a>"
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
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(caption, reply_markup=kb, parse_mode="HTML")

# 10. Предпросмотр карточки по кнопке
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
        f"👁 <b>Предпросмотр карточки:</b>\n\n"
        f"📰 <b>{details['title']}</b>\n"
        f"📅 <b>Дата:</b> <code>{details['date']}</code>\n\n"
        f"📝 <b>Лид:</b> {details['excerpt']}\n\n"
        f"🔗 <a href=\"{details['card_url']}\">Оригинал статьи</a>"
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
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(caption, reply_markup=kb, parse_mode="HTML")

# 11. Подтверждение публикации карточки
@router.callback_query(F.data.startswith("acat_confirm:") | F.data.startswith("acat_pub_now:"))
async def cb_acat_confirm_publish(callback: CallbackQuery):
    if "acat_confirm:" in callback.data:
        slug_part = callback.data.split("acat_confirm:")[1]
    else:
        slug_part = callback.data.split("acat_pub_now:")[1]
        
    await callback.answer("Начинаю публикацию...")
    status_msg = await callback.message.answer("⏳ <b>Публикация на acat.kz...</b>\n<i>Авторизация в CMS, загрузка фото и создание записи...</i>", parse_mode="HTML")
    
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
        news_id = res.get("id", "")
        success_text = (
            f"✅ <b>Новость успешно опубликована на сайте acat.kz!</b>\n\n"
            f"📰 <b>Заголовок:</b> {res['title']}\n"
            f"📅 <b>Дата:</b> {res['date']}\n"
            f"🆔 <b>ID в CMS:</b> <code>{news_id}</code>\n\n"
            f"👉 <b>Ссылка:</b> <a href=\"{res['url']}\">Открыть новость на acat.kz</a>\n"
            f"🌐 <a href=\"https://www.acat.kz/news/\">Общий раздел новостей</a>"
        )
        
        buttons = [
            [InlineKeyboardButton(text="🌐 Открыть новость на сайте", url=res['url'])],
            [InlineKeyboardButton(text="📋 Список кандидатов", callback_data="acat_candidates")]
        ]
        if news_id:
            buttons.append([InlineKeyboardButton(text=f"🗑 Удалить эту новость (ID {news_id})", callback_data=f"acat_del_ask:{news_id}")])
        buttons.append([InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")])
        
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await status_msg.edit_text(success_text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=False)
    else:
        err_text = f"❌ <b>Ошибка при публикации:</b>\n<code>{res.get('error', 'Неизвестная ошибка')}</code>"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Меню новостей", callback_data="acat_menu")]])
        await status_msg.edit_text(err_text, reply_markup=kb, parse_mode="HTML")

# 12. Перехват ссылок на informburo.kz/cards, отправленных пользователем в чат
@router.message(F.text.regexp(r'https?://informburo\.kz/cards/([a-zA-Z0-9_-]+)'))
async def handle_informburo_url(message: Message):
    match = re.search(r'https?://informburo\.kz/cards/([a-zA-Z0-9_-]+)', message.text)
    if not match:
        return
        
    card_url = match.group(0)
    slug = match.group(1)
    
    status_msg = await message.answer("🔍 <b>Обнаружена карточка Informburo!</b> Загружаю данные...", parse_mode="HTML")
    details = await asyncio.to_thread(get_card_details, card_url)
    
    if not details:
        await status_msg.edit_text("⚠️ Не удалось получить содержимое карточки по ссылке.")
        return
        
    caption = (
        f"📰 <b>{details['title']}</b>\n\n"
        f"📅 <b>Дата:</b> <code>{details['date']}</code>\n"
        f"📝 <b>Лид:</b> {details['excerpt']}\n\n"
        f"Хотите опубликовать эту новость на <b>acat.kz</b>?"
    )
    
    kb = get_confirm_publish_keyboard(slug[:45])
    await status_msg.delete()
    
    if details["image_url"]:
        await message.answer_photo(
            photo=details["image_url"],
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        await message.answer(caption, reply_markup=kb, parse_mode="HTML")
