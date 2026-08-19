import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
from config import GEMINI_API_KEY, CATEGORIES

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-3.6-flash"

CATEGORIES_PROMPT = "\n".join([f"- {c}" for c in CATEGORIES])

def parse_expense_text(text: str) -> dict:
    """
    Парсит естественный текст на сумму, категорию и комментарий.
    """
    prompt = f"""
Ты — персональный финансовый ассистент. Проанализируй сообщение пользователя о трате и извлеки данные в формате JSON.

Список доступных категорий:
{CATEGORIES_PROMPT}

Правила:
1. "amount": число (float или int, сумма в тенге). Если сумма не указана, верни 0.
2. "category": выбери НАИБОЛЕЕ подходящую категорию СТРОГО из списка выше.
3. "comment": краткое описание/название мерчанта или товара (например, "Обед", "Бензин Qazaq Oil", "Zara").
4. "is_expense": true, если это сообщение о трате/покупке, false если это просто приветствие или вопрос.

Ответь ТОЛЬКО валидным JSON-объектом без лишнего markdown, например:
{{"is_expense": true, "amount": 2600, "category": "🍔 Рестораны и заведения", "comment": "Обед"}}

Сообщение пользователя: "{text}"
"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        return json.loads(raw_text.strip())
    except Exception as e:
        print(f"Error in parse_expense_text: {e}")
        return {"is_expense": False, "amount": 0, "category": "📦 Прочее", "comment": text}

def parse_receipt_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    prompt = f"""
Проанализируй фото чека. Извлеки:
1. "amount": итоговая сумма к оплате (в тенге / KZT).
2. "merchant": название магазина/ресторана.
3. "category": выбери наиболее подходящую категорию СТРОГО из:
{CATEGORIES_PROMPT}
4. "comment": краткий список основных позиций или название заведения.

Ответь ТОЛЬКО JSON:
{{"amount": 12450.0, "category": "🛒 Супермаркеты и продукты", "comment": "Magnum: молоко, хлеб, сыр", "is_receipt": true}}
"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt
            ]
        )
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        return json.loads(raw_text.strip())
    except Exception as e:
        print(f"Error parsing receipt: {e}")
        return {"is_receipt": False}

def parse_voice_audio(audio_bytes: bytes, mime_type: str = "audio/ogg") -> dict:
    prompt = f"""
Послушай аудиозапись пользователя о расходах. Распознай речь и извлеки данные в JSON:
1. "amount": числовая сумма расхода.
2. "category": строго из списка:
{CATEGORIES_PROMPT}
3. "comment": что было куплено / название места.
4. "transcript": текст того, что сказал пользователь.

Ответь ТОЛЬКО JSON:
{{"amount": 3500, "category": "🍔 Рестораны и заведения", "comment": "Обед в Навате", "transcript": "пообедал на 3500 в навате", "is_expense": true}}
"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                genai.types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                prompt
            ]
        )
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        return json.loads(raw_text.strip())
    except Exception as e:
        print(f"Error parsing voice: {e}")
        return {"is_expense": False}
