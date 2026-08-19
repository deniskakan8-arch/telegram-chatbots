import asyncio
import sys
import os

# UTF-8 консоль для Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import TELEGRAM_BOT_TOKEN, validate_config
from database.db import init_db
from handlers.user import router as user_router
from server import start_health_server

async def main():
    print("=" * 60, flush=True)
    print("🤖 Запуск Telegram Finance & AI Чат-Бота (Render 24/7)...", flush=True)
    print("=" * 60, flush=True)

    validate_config()

    # Запуск фонового веб-сервера активности для Render
    start_health_server()
    
    # Инициализация базы данных SQLite
    init_db()

    # Инициализация бота и диспетчера
    bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(user_router)

    bot_info = await bot.get_me()
    print(f"✅ Успешное подключение к Telegram: @{bot_info.username} ({bot_info.first_name})", flush=True)
    print("🟢 Бот запущен и ожидает расходов, выписок и вопросов!", flush=True)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Telegram-бот остановлен.", flush=True)
