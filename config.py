import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv(override=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def validate_config():
    """Проверка наличия токена и ключей."""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("❌ [ОШИБКА] Не указан TELEGRAM_BOT_TOKEN в файле .env!", flush=True)
        sys.exit(1)
        
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        print("ℹ️ [Внимание] GEMINI_API_KEY не указан. Бот будет работать без функций ИИ.", flush=True)
    else:
        print("🤖 [AI] Обнаружен GEMINI_API_KEY, модуль ИИ активен!", flush=True)
