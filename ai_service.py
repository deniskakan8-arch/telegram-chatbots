import os
import asyncio
from dotenv import load_dotenv

SYSTEM_INSTRUCTION = (
    "Ты — умный, вежливый и полезный ИИ-помощник в Telegram-боте. "
    "Отвечай понятно, структурированно, грамотно и емко на русском языке. "
    "Используй красивое форматирование и эмодзи. "
    "Если вопрос короткий, отвечай лаконично."
)

user_chats = {}
_client = None

def init_gemini():
    """Инициализация клиента Google Gemini API."""
    global _client
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key or api_key == "your_gemini_api_key_here":
        return False
        
    try:
        from google import genai
        _client = genai.Client(api_key=api_key)
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации google-genai: {e}", flush=True)
        return False

def get_user_chat(user_id: int):
    """Получение или создание контекстной сессии чата пользователя."""
    if user_id not in user_chats:
        from google.genai import types
        try:
            user_chats[user_id] = _client.chats.create(
                model="gemini-3.5-flash-lite",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.6,
                    max_output_tokens=1500,
                )
            )
        except Exception:
            user_chats[user_id] = _client.chats.create(
                model="gemini-3.6-flash",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.6,
                    max_output_tokens=1500,
                )
            )
    return user_chats[user_id]

def reset_user_chat(user_id: int) -> bool:
    """Очистить историю диалога пользователя с ИИ."""
    if user_id in user_chats:
        del user_chats[user_id]
        return True
    return False

def _sync_ask_gemini(user_id: int, prompt: str) -> str:
    """Синхронный вызов генерации Gemini."""
    global _client
    if _client is None:
        if not init_gemini():
            return "⚠️ Модуль ИИ ещё не настроен: укажите GEMINI_API_KEY в настройках (.env)."

    try:
        chat = get_user_chat(user_id)
        response = chat.send_message(prompt)
        text = (response.text or "").strip()
        
        # Лимит длины одного сообщения в Telegram (4096 символов)
        if len(text) > 4000:
            text = text[:3990] + "...\n\n*(Ответ сокращен из-за лимита Telegram)*"
            
        return text or "🤔 Нейросеть вернула пустой ответ."
        
    except Exception as e:
        print(f"⚠️ Ошибка Gemini API ({e}) для пользователя {user_id}", flush=True)
        err = str(e).lower()
        if "quota" in err or "rate limit" in err:
            return "⏳ Превышен лимит запросов к ИИ. Пожалуйста, подождите минутку и попробуйте снова."
        elif "api key" in err:
            return "❌ Неверный API-ключ Gemini. Проверьте правильность ключа."
        else:
            return "😔 Произошла ошибка при обращении к нейросети. Попробуйте переформулировать вопрос."

async def ask_gemini_async(user_id: int, prompt: str) -> str:
    """Асинхронный вызов для неблокирующей работы в Telegram Event Loop."""
    return await asyncio.to_thread(_sync_ask_gemini, user_id, prompt)
