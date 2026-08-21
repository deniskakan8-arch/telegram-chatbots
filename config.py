import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DB_PATH = BASE_DIR / os.getenv("DB_PATH", "database/expenses.db")

CATEGORIES = [
    "🍔 Рестораны и заведения",
    "🚴‍♂️ Доставка еды и фастфуд",
    "🛒 Супермаркеты и продукты",
    "⛽ Топливо и АЗС",
    "🧖‍♂️ Развлечения и бани",
    "👔 Шопинг и одежда",
    "💡 Коммуналка и связь",
    "💊 Здоровье и аптеки",
    "📦 Яндекс Доставка (курьеры)",
    "📱 Подписки и сервисы",
    "🚗 Автосервис и запчасти",
    "🚨 Штрафы ПДД",
    "📦 Прочее",
]

DEFAULT_LIMITS = {
    "🍔 Рестораны и заведения": 50000,
    "🚴‍♂️ Доставка еды и фастфуд": 20000,
}

def validate_config():
    """Проверка наличия токена и ключей."""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("❌ [ОШИБКА] Не указан TELEGRAM_BOT_TOKEN в файле .env!", flush=True)
        sys.exit(1)
        
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        print("ℹ️ [Внимание] GEMINI_API_KEY не указан. Бот будет работать без функций ИИ.", flush=True)
    else:
        print("🤖 [AI] Обнаружен GEMINI_API_KEY, модуль ИИ активен!", flush=True)
