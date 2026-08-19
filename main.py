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
from config import TELEGRAM_BOT_TOKEN, validate_config
from handlers.user import router as user_router
from handlers.acat_news import router as acat_router
from server import start_health_server

async def main():
    print("=" * 60, flush=True)
    print("🤖 Запуск Telegram AI & News Management Бота...", flush=True)
    print("=" * 60, flush=True)

    validate_config()

    # Запуск фонового веб-сервера активности для Render/Cloud 24/7
    start_health_server()

    # Инициализация бота и диспетчера aiogram
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    
    # Подключаем роутеры: сначала специализированный acat_router, затем общий user_router
    dp.include_router(acat_router)
    dp.include_router(user_router)

    # Проверка подключения
    bot_info = await bot.get_me()
    print(f"✅ Успешное подключение к Telegram: @{bot_info.username} ({bot_info.first_name})", flush=True)
    print("🟢 Бот запущен и ожидает сообщений!", flush=True)
    print(f"👉 Откройте https://t.me/{bot_info.username} и нажмите /start\n", flush=True)

    # Сбрасываем старые вебхуки и запускаем Long Polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Telegram-бот остановлен.", flush=True)
