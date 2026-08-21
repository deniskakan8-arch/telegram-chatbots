import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from io import BytesIO
from pypdf import PdfReader
from google import genai
from config import GEMINI_API_KEY, CATEGORIES

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-3.6-flash"

CATEGORIES_PROMPT = "\n".join([f"- {c}" for c in CATEGORIES])

def parse_statement_pdf(pdf_bytes: bytes) -> list:
    """
    Извлекает текст из PDF банковской выписки и парсит транзакции.
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    all_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            all_text += text + "\n"
            
    prompt = f"""
Ты — банковский парсер. Перед тобой текст выписки по банковской карте.
Твоя задача — извлечь ВСЕ расходные операции (покупки, оплаты услуг, комиссии, снятия). Игнорируй поступления и переводы между своими счетами.

Для каждой операции определи:
- "date": дата в формате "YYYY-MM-DD"
- "merchant": название магазина/услуги
- "amount": положительное число суммы расхода в KZT
- "category": строго выбери из списка:
{CATEGORIES_PROMPT}

Ответь ТОЛЬКО валидным JSON-массивом объектов:
[
  {{"date": "2026-08-16", "merchant": "DODO PITSTSA", "amount": 2990.0, "category": "🚴‍♂️ Доставка еды и фастфуд"}},
  {{"date": "2026-08-16", "merchant": "IP ALTYN ADAM", "amount": 2810.0, "category": "🛒 Супермаркеты и продукты"}}
]

Текст выписки:
{all_text[:30000]}
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
        print(f"Error parsing statement with LLM: {e}")
        return []

def analyze_statement_dynamics(prev_month_data: dict, curr_month_data: dict) -> str:
    """
    Генерирует умный отчёт по динамике расходов с аналитикой всплесков и экономии.
    """
    prompt = f"""
Ты — профессиональный финансовый консультант Кан Дениса.
Сравни расходы за предыдущий период и текущий период:

Предыдущий период:
Общая сумма: {prev_month_data.get('total', 0)} KZT
По категориям: {json.dumps(prev_month_data.get('categories', {}), ensure_ascii=False)}

Текущий период:
Общая сумма: {curr_month_data.get('total', 0)} KZT
По категориям: {json.dumps(curr_month_data.get('categories', {}), ensure_ascii=False)}

Составь краткий, ёмкий и мотивирующий финансовый отчёт для Telegram:
1. 📊 Динамика общих расходов (выросли/снизились на X%).
2. 🚨 Где зафиксирован рост (всплески трат) и на сколько процентов (+X%).
3. 🎉 Где удалось сэкономить (-X%).
4. 💡 2-3 конкретных совета по оптимизации бюджета на следующий месяц.

Форматируй в красивом Telegram Markdown с эмодзи.
"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Не удалось сгенерировать аналитику динамики: {e}"
