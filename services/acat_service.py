"""
acat_service.py - Модуль взаимодействия с Informburo Cards и FastEdit CMS acat.kz
"""

import os
import re
import urllib.parse
import html
from datetime import datetime
import requests

CMS_BASE_URL = "https://www.acat.kz"
CMS_LOGIN_URL = "https://www.acat.kz/cms/"
CMS_AJAX_URL = "https://www.acat.kz/frontEnd/ajax.php"
CMS_USER = "root"
CMS_PASS = "VqmIsB"
CMS_PARENT_ID = 9
CMS_CLASS_ID = 8

CARDS_URL = "https://informburo.kz/cards"

LEGAL_KEYWORDS = [
    "закон", "права", "суд", "адвокат", "юрист", "штраф", "кодекс", "статья",
    "мошенничеств", "дроппер", "полици", "наследств", "недвижим", "налог",
    "ип", "самозанят", "трудов", "алимент", "льгот", "правил", "регистрац",
    "нотариус", "договор", "ипотек", "банк", "кредит", "паспорт", "удостоверен",
    "документ", "пособ", "пенси", "жилищн", "выплат", "гаранти", "грант"
]

def cp1251_quote(s: str) -> str:
    """Кодирование строки в URL-encoded представление байт CP1251 (требование FastEdit CMS)."""
    if not s:
        return ""
    bytes_data = s.encode("cp1251", errors="replace")
    return urllib.parse.quote_from_bytes(bytes_data)

