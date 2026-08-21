"""
services/acat_service.py - Модуль интеграции с Informburo и FastEdit CMS acat.kz.
Автоматизирует парсинг юридических карточек, их публикацию и удаление на сайте www.acat.kz.
"""

import re
import html
import requests
import urllib3
import time
from datetime import datetime

# Отключаем предупреждения о SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CMS_BASE_URL = "https://www.acat.kz"
CMS_LOGIN_URL = "https://www.acat.kz/cms/"
CMS_AJAX_URL = "https://www.acat.kz/cms/ajax.php"
CMS_USER = "root"
CMS_PASS = "VqmIsB"
CMS_CLASS_ID = 8
CMS_PARENT_ID = 9
CARDS_URL = "https://informburo.kz/cards"

LEGAL_KEYWORDS = [
    "закон", "юрист", "адвокат", "штраф", "налог", "суд", "право", "права",
    "пособи", "пенси", "льгот", "документ", "цоны", "цон",
    "паспорт", "удостоверен", "труд", "работ", "увольн", "отпуск", "зарплат",
    "мошенник", "долг", "кредит", "банк", "имущество", "наследств", "жиль",
    "авто", "пдд", "водятел", "полици", "стать", "кодекс", "уголовн", "дроппер",
    "страхован", "бизнес", "ип", "самозанят", "очереди", "справк", "льгот", "коллектор"
]