def is_legal_topic(title: str) -> bool:
    """Проверка релевантности заголовка юридической/правовой тематике."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in LEGAL_KEYWORDS)

def get_published_news():
    """Получение списка последних опубликованных новостей на acat.kz."""
    try:
        resp = requests.get(f"{CMS_BASE_URL}/news/", timeout=15)
        resp.encoding = "utf-8"
        pattern = r'<div class="news1" id="news-(\d+)">\s*<div class="date">([^<]+)</div>\s*<div class="name">\s*<a href="([^"]+)"><b>([^<]+)</b></a>'
        matches = re.findall(pattern, resp.text, re.DOTALL)
        items = []
        for news_id, date_str, rel_url, title in matches:
            items.append({
                "id": news_id,
                "date": date_str.strip(),
                "url": f"{CMS_BASE_URL}{rel_url}",
                "title": html.unescape(title.strip())
            })
        return items
    except Exception as e:
        print(f"Error fetching published news from acat.kz: {e}")
        return []

def get_candidate_cards():
    """Получение и фильтрация юридических карточек с informburo.kz/cards."""
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
            
            title_m = re.search(r'<span[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</span>', inner_html)
            if title_m:
                title = title_m.group(1).strip()
            else:
                clean = re.sub(r'<[^>]+>', ' ', inner_html).strip()
                clean = re.sub(r'\s+', ' ', clean)
                title = clean if len(clean) > 15 else ""
                
            title = re.sub(r'^\d{1,2}\s+[а-яА-ЯёЁ]+,\s+\d{1,2}:\d{2}\s*', '', title).strip()
            title = html.unescape(title)
            
            if not title:
                continue
                
            is_legal = is_legal_topic(title)
            
            is_pub = False
            for p in published:
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
    """Парсинг детальной страницы карточки и формирование HTML с версткой под acat.kz."""
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
        
        # Look for storage/photos path
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
            
        # Cards body
        card_matches = re.findall(r'<div\s+class="article-text-card">([\s\S]*?)</div>\s*</div>', text, re.IGNORECASE)
        body_cards = ""
        if card_matches:
            for c in card_matches:
                cleaned = re.sub(r'<script[\s\S]*?</script>', '', c)
                cleaned = re.sub(r'<style[\s\S]*?</style>', '', cleaned).strip()
                body_cards += f"\t\t<div class=\"article-text-card\">{cleaned}</div>\n"
        else:
            art_m = re.search(r'<div\s+class="article">([\s\S]*?)<div\s+class="read-more">', text)
            if art_m:
                body_cards = art_m.group(1).strip()
                
        # Intro paragraphs
        intro_html = ""
        intro_m = re.search(r'<div\s+class="article">([\s\S]*?)<div\s+class="article-text-card">', text)
        if intro_m:
            p_matches = re.findall(r'<p[^>]*>([\s\S]*?)</p>', intro_m.group(1))
            for p in p_matches:
                intro_html += f"\t\t<p>{p.strip()}</p>\n"
                
        # Formatted full HTML for acat.kz
        img_style = "width: 475px; height: 267px; border-width: 5px; border-style: solid; margin: 5px; float: right;"
        
        full_html = (
            f'<div class="uk-width-2-3@m uk-width-1-1">\n'
            f'\t<strong class="article-excerpt">{excerpt}</strong><img alt="{img_alt}" src="{img_url}" style="{img_style}" />\n'
            f'\t<div class="article">\n'
            f'{intro_html}{body_cards}\t\t<div class="read-more">\n'
            f'\t\t\t<hr />\n'
            f'\t\t\t<p style="text-align: right;">\n'
            f'\t\t\t\tИсточник: <a href="{card_url}" target="_blank">informburo.kz</a></p>\n'
            f'\t\t</div>\n'
            f'\t</div>\n'
            f'</div>\n'
            f'<p>&nbsp;</p>'
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
    """Публикация карточки на сайт acat.kz через FastEdit CMS."""
    details = get_card_details(card_url)
    if not details:
        return {"success": False, "error": "Не удалось загрузить или спарсить карточку"}
        
    session = requests.Session()
    
    # 1. Авторизация в CMS
    login_data = {
        "auth_admin_name": CMS_USER,
        "auth_admin_pw": CMS_PASS
    }
    session.post(CMS_LOGIN_URL, data=login_data, verify=False, timeout=15)
    
    # 2. Загрузка картинки
    server_img_name = ""
    if details["image_url"]:
        try:
            img_resp = requests.get(details["image_url"], timeout=15)
            if img_resp.status_code == 200:
                files = {
                    "file[138]": ("image.webp", img_resp.content, "image/webp")
                }
                headers = {"X-Requested-With": "XMLHttpRequest"}
                up_resp = session.post(f"{CMS_AJAX_URL}?uploadFiles", files=files, headers=headers, verify=False, timeout=20)
                json_data = up_resp.json()
                server_img_name = json_data.get("file-138", "")
        except Exception as e:
            print(f"Warning: Image upload failed: {e}")
            
    # 3. Подготовка и кодирование полей в CP1251
    meta_title = f"{details['title']} | Адвокатская контора АСАТ"
    meta_desc = details["excerpt"]
    meta_kw = "Адвокатская контора АСАТ, адвокаты Алматы, юристы, юридические услуги в Алматы, законодательство Казахстана"
    
    fields = [
        ("createObject", str(CMS_PARENT_ID)),
        ("lang", "ru"),
        ("obj[name]", details["title"]),
        ("obj[class_id]", str(CMS_CLASS_ID)),
        ("obj[fields][116]", meta_title),
        ("obj[fields][117]", meta_kw),
        ("obj[fields][118]", meta_desc),
        ("obj[fields][19]", details["date"]),
        ("obj[fields][20]", details["title"]),
        ("obj[fields][144]", details["title"]),
        ("obj[fields][21]", details["excerpt"]),
        ("obj[fields][22]", details["html"]),
        ("obj[fields][138]", server_img_name),
        ("obj[fields][145]", "")
    ]
    
    encoded_pairs = []
    for k, v in fields:
        enc_k = cp1251_quote(k)
        enc_v = cp1251_quote(v)
        encoded_pairs.append(f"{enc_k}={enc_v}")
        
    post_body = "&".join(encoded_pairs).encode("ascii")
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=windows-1251",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    post_resp = session.post(CMS_AJAX_URL, data=post_body, headers=headers, verify=False, timeout=25)
    
    if post_resp.status_code == 200 and "ok" in post_resp.text:
        latest_published = get_published_news()
        published_url = f"{CMS_BASE_URL}/news/"
        if latest_published:
            published_url = latest_published[0]["url"]
            
        return {
            "success": True,
            "title": details["title"],
            "date": details["date"],
            "url": published_url,
            "excerpt": details["excerpt"],
            "image_url": details["image_url"]
        }
    else:
        return {
            "success": False,
            "error": f"Ответ сервера: {post_resp.text[:200]}"
        }