def is_legal_topic(title: str) -> bool:
    """Проверяет релевантность заголовка юридической/гражданской тематике."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in LEGAL_KEYWORDS)

def get_published_news():
    """Получает список уже опубликованных новостей с сайта acat.kz/news/."""
    try:
        resp = requests.get(f"{CMS_BASE_URL}/news/", timeout=15, verify=False)
        resp.encoding = "utf-8"
        pattern = r'<div class="news1" id="news-(\d+)">\s*<div class="date">([^<]+)</div>\s*<div class="name">\s*<a href="([^"]+)"><b>([^<]+)</b></a>'
        matches = re.findall(pattern, resp.text, re.DOTALL)
        items = []
        for news_id, date_str, rel_url, title in matches:
            full_url = f"{CMS_BASE_URL}{rel_url}" if rel_url.startswith("/") else rel_url
            items.append({
                "id": news_id,
                "date": date_str.strip(),
                "url": full_url,
                "title": html.unescape(title.strip())
            })
        return items
    except Exception as e:
        print(f"Error fetching published news from acat.kz: {e}")
        return []

def get_candidate_cards():
    """Получает свежие карточки с informburo.kz/cards и проверяет их статус публикации."""
    try:
        resp = requests.get(CARDS_URL, timeout=15)
        resp.encoding = "utf-8"
        
        matches = re.findall(r'<a\s+href="(/cards/[a-zA-Z0-9_-]+)"[^>]*>([\s\S]*?)</a>', resp.text, re.IGNORECASE)
        published = get_published_news()
        
        cards = []
        seen = set()
        
        for rel_url, inner_html in matches:
            if rel_url in seen:
                continue
            seen.add(rel_url)
            
            title_m = re.search(r'<strong[^>]*class="[^"]*uk-card-title[^"]*"[^>]*>([\s\S]*?)</strong>', inner_html)
            if title_m:
                title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
            else:
                title_m2 = re.search(r'<span[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</span>', inner_html)
                if title_m2:
                    title = title_m2.group(1).strip()
                else:
                    clean = re.sub(r'<[^>]+>', ' ', inner_html).strip()
                    clean = re.sub(r'\s+', ' ', clean)
                    title = clean if len(clean) > 15 else ""
                
            title = re.sub(r'^\d{1,2}\s+[а-яА-ЯёЁa-zA-Z]+,\s+\d{1,2}:\d{2}\s*', '', title).strip()
            title = html.unescape(title)
            
            if not title:
                continue
                
            is_legal = is_legal_topic(title)
            
            is_pub = False
            for p in published:
                if len(p["title"]) >= 15 and len(title) >= 15:
                    if p["title"][:20].lower() in title.lower() or title[:20].lower() in p["title"].lower():
                        is_pub = True
                        break
                    
            if is_legal:
                cards.append({
                    "title": title,
                    "url": f"https://informburo.kz{rel_url}",
                    "slug": rel_url.replace("/cards/", ""),
                    "is_published": is_pub
                })
                
        return cards
    except Exception as e:
        print(f"Error fetching cards from Informburo: {e}")
        return []

def get_card_details(card_url: str):
    """Парсит детальную страницу карточки и формирует чистый HTML по стандартам acat.kz без лишних промо-блоков."""
    try:
        resp = requests.get(card_url, timeout=15)
        resp.encoding = "utf-8"
        text = resp.text
        
        # H1
        h1_m = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', text)
        title = html.unescape(re.sub(r'<[^>]+>', '', h1_m.group(1)).strip()) if h1_m else ""
        
        # Excerpt
        exc_m = re.search(r'<strong\s+class="article-excerpt">([\s\S]*?)</strong>', text)
        excerpt = html.unescape(re.sub(r'<[^>]+>', '', exc_m.group(1)).strip()) if exc_m else ""
        
        # Date
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_m = re.search(r'itemprop="datePublished"\s+content="([0-9]{4}-[0-9]{2}-[0-9]{2})', text)
        if date_m:
            date_str = date_m.group(1)
        else:
            iso_m = re.search(r'([0-9]{4}-[0-9]{2}-[0-9]{2})T[0-9]{2}:[0-9]{2}', text)
            if iso_m:
                date_str = iso_m.group(1)
                
        # Main image & alt
        img_url = ""
        img_alt = "Иллюстрация informburo.kz"
        
        storage_m = re.search(r'<img[^>]+src="([^"]*?/storage/photos/[^"]+)"([^>]*alt="([^"]*)")?', text)
        if storage_m:
            raw_src = storage_m.group(1)
            img_url = raw_src if raw_src.startswith("http") else f"https://informburo.kz{raw_src}"
            if storage_m.group(3):
                img_alt = html.unescape(storage_m.group(3))
        else:
            img_m = re.search(r'<img[^>]+class="[^"]*article-main-image[^"]*"[^>]+src="([^"]+)"', text)
            if img_m:
                raw_src = img_m.group(1)
                img_url = raw_src if raw_src.startswith("http") else f"https://informburo.kz{raw_src}"
            
        # Parse clean article content
        art_m = re.search(r'<div\s+class="article">([\s\S]*?)</div>\s*</div>', text, re.IGNORECASE)
        if not art_m:
            art_m = re.search(r'<div\s+class="article">([\s\S]*?)<div\s+class="read-more">', text, re.IGNORECASE)
            
        full_art = art_m.group(1) if art_m else ""
        
        # Strip all unwanted scripts, styles, banners, and internal "Читайте также" blocks
        full_art = re.sub(r'<script[\s\S]*?</script>', '', full_art, flags=re.IGNORECASE)
        full_art = re.sub(r'<style[\s\S]*?</style>', '', full_art, flags=re.IGNORECASE)
        full_art = re.sub(r'<div\s+class="read-more"[\s\S]*?</div>', '', full_art, flags=re.IGNORECASE)
        full_art = re.sub(r'<ul\s+class="several-images-read-more"[\s\S]*?</ul>', '', full_art, flags=re.IGNORECASE)
        full_art = re.sub(r'<div\s+class="article-banner[\s\S]*?</div>', '', full_art, flags=re.IGNORECASE)
        full_art = re.sub(r'<p[^>]*>\s*<strong>\s*Читайте также:?\s*</strong>\s*</p>', '', full_art, flags=re.IGNORECASE)
        
        parts = re.split(r'<div\s+class="article-text-card">', full_art, flags=re.IGNORECASE)
        
        # Intro paragraphs (part 0)
        intro_html = ""
        if len(parts) > 0:
            raw_intro = parts[0].strip()
            p_matches = re.findall(r'<p[^>]*>([\s\S]*?)</p>', raw_intro)
            for p in p_matches:
                p_clean = re.sub(r'<[^>]+>', '', p).strip()
                if p_clean and not p_clean.startswith("Читайте также"):
                    intro_html += f'\t\t<p>{p.strip()}</p>\n'
                    
        # Body cards (parts 1..N)
        body_cards = ""
        for p in parts[1:]:
            card_content = p.strip()
            card_content = re.sub(r'(?:</div>\s*)+$', '', card_content).strip()
            card_content = re.sub(r'<div\s+class="read-more"[\s\S]*?</div>', '', card_content, flags=re.IGNORECASE)
            card_content = re.sub(r'<ul\s+class="several-images-read-more"[\s\S]*?</ul>', '', card_content, flags=re.IGNORECASE)
            if card_content:
                body_cards += f'\t\t<div class="article-text-card">\n\t\t\t{card_content}\n\t\t</div>\n'
                
        # Formatted full HTML for acat.kz
        img_style = "width: 475px; height: 267px; border-width: 5px; border-style: solid; margin: 5px; float: right;"
        
        full_html = (
            '<div class="uk-width-2-3@m uk-width-1-1">\n'
            f'\t<strong class="article-excerpt">{excerpt}</strong><img alt="{img_alt}" src="{img_url}" style="{img_style}" />\n'
            '\t<div class="article">\n'
            f'{intro_html}{body_cards}\t\t<div class="read-more">\n'
            '\t\t\t<hr />\n'
            '\t\t\t<p style="text-align: right;">\n'
            f'\t\t\t\tИсточник: <a href="{card_url}" target="_blank">informburo.kz</a></p>\n'
            '\t\t</div>\n'
            '\t</div>\n'
            '</div>\n'
            '<p>&nbsp;</p>'
        )
        
        return {
            "title": title,
            "date": date_str,
            "excerpt": excerpt,
            "image_url": img_url,
            "image_alt": img_alt,
            "html": full_html,
            "card_url": card_url
        }
    except Exception as e:
        print(f"Error parsing card details {card_url}: {e}")
        return None

def publish_card_to_acat(card_url: str):
    """Публикует карточку на сайт acat.kz через FastEdit CMS."""
    details = get_card_details(card_url)
    if not details:
        return {"success": False, "error": "Не удалось загрузить и распарсить карточку"}
        
    session = requests.Session()
    
    # 1. Авторизация в FastEdit CMS
    login_data = {
        "auth_admin_name": CMS_USER,
        "auth_admin_pw": CMS_PASS
    }
    session.post(CMS_LOGIN_URL, data=login_data, verify=False, timeout=15)
    
    # 2. Загрузка главного изображения в CMS
    server_img_name = ""
    if details["image_url"]:
        try:
            img_resp = requests.get(details["image_url"], timeout=15)
            if img_resp.status_code == 200:
                files = {
                    "file[138]": ("image.webp", img_resp.content, "image/webp" if "webp" in details["image_url"] else "image/jpeg")
                }
                headers = {"X-Requested-With": "XMLHttpRequest"}
                up_resp = session.post(f"{CMS_AJAX_URL}?go=uploadFiles&run=content", files=files, headers=headers, verify=False, timeout=20)
                json_data = up_resp.json()
                server_img_name = json_data.get("file-138", "")
        except Exception as e:
            print(f"Warning: Image upload failed: {e}")
            
    # 3. Подготовка и сохранение объекта в CMS
    meta_title = f"{details['title']} | Адвокатская контора АСАТ"
    meta_desc = details["excerpt"]
    meta_kw = "Адвокатская контора АСАТ, адвокаты Алматы, юристы, юридические услуги в Алматы, законодательство Казахстана"
    
    save_data = {
        "run": "content",
        "go": "saveObject",
        "head": str(CMS_PARENT_ID),
        "active": "1",
        "name": details["title"],
        "lang": "ru",
        "class_id": str(CMS_CLASS_ID),
        "fields[116]": meta_title,
        "fields[117]": meta_kw,
        "fields[118]": meta_desc,
        "fields[19]": details["date"],
        "fields[20]": details["title"],
        "fields[144]": details["title"],
        "fields[21]": details["excerpt"],
        "fields[22]": details["html"],
        "fields[138]": server_img_name,
        "fields[145]": ""
    }
    
    post_resp = session.post(CMS_AJAX_URL, data=save_data, verify=False, timeout=25)
    
    # FastEdit CMS возвращает '1' при успешном сохранении
    if post_resp.status_code == 200 and (post_resp.text.strip() == "1" or "1" in post_resp.text or "ok" in post_resp.text):
        time.sleep(1)
        latest_published = get_published_news()
        published_url = f"{CMS_BASE_URL}/news/"
        news_id = ""
        
        # Находим URL и ID опубликованной статьи
        if latest_published:
            for item in latest_published:
                if len(item["title"]) >= 15 and len(details["title"]) >= 15:
                    if item["title"][:20].lower() in details["title"].lower() or details["title"][:20].lower() in item["title"].lower():
                        published_url = item["url"]
                        news_id = item["id"]
                        break
            else:
                published_url = latest_published[0]["url"]
                news_id = latest_published[0]["id"]
            
        return {
            "success": True,
            "id": news_id,
            "title": details["title"],
            "date": details["date"],
            "url": published_url,
            "excerpt": details["excerpt"],
            "image_url": details["image_url"]
        }
    else:
        return {
            "success": False,
            "error": f"Ответ сервера CMS: {post_resp.text[:200]}"
        }

def delete_news_from_acat(news_id: str | int) -> dict:
    """Удаляет новость с сайта acat.kz по её ID через FastEdit CMS."""
    try:
        session = requests.Session()
        login_data = {
            "auth_admin_name": CMS_USER,
            "auth_admin_pw": CMS_PASS
        }
        session.post(CMS_LOGIN_URL, data=login_data, verify=False, timeout=15)
        
        resp = session.get(
            CMS_AJAX_URL,
            params={"run": "content", "go": "deleteObject", "id": str(news_id)},
            verify=False,
            timeout=15
        )
        if resp.status_code == 200 and resp.text.strip() == "1":
            return {"success": True, "news_id": str(news_id)}
        else:
            return {"success": False, "error": f"Ответ сервера CMS: {resp.text[:200]}"}
    except Exception as e:
        print(f"Error deleting news {news_id}: {e}")
        return {"success": False, "error": str(e)}
